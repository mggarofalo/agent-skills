# Ramp: observed workflow

These notes come from a September 2026 session that drove Ramp in Safari through desktop automation. Treat them as navigation hints, not guarantees about current controls. Use Claude in Chrome (load `/anthropic-skills:chrome-browser` first); fall back to computer use (`/anthropic-skills:computer-use`) only for steps Chrome cannot do. Re-read the page after every action. Do not reuse element references from an earlier page state, private endpoints, browser storage, or the original session's reimbursement IDs.

## Finding the session

- Look for an existing signed-in Ramp tab in Chrome first. If Ramp is open only in another browser, either sign in to Ramp in Chrome (Michael completes any login prompt) or fall back to computer use on that browser.

## Navigation

- My expenses → Reimbursements contains saved drafts and completed requests. New reimbursement may show a personal-card connection offer; Skip continues to receipt upload. Do not connect a financial account for this task.
- A required address form appeared once. Use current confirmed address information from the authorized bills if it is still applicable. Autocomplete filled city, state, and ZIP but left the street blank; inspect the completed form before continuing.
- `Have multiple receipts? … click to upload` creates separate drafts. From the draft editor, `Create another reimbursement` → `Upload receipt` opens the batch upload area.

## Uploading receipts

- Prefer uploading the cached PDF straight to the page's file input from Chrome when the tool supports it. Check the selected filenames and count before confirming the upload.
- If a native file chooser opens instead, that dialog is outside the web page; handle it with computer use. If unrelated files make selection awkward, copy only the unclaimed original PDFs to a task-local staging directory and choose from there. Do not alter or remove the Downloads or cache originals.
- In the native chooser, rapid keystrokes lost some selections. Extending the selection one file at a time (Shift+Down, then re-reading the dialog) reliably selected a contiguous batch. Verify the final count; do not assume repeated keystrokes selected everything. Cmd+Shift+Down opened/uploaded the selected files rather than extending the range. Go To Folder accepted a typed path when pasting timed out.

## Entering values

- Ramp's text inputs are controlled components. Setting a field's value directly cleared it without reliably saving the new value, and typing character by character sometimes truncated a memo while the field re-rendered. Clicking into the field, selecting all, and pasting the complete value reliably entered amounts, memos, and dates. Click away afterward and read the field back.
- Search accounting dropdowns by exact code: `68005`, `68010`, `IT-001`, and `9831`. Select the matching label after results load. A broad `NetData` search showed multiple entities with only the first exposed to accessibility; exact-code search avoided selecting the wrong entity.
- Some selected accounting values were missing from the accessibility tree. A screenshot revealed them. The reimbursement list exposes the saved category, department, and location as readable cells, which makes it useful for final verification.

## Saving and dates

- The editor saves drafts automatically and has a separate Submit button. Do not click Submit merely to validate a draft. The list's `Submit` action is also a submission control.
- Future days were disabled in the date picker. Typed future dates did not persist even though the rest of the draft saved. Verify dates after navigating away, not just in the input.
