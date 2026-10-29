import argparse, json, sys
from pathlib import Path
from app.service import analyze
from app.aws_logs import fetch_logs, list_log_groups

def main():
    parser = argparse.ArgumentParser(description="AI Log Analyzer CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    local = sub.add_parser("file", help="Analyze a local log file")
    local.add_argument("path")
    local.add_argument("--no-ai", action="store_true")
    groups = sub.add_parser("groups", help="List CloudWatch log groups")
    aws = sub.add_parser("cloudwatch", help="Analyze a CloudWatch log group")
    aws.add_argument("log_group")
    aws.add_argument("--hours", type=int, default=1)
    aws.add_argument("--limit", type=int, default=1000)
    aws.add_argument("--no-ai", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "groups":
            print("\n".join(list_log_groups()))
            return
        if args.command == "file":
            raw = Path(args.path).read_text(errors="replace")
            result = analyze(raw, not args.no_ai)
        else:
            raw = fetch_logs(args.log_group, args.hours, args.limit)
            result = analyze(raw, not args.no_ai)
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
