#!/usr/bin/env python3
"""Cache original AT&T PDFs and plan portal checks. No network or Ramp writes."""
import argparse
from contextlib import contextmanager
from datetime import date, timedelta
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

# Existing cache location (created under Codex); override with ATT_BILL_CACHE.
DEFAULT_ROOT = Path(os.environ.get("ATT_BILL_CACHE") or Path.home() / "Documents/Codex/BillCache/att")
ACCOUNTS = {
    "phone": {"suffix": "4031", "issue_day": 15, "posting_grace_days": 2},
    "internet": {"suffix": "5117", "issue_day": 24, "posting_grace_days": 2},
}


def month(value):
    if not re.fullmatch(r"\d{4}-\d{2}", value):
        raise argparse.ArgumentTypeError("Month must be YYYY-MM")
    try:
        date.fromisoformat(value + "-01")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return value


def next_month(value):
    start = date.fromisoformat(value + "-01")
    return (start.replace(day=28) + timedelta(days=4)).strftime("%Y-%m")


def check_date(period, account):
    return date.fromisoformat(f"{period}-{account['issue_day']:02d}") + timedelta(days=account["posting_grace_days"])


@contextmanager
def locked(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def load(root):
    path = root / "manifest.json"
    if not path.exists():
        return {"version": 1, "accounts": ACCOUNTS, "bills": [], "checks": {}}
    data = json.loads(path.read_text())
    if data.get("version") != 1 or not isinstance(data.get("bills"), list) or not isinstance(data.get("checks"), dict):
        raise ValueError("Unsupported or damaged manifest; preserve it and repair before continuing")
    for service, account in data["accounts"].items():
        if service not in ACCOUNTS or account["suffix"] != ACCOUNTS[service]["suffix"]:
            raise ValueError("Unexpected account configuration; reconcile before continuing")
        if not 1 <= account["issue_day"] <= 28 or not 0 <= account["posting_grace_days"] <= 7:
            raise ValueError("Invalid expected bill schedule")
    if set(data["accounts"]) != set(ACCOUNTS):
        raise ValueError("Missing account configuration")
    return data


def save(root, data):
    fd, name = tempfile.mkstemp(prefix=".manifest-", suffix=".json", dir=root)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, root / "manifest.json")
    finally:
        Path(name).unlink(missing_ok=True)


def cached_path(root, row):
    path = (root / row["file"]).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Cached path escapes cache root")
    return path


def healthy(root, row):
    path = cached_path(root, row)
    return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]


def store_pdf(root, row, content):
    path = cached_path(root, row)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".bill-", suffix=".pdf", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def import_pdfs(root, data, sources, pattern):
    results = {"imported": [], "reused": [], "repaired": [], "errors": []}
    files = set()
    for source in sources:
        source = source.expanduser()
        if source.is_dir():
            files.update(p.resolve() for p in source.glob(pattern) if p.is_file())
        elif source.is_file():
            files.add(source.resolve())
        else:
            results["errors"].append({"file": str(source), "reason": "Source does not exist"})
    for path in sorted(files):
        try:
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            existing = next((r for r in data["bills"] if r["sha256"] == digest), None)
            if existing:
                if healthy(root, existing):
                    results["reused"].append(existing["file"])
                else:
                    store_pdf(root, existing, content)
                    results["repaired"].append(existing["file"])
                continue
            from inventory_bills import inspect
            row = inspect(path)
            if row["warnings"]:
                raise ValueError("; ".join(row["warnings"]))
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest or row["sha256"] != digest:
                raise ValueError("Source changed while reading; retry with the complete PDF")
            row["file"] = f"bills/{row['service']}/{row['bill_month']}/{digest}.pdf"
            row["original_filename"] = path.name
            row["cached_on"] = date.today().isoformat()
            store_pdf(root, row, content)
            data["bills"].append(row)
            save(root, data)
            results["imported"].append(row["file"])
        except Exception as exc:
            results["errors"].append({"file": str(path), "reason": str(exc)})
    return results


def plan(root, data, today, since=None):
    result = {"as_of": today.isoformat(), "cache_root": str(root), "bills": [], "conflicts": [], "damaged": [], "check_now": [], "deferred": [], "next_expected": [], "needs_baseline": []}
    valid = {}
    for row in data["bills"]:
        if healthy(root, row):
            key = (row["service"], row["bill_month"])
            valid.setdefault(key, []).append(row)
            result["bills"].append({**row, "file": str(cached_path(root, row))})
        else:
            result["damaged"].append(row["file"])
    for (service, period), rows in valid.items():
        if len(rows) > 1:
            result["conflicts"].append({"service": service, "bill_month": period, "files": [r["file"] for r in rows]})
    for service, account in data["accounts"].items():
        known = [r["bill_month"] for r in data["bills"] if r["service"] == service]
        if not known and not since:
            result["needs_baseline"].append(service)
            continue
        period = since or min(known)
        while check_date(period, account) <= today:
            if (service, period) not in valid:
                entry = {"service": service, "account_suffix": account["suffix"], "bill_month": period, "expected_issue_date": f"{period}-{account['issue_day']:02d}"}
                last_check = data["checks"].get(f"{service}:{period}")
                if last_check and date.fromisoformat(last_check["retry_on"]) > today:
                    result["deferred"].append({**entry, **last_check})
                else:
                    result["check_now"].append(entry)
            period = next_month(period)
        # A bill imported before its usual posting date needs no additional check.
        while (service, period) in valid:
            period = next_month(period)
        result["next_expected"].append({"service": service, "bill_month": period, "expected_issue_date": f"{period}-{account['issue_day']:02d}", "check_on": check_date(period, account).isoformat()})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    imp = sub.add_parser("import", help="Copy verified originals; preserve Downloads")
    imp.add_argument("sources", type=Path, nargs="+")
    imp.add_argument("--pattern", default="ATTBill_*.pdf")
    planning = sub.add_parser("plan", help="Verify cache and list missing expected bills")
    planning.add_argument("--on", type=date.fromisoformat, default=date.today())
    planning.add_argument("--since", type=month, help="First bill month to track if no baseline exists")
    check = sub.add_parser("unavailable", help="Record a verified portal result, never a login failure")
    check.add_argument("service", choices=ACCOUNTS)
    check.add_argument("bill_month", type=month)
    check.add_argument("--on", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    with locked(root):
        data = load(root)
        if args.command == "import":
            result = import_pdfs(root, data, args.sources, args.pattern)
        elif args.command == "plan":
            result = plan(root, data, args.on, args.since)
        else:
            if args.on > date.today():
                parser.error("Cannot record a portal check in the future")
            if check_date(args.bill_month, data["accounts"][args.service]) > args.on:
                parser.error("Bill is not yet expected; no unavailable record needed")
            if any(r["service"] == args.service and r["bill_month"] == args.bill_month and healthy(root, r) for r in data["bills"]):
                parser.error("Bill is already cached; do not record it as unavailable")
            key = f"{args.service}:{args.bill_month}"
            result = {"checked_on": args.on.isoformat(), "retry_on": (args.on + timedelta(days=3)).isoformat(), "result": "not_available"}
            data["checks"][key] = result
            save(root, data)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
