import re
from collections import Counter
from datetime import datetime, timezone
from app.redaction import redact

LEVEL_RE = re.compile(r"\b(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b", re.I)
PATTERNS = [
    ("database_connection", re.compile(r"connection (?:pool )?exhausted|database.*timeout|connection refused", re.I),
     "Database connectivity or connection-pool exhaustion", "Check database availability, active connections, pool limits, slow queries, and connection leaks."),
    ("memory_pressure", re.compile(r"out of memory|oomkilled|memory limit|heap space", re.I),
     "Memory pressure or out-of-memory condition", "Inspect memory usage, container limits, heap settings, and traffic or deployment changes."),
    ("disk_pressure", re.compile(r"no space left|disk full|filesystem.*full", re.I),
     "Disk capacity exhaustion", "Check filesystem utilization, log growth, temporary files, and volume capacity."),
    ("upstream_timeout", re.compile(r"upstream.*timed out|request timed out|read timed out|deadline exceeded", re.I),
     "Request or upstream timeout", "Check upstream latency, network path, service saturation, timeout settings, and dependency health."),
    ("auth_failure", re.compile(r"unauthorized|forbidden|access denied|invalid credentials", re.I),
     "Authentication or authorization failures", "Check identity, token/certificate expiry, IAM/RBAC policy, and recent credential rotations."),
    ("crash_or_restart", re.compile(r"panic:|segmentation fault|crashloopbackoff|container.*(restarting|exited)", re.I),
     "Application crash or repeated restart", "Inspect the first exception, exit code, recent release, resource limits, and health checks."),
]

def analyze_logs(raw: str) -> dict:
    lines = [redact(x.strip()) for x in raw.splitlines() if x.strip()]
    levels = Counter()
    errors = []
    for line in lines:
        match = LEVEL_RE.search(line)
        level = match.group(1).upper() if match else "UNKNOWN"
        if level == "WARNING":
            level = "WARN"
        levels[level] += 1
        if level in {"ERROR", "FATAL", "CRITICAL"}:
            errors.append(line)

    findings = []
    for key, regex, title, recommendation in PATTERNS:
        matches = [line for line in lines if regex.search(line)]
        if matches:
            findings.append({
                "id": key, "title": title, "count": len(matches),
                "severity": "high" if key in {"database_connection", "memory_pressure", "crash_or_restart"} else "medium",
                "evidence": matches[:5], "recommendation": recommendation
            })

    if errors and not findings:
        findings.append({
            "id": "unclassified_errors", "title": "Unclassified application errors",
            "count": len(errors), "severity": "medium", "evidence": errors[:5],
            "recommendation": "Review the first error and correlate it with deployment, dependency, and infrastructure events."
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"total_lines": len(lines), "error_count": levels["ERROR"] + levels["FATAL"] + levels["CRITICAL"],
                    "warning_count": levels["WARN"], "levels": dict(levels)},
        "findings": findings,
        "redacted_log_excerpt": "\n".join(lines[:100])
    }
