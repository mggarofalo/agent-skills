#!/usr/bin/env python3
"""Read AT&T PDFs into a local inventory; no Ramp access or file mutations."""
import argparse
import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pdfplumber

DATE = r"[A-Za-z]{3,9}\s+\d{1,2},\s*\d{4}"


def unique_value(values, label, warnings):
    values = sorted(set(values))
    if len(values) != 1:
        warnings.append(f"Expected one {label}; found {values!r}")
        return None
    return values[0]


def iso_date(value):
    value = re.sub(r"\s+", " ", value)
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"Unrecognized date: {value}")


def inspect(path):
    warnings = []
    with pdfplumber.open(path) as pdf:
        text = "\n\n".join(page.extract_text() or "" for page in pdf.pages)
    issue = unique_value(
        [iso_date(v) for v in re.findall(r"Issue Date:\s*(" + DATE + ")", text)],
        "issue date", warnings,
    )
    accounts = re.findall(r"Account [Nn]umber:\s*([\d -]+)", text)
    suffix = unique_value(
        [re.sub(r"\D", "", v)[-4:] for v in accounts], "account suffix", warnings
    )
    totals = re.findall(r"Total due\s*\$([\d,]+\.\d{2})", text)
    total = unique_value([v.replace(",", "") for v in totals], "bill total", warnings)
    dates = re.findall(r"AutoPay is scheduled to debit your bank account on\s*(" + DATE + ")", text)
    dates += re.findall(r"AutoPay of \$[\d,.]+ is scheduled for\s*(" + DATE + ")", text)
    dates += re.findall(r"AutoPay is scheduled for:\s*(" + DATE + ")", text)
    payment = unique_value([iso_date(v) for v in dates], "scheduled AutoPay date", warnings)
    service = {"4031": "phone", "5117": "internet"}.get(suffix)
    if service is None:
        warnings.append("Unknown account; identify service manually")
    elif not re.search(r"\b" + ("Wireless" if service == "phone" else "Internet") + r"\b", text):
        warnings.append("Expected service label not found; inspect the bill")
    claim = None
    if total and service:
        amount = Decimal(total)
        if amount <= 0:
            warnings.append("Nonpositive bill total; reconcile credits manually")
        else:
            claim = format(min(amount, Decimal("75")) if service == "phone" else amount, ".2f")
    return {
        "file": str(path.resolve()),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "service": service,
        "account_suffix": suffix,
        "issue_date": issue,
        "bill_month": issue[:7] if issue else None,
        "bill_total": total,
        "claim_amount": claim,
        "scheduled_autopay_date": payment,
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=Path.home() / "Downloads")
    parser.add_argument("--pattern", default="ATTBill_*.pdf")
    args = parser.parse_args()
    rows = []
    for path in sorted(args.directory.expanduser().glob(args.pattern)):
        if path.is_file():
            try:
                rows.append(inspect(path))
            except Exception as exc:
                rows.append({"file": str(path.resolve()), "warnings": [f"Extraction failed: {exc}"]})
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
