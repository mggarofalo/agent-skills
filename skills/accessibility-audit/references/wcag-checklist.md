# WCAG 2.1 AA Quick Reference

Criteria organized by POUR principles. Each entry indicates whether it can be checked automatically via agent-browser (Auto), requires static source analysis (Static), or needs manual human review (Manual).

## Perceivable

| # | Criterion | Level | Description | Method |
|---|-----------|-------|-------------|--------|
| 1.1.1 | Non-text Content | A | All images, icons, and non-text content have text alternatives | Static (alt attr), Auto (accessible names) |
| 1.2.1 | Audio-only and Video-only | A | Prerecorded audio/video has alternatives (transcript/description) | Manual |
| 1.2.2 | Captions (Prerecorded) | A | Prerecorded video with audio has captions | Manual |
| 1.2.3 | Audio Description or Media Alternative | A | Prerecorded video has audio description or text alternative | Manual |
| 1.2.4 | Captions (Live) | AA | Live video with audio has captions | Manual |
| 1.2.5 | Audio Description (Prerecorded) | AA | Prerecorded video has audio description | Manual |
| 1.3.1 | Info and Relationships | A | Structure and relationships conveyed visually are available programmatically (landmarks, headings, tables, form labels) | Auto (landmarks, headings, tables, labels in a11y tree) |
| 1.3.2 | Meaningful Sequence | A | Reading order is correct and meaningful | Auto (partial — DOM order check), Manual (visual vs. DOM) |
| 1.3.3 | Sensory Characteristics | A | Instructions don't rely solely on shape, size, visual location, orientation, or sound | Manual |
| 1.3.4 | Orientation | AA | Content doesn't restrict display to a single orientation unless essential | Manual |
| 1.3.5 | Identify Input Purpose | AA | Input fields that collect user data have programmatically determinable purpose (autocomplete attributes) | Static (autocomplete attr) |
| 1.4.1 | Use of Color | A | Color is not the only visual means of conveying information | Manual |
| 1.4.2 | Audio Control | A | Audio that plays automatically can be paused/stopped or volume controlled | Manual |
| 1.4.3 | Contrast (Minimum) | AA | Text has at least 4.5:1 contrast ratio (3:1 for large text) | Manual (screenshot inspection) |
| 1.4.4 | Resize Text | AA | Text can be resized up to 200% without loss of content or function | Manual |
| 1.4.5 | Images of Text | AA | Text is used instead of images of text (unless essential) | Manual |
| 1.4.10 | Reflow | AA | Content reflows at 320px width without horizontal scrolling | Manual |
| 1.4.11 | Non-text Contrast | AA | UI components and graphical objects have at least 3:1 contrast ratio | Manual |
| 1.4.12 | Text Spacing | AA | No loss of content when text spacing is increased (line height 1.5x, paragraph spacing 2x, letter spacing 0.12em, word spacing 0.16em) | Manual |
| 1.4.13 | Content on Hover or Focus | AA | Hover/focus-triggered content is dismissible, hoverable, and persistent | Manual |

## Operable

| # | Criterion | Level | Description | Method |
|---|-----------|-------|-------------|--------|
| 2.1.1 | Keyboard | A | All functionality is operable via keyboard | Auto (keyboard nav test), Static (onClick without onKeyDown) |
| 2.1.2 | No Keyboard Trap | A | Focus can be moved away from any component using keyboard | Auto (keyboard nav test — focus not stuck) |
| 2.1.4 | Character Key Shortcuts | A | Single-character key shortcuts can be turned off or remapped | Manual |
| 2.2.1 | Timing Adjustable | A | Time limits can be turned off, adjusted, or extended | Manual |
| 2.2.2 | Pause, Stop, Hide | A | Moving, blinking, scrolling, or auto-updating content can be paused/stopped | Manual |
| 2.3.1 | Three Flashes or Below | A | Content doesn't flash more than 3 times per second | Manual |
| 2.4.1 | Bypass Blocks | A | Skip navigation mechanism exists to bypass repeated content | Auto (check for skip link in a11y tree) |
| 2.4.2 | Page Titled | A | Pages have descriptive, unique titles | Auto (`agent-browser get title`) |
| 2.4.3 | Focus Order | A | Focus order preserves meaning and operability | Auto (keyboard tab test), Static (positive tabIndex) |
| 2.4.4 | Link Purpose (In Context) | A | Link purpose is determinable from link text or context | Auto (check link text in a11y tree) |
| 2.4.5 | Multiple Ways | AA | More than one way to locate a page within a set of pages | Manual |
| 2.4.6 | Headings and Labels | AA | Headings and labels describe topic or purpose | Auto (heading presence and hierarchy in a11y tree) |
| 2.4.7 | Focus Visible | AA | Keyboard focus indicator is visible | Auto (screenshot after Tab — check for focus ring) |
| 2.5.1 | Pointer Gestures | A | Multipoint or path-based gestures have single-pointer alternatives | Manual |
| 2.5.2 | Pointer Cancellation | A | Down-event doesn't trigger function; up-event can abort | Manual |
| 2.5.3 | Label in Name | A | Visible label is included in the accessible name | Auto (compare visible text to accessible name in tree) |
| 2.5.4 | Motion Actuation | A | Motion-triggered functions have UI alternatives and can be disabled | Manual |

## Understandable

| # | Criterion | Level | Description | Method |
|---|-----------|-------|-------------|--------|
| 3.1.1 | Language of Page | A | Default human language of page is programmatically determinable | Auto (`document.documentElement.lang`) |
| 3.1.2 | Language of Parts | AA | Language of passages/phrases is identified when different from page default | Manual |
| 3.2.1 | On Focus | A | Receiving focus doesn't initiate unexpected change of context | Auto (partial — keyboard nav test) |
| 3.2.2 | On Input | A | Changing a UI component doesn't automatically cause a context change unless user is warned | Manual |
| 3.2.3 | Consistent Navigation | AA | Navigation mechanisms repeated on multiple pages are in consistent order | Auto (compare nav structure across pages) |
| 3.2.4 | Consistent Identification | AA | Components with same functionality are identified consistently across pages | Manual |
| 3.3.1 | Error Identification | A | Input errors are identified and described to the user in text | Manual |
| 3.3.2 | Labels or Instructions | A | Labels or instructions are provided when user input is required | Auto (form field labels in a11y tree) |
| 3.3.3 | Error Suggestion | AA | If an input error is detected, suggestions for correction are provided | Manual |
| 3.3.4 | Error Prevention (Legal, Financial, Data) | AA | Submissions that cause legal/financial commitments are reversible, verified, or confirmed | Manual |

## Robust

| # | Criterion | Level | Description | Method |
|---|-----------|-------|-------------|--------|
| 4.1.1 | Parsing | A | (Obsolete in WCAG 2.2, but still in 2.1) No duplicate IDs, proper nesting | Static (grep for duplicate IDs) |
| 4.1.2 | Name, Role, Value | A | All UI components have accessible names, roles, and states | Auto (a11y tree — buttons, dialogs, form controls have names) |
| 4.1.3 | Status Messages | AA | Status messages are programmatically determinable via roles (alert, status, log) without receiving focus | Auto (check for live regions in a11y tree) |

## Method Legend

| Method | Description |
|--------|-------------|
| **Auto** | Can be checked automatically via agent-browser accessibility tree or page-level commands |
| **Static** | Can be checked by grepping/reading source files |
| **Manual** | Requires human judgment — noted in report but not auto-checked |
