from pathlib import Path
from app.analyzer import analyze_logs

SAMPLE = (Path(__file__).parent.parent / "samples" / "sample.log").read_text()

def test_summary_counts_levels():
    result = analyze_logs(SAMPLE)
    summary = result["summary"]
    assert summary["total_lines"] == 9
    assert summary["error_count"] == 4
    assert summary["warning_count"] == 3

def test_detects_known_patterns():
    ids = {f["id"] for f in analyze_logs(SAMPLE)["findings"]}
    assert {"database_connection", "memory_pressure", "upstream_timeout", "crash_or_restart"} <= ids

def test_excerpt_is_redacted():
    excerpt = analyze_logs(SAMPLE)["redacted_log_excerpt"]
    assert "hunter2" not in excerpt and "eyJhbGci" not in excerpt

def test_unclassified_errors_fallback():
    findings = analyze_logs("ERROR something odd happened")["findings"]
    assert [f["id"] for f in findings] == ["unclassified_errors"]
