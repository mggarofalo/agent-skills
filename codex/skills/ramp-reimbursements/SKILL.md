---
name: ramp-reimbursements
description: Find and download Michael's missing AT&T phone and internet bills, maintain a local PDF cache, and prepare Ramp reimbursement drafts using payment dates and the $75 phone cap. Use for monthly bill collection, reimbursement preparation, or catching up on missed months.
---

# Monthly Ramp reimbursements

Collect missing bills and prepare saved, reviewable drafts with the matching original PDFs attached. Use the durable cache at `~/Documents/Codex/BillCache/att`, importing relevant PDFs from Downloads first. A bill-collection-only request stops after updating the cache. Do not submit requests or schedule recurring work unless the user separately asks. Michael has requested collection from his AT&T accounts, local caching, and draft preparation in Ramp; do not reconfirm those routine steps when invoked within that scope.

## Michael's defaults

These are preferences and accounting values confirmed in September 2026. Apply later user corrections and check Ramp's current requirements.

| Item | Cell phone | Internet |
|---|---|---|
| Merchant | AT&T | AT&T |
| Account suffix / typical filename | 4031 / `ATTBill_4031_*.pdf` | 5117 / `ATTBill_5117_*.pdf` |
| Requested amount | $75 per monthly bill, or the bill total if lower | Full current bill amount; no user-specified cap |
| Intacct category | 68005 — Cell Phone | 68010 — Data/Internet |
| Memo | Cell Phone Reimbursement - Month YYYY | Internet Reimbursement - Month YYYY |

Both use **IT-001 — IT Software Engineering** and **9831 — NetData (Justice Tech)**. Other NetData entities are different locations. Prior requests used no spend fund; in this session Ramp displayed `Reimburse from: None` under its automatic fund policy. Preserve current valid defaults rather than selecting an unrelated fund.

The memo month identifies the bill's issue month. The transaction date identifies its payment and may fall in the following month. Internet was $47.13 through July 2026 and $51.13 in August; always read each bill instead of reusing either amount. A missing internet cap is a user preference, not proof of company policy; honor any applicable restriction actually displayed by Ramp.

## Reconcile before creating

1. Import Downloads into the cache and plan missing expected bills using [references/bill-collection.md](references/bill-collection.md). Follow that reference to collect missing originals through AT&T's current website. If the cache covers the expected periods, skip portal visits and downloads. On authentication or download failure, continue with cached bills and report the missing ones.
2. Reconcile the verified cache inventory with existing Ramp reimbursements, including **drafts**, completed requests, pending approvals, and returned or rejected requests. Review the most recent request of each type to confirm categories and the billing period already covered. Do not infer the last covered bill from the reimbursement date alone. The cache is evidence of possession, not evidence of a reimbursement's status; always check Ramp.
   The cache helper uses `scripts/inventory_bills.py` to extract new PDFs with `pdfplumber`; run it with the bundled Python runtime located by `load_workspace_dependencies`. Resolve extraction warnings by reading the PDF before creating a request. Use the PDF skill for visual inspection. Cached inventory includes service, account suffix, issue date, current total, and scheduled AutoPay date.
3. Match requests by service/account and bill period, using attached receipts and memos to resolve ambiguity. Same merchant and amount do not establish a duplicate. PDFs with identical hashes are copies of one bill; revised PDFs for the same period need reconciliation, not two claims.
4. Prepare only missing requests. Resume an existing unfinished draft for that bill. After any uncertain upload or save, inspect the draft list before retrying. If its existence remains ambiguous, stop creation for that bill and report the ambiguity; continue independent bills.

## Dates and pending payments

- Prefer an actual payment date when evidence ties it to this bill; otherwise use this bill's listed AutoPay date, as Michael requested. A later bill's matching payment acknowledgement can corroborate it. Flag a material discrepancy instead of silently selecting a different date.
- The `Payment, … Thank you!` entry in a bill's account summary normally pays the **previous** bill. Do not use that entry as the current bill's payment date.
- Keep actual payments and scheduled AutoPay distinct. Do not claim a scheduled debit has already cleared.
- Ramp blocked future transaction dates in the observed workflow. For a future payment, keep the receipt, amount, memo, and accounting as a draft with the date unset. Append `- Pending AutoPay Month D, YYYY` to its memo. Do not substitute the issue date or today's date without a user instruction. On a later run, revisit this draft when its listed payment date is no longer future, enter the date, remove the pending note, and verify the saved result; do not create a duplicate.
- Previously prepared pending example: August 2026 internet, $51.13, AutoPay September 15, 2026. This is a historical clue for reconciliation, not a permanent instruction to recreate it or assume it remains unfinished.

## Prepare in Ramp

Use an available Ramp connector if it exposes the necessary operations. Otherwise use the user's existing Ramp tab with the supported computer-use APIs. Read [references/ramp-ui.md](references/ramp-ui.md) for the observed Safari workflow and input pitfalls.

Upload one original PDF per reimbursement. Batch upload is useful when Ramp creates a separate draft per file; verify the selected filenames and resulting count. Ramp's receipt extraction is a starting point: correct the amount, date, memo, category, department, and location from the reconciled inventory. In particular, overwrite each phone bill's extracted full amount with its capped claim amount **before treating the draft as complete**.

Match each draft's receipt preview to its bill. Wait for saving to finish, leave the draft, and verify persisted fields by reopening it or reading the reimbursement list. A value visible while editing is not evidence it saved: a future date appeared in the input but disappeared after reopening during the original session.

## Final verification and handoff

Require exactly one request per newly claimed bill period, seven or any other count only when supported by the current inventory. Verify:

- All requested phone amounts are at or below $75, and all internet amounts match their current bills.
- Every ready draft has its intended payment date, service/month memo, accounting values, and matching receipt.
- Existing pending drafts were reused; future-dated drafts remain clearly pending.
- The persisted count and totals agree with the reconciled inventory. Distinguish the amount ready now from the pending amount.

Leave Ramp on the reimbursement list after draft preparation. Report bills newly downloaded versus reused, any missing or revised bills, the next expected checks when useful, the number of drafts ready and their total, pending requests and dates, and that nothing was submitted. Do not describe a draft with an unset required date as ready to submit.
