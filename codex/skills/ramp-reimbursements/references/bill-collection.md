# Bill collection and local cache

The cache is operational data outside the skill repository: `~/Documents/Codex/BillCache/att`. Keep personal bills and its manifest out of Git. Store original PDF bytes, not screenshots or browser printouts. Copy from Downloads, preserving those originals unless Michael asks to remove them.

## Expected schedule

| Service | Account suffix | Expected bill issue | First routine portal check | Typical following-month AutoPay |
|---|---|---|---|---|
| Phone | 4031 | 15th | 17th | 4th |
| Internet | 5117 | 24th | 26th | Around 15th |

These are expectations derived from February–August 2026, not payment evidence. Internet AutoPay included the 14th and 18th. Always take transaction dates from the actual bill/payment evidence. The two-day posting grace avoids premature routine checks; check earlier if the user explicitly requests it or a visible AT&T notice says the bill is ready. An expected date does not authorize fabricating a bill or reimbursement.

The manifest stores issue-day and posting-grace expectations per account. Update them only if new evidence establishes a changed cycle. It also retains each bill's actual issue and scheduled AutoPay dates. This skill runs when invoked; these expectations do not create a scheduled task.

## Cache commands

Use the Python runtime from `load_workspace_dependencies`. Below, `$BILL_PYTHON` denotes that executable, and `$BILL_SKILL` the installed skill directory; set task-specific shell variables with proper quoting.

```sh
"$BILL_PYTHON" "$BILL_SKILL/scripts/bill_cache.py" import "$HOME/Downloads"
"$BILL_PYTHON" "$BILL_SKILL/scripts/bill_cache.py" plan
```

Directory imports default to `ATTBill_*.pdf`; an explicit PDF path works regardless of its downloaded filename. Use an explicit path for a new `bill.pdf` rather than broadening discovery to unrelated documents. The helper copies originals into `bills/<service>/<YYYY-MM>/<sha256>.pdf`, retains the source filename and extracted facts in `manifest.json`, and reuses an existing hash without re-extracting or copying it.

`plan` verifies the cached bytes and returns:

- `bills`: healthy PDFs with absolute paths and metadata for Ramp reconciliation.
- `check_now`: missing expected periods to look for in AT&T.
- `deferred`: previously confirmed unavailable periods still inside the three-day retry interval.
- `next_expected`: upcoming routine checks per account.
- `conflicts`: multiple different PDFs for one account/period. Preserve both and compare issue dates, amounts, and portal revision labels; do not submit both or silently replace the original.
- `damaged`: missing files or hash mismatches. Import a good Downloads copy to repair them before redownloading; otherwise retrieve that bill again even if the manifest says it was cached.
- `needs_baseline`: an account with no cached history. Reconcile Ramp and the requested catch-up range, then use `plan --since YYYY-MM` for the first period to collect. With existing cache history, the plan checks gaps starting with each account's earliest cached month. It does not automatically fetch older already-reimbursed history.

After downloading an original:

```sh
"$BILL_PYTHON" "$BILL_SKILL/scripts/bill_cache.py" import "/actual/downloaded/bill.pdf"
"$BILL_PYTHON" "$BILL_SKILL/scripts/bill_cache.py" plan
```

The import must report a verified cached bill with the expected account and month. A download-button click, login page saved as PDF, partial browser download, or filename alone is not success. Resolve extraction errors without attaching the unverified file. Already cached different bytes for the same period remain visible as a conflict. A malformed manifest causes an error; preserve it and recover from the PDFs rather than resetting history to an empty cache.

Only after successfully viewing the correct account's bill list and confirming an expected month's PDF is not available, record:

```sh
"$BILL_PYTHON" "$BILL_SKILL/scripts/bill_cache.py" unavailable phone 2026-09
```

This example records today's real check and a retry date three days later; substitute the observed service/month. Do not record unavailable on login failure, CAPTCHA, network failure, an incomplete page, or after looking at the wrong account. Do not invent a successful download/check in the manifest. Explicit user requests to recheck or a new availability notice can override the interval.

`--root /path` before the command supports an isolated test cache. `plan --on YYYY-MM-DD` is for previews/tests; do not treat a preview as a completed portal check. Normal operation uses the current local date.

## AT&T portal workflow

Use an available AT&T connector if it supports account bills. Otherwise use the supported computer-use APIs and inspect current UI. Prefer an existing signed-in AT&T tab. If none is available, open the official **https://www.att.com/myatt/** entry point (also printed on the bills). Normal sign-in is within the requested collection scope; allow the user to complete any authentication challenge that requires their input. Never store credentials, cookies, MFA codes, or temporary authenticated download URLs in the cache.

1. Reuse healthy cached periods. Visit the portal only for due missing bills, repair, explicit refresh, or a known revision. A monthly invocation does not require downloading the latest cached PDF again.
2. Select the phone or internet account by the observed account suffix. Linked accounts may share one login but expose separate bill histories. Read the current bill/history controls; do not rely on fixed selectors or undocumented endpoints.
3. Locate missing periods from `check_now`. Compare the portal's displayed date/amount with the intended period. Inspect newer available bills if shown and cache them, even if posted early. Avoid bulk downloading all billing history.
4. Choose the original bill PDF download and wait until the file is complete. If the browser asks for a destination, use a task-local download directory and then import. If it downloads to Downloads, identify the actual new file through the supported download UI or filesystem; do not infer its name from a prior run.
5. Import immediately, verify its account/period, and rerun the plan. If the browser shows an unexpected revision of a cached bill, retain it as a separate version for comparison. Do not erase or overwrite an attached historical bill.
6. On an uncertain download, inspect local downloads/cache and the portal result before retrying once. If still unresolved, report that bill as blocked and continue other accounts or cached bills. Do not repeatedly click download or attempt an authentication workaround.

The cache helper performs no network or browser operations. The agent carries out the live portal interaction, so website changes and login challenges remain visible to the user.
