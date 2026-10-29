from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from app.service import analyze
from app.aws_logs import list_log_groups, fetch_logs
from app.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")

class AnalyzeRequest(BaseModel):
    logs: str = Field(min_length=1)
    use_ai: bool = True

class CloudWatchRequest(BaseModel):
    log_group: str
    hours: int = Field(default=1, ge=1, le=168)
    limit: int = Field(default=1000, ge=1, le=10000)
    use_ai: bool = True

@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}

@app.post("/api/analyze")
def analyze_endpoint(payload: AnalyzeRequest):
    try:
        return analyze(payload.logs, payload.use_ai)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/api/aws/log-groups")
def aws_log_groups():
    try:
        return {"log_groups": list_log_groups()}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"CloudWatch request failed: {type(exc).__name__}: {exc}")

@app.post("/api/aws/analyze")
def aws_analyze(payload: CloudWatchRequest):
    try:
        logs = fetch_logs(payload.log_group, payload.hours, payload.limit)
        if not logs.strip():
            raise HTTPException(status_code=404, detail="No events found in the selected time window.")
        return analyze(logs, payload.use_ai)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"CloudWatch analysis failed: {type(exc).__name__}: {exc}")

@app.get("/", response_class=HTMLResponse)
def index():
    return HTML
HTML = r"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Log Analyzer</title>
<style>
body{font:15px system-ui;background:#0b1220;color:#e5e7eb;margin:0;padding:28px}main{max-width:1050px;margin:auto}
h1{margin-bottom:4px}.muted{color:#9ca3af}.card{background:#111c2e;border:1px solid #26364e;border-radius:12px;padding:18px;margin:16px 0}
textarea,input,select,button{font:inherit;border-radius:8px;border:1px solid #34445d;background:#0b1424;color:#e5e7eb;padding:10px}
textarea{width:100%;min-height:220px;box-sizing:border-box}button{background:#2563eb;border:0;cursor:pointer;margin:8px 8px 8px 0}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#08101d;padding:12px;border-radius:8px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.pill{display:inline-block;padding:3px 9px;border-radius:20px;background:#243b5c}
@media(max-width:700px){.grid{grid-template-columns:1fr}}
</style></head><body><main>
<h1>AI Log Analyzer</h1><div class="muted">Local-first SRE investigation · no automatic remediation</div>
<section class="card"><h2>Analyze pasted logs</h2><textarea id="logs" placeholder="Paste application or infrastructure logs here..."></textarea><br>
<label><input id="useai" type="checkbox" checked> Use AI (Ollama first, Bedrock fallback)</label><br>
<button onclick="analyzeText()">Analyze logs</button><button onclick="document.getElementById('logs').value=sample">Load sample</button></section>
<section class="card"><h2>Analyze AWS CloudWatch</h2><div class="grid">
<div><label>Log group</label><br><input id="group" style="width:95%" placeholder="/aws/ecs/my-service"></div>
<div><label>Lookback hours (1–168)</label><br><input id="hours" type="number" min="1" max="168" value="1"></div></div>
<label><input id="awsai" type="checkbox" checked> Use AI</label><br><button onclick="loadGroups()">List log groups</button><button onclick="analyzeAws()">Fetch and analyze</button><div id="groups" class="muted"></div></section>
<section class="card"><h2>Investigation result</h2><div id="status" class="muted">Waiting for logs...</div><div id="result"></div></section>
</main><script>
const sample=`2026-10-28T10:00:01Z INFO Payments API started
2026-10-28T10:01:02Z WARN Database connection pool exhausted
2026-10-28T10:01:03Z ERROR Database connection timeout after 3000ms
2026-10-28T10:01:04Z WARN Retry attempt 3 failed
2026-10-28T10:01:05Z ERROR Unable to process transaction`;
async function call(url,body){const r=await fetch(url,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const j=await r.json();if(!r.ok)throw new Error(j.detail||r.statusText);return j}
function render(j){document.getElementById('result').innerHTML='<pre>'+escapeHtml(JSON.stringify(j,null,2))+'</pre>';document.getElementById('status').textContent='Analysis complete'}
function escapeHtml(s){return s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
async function analyzeText(){try{document.getElementById('status').textContent='Analyzing...';render(await call('/api/analyze',{logs:document.getElementById('logs').value,use_ai:document.getElementById('useai').checked}))}catch(e){document.getElementById('status').textContent=e.message}}
async function loadGroups(){try{const j=await call('/api/aws/log-groups');document.getElementById('groups').textContent=j.log_groups.join(' · ')||'No log groups found'}catch(e){document.getElementById('groups').textContent=e.message}}
async function analyzeAws(){try{document.getElementById('status').textContent='Fetching CloudWatch events...';render(await call('/api/aws/analyze',{log_group:document.getElementById('group').value,hours:Number(document.getElementById('hours').value),limit:1000,use_ai:document.getElementById('awsai').checked}))}catch(e){document.getElementById('status').textContent=e.message}}
</script></body></html>"""
