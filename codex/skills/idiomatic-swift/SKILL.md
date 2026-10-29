---
name: idiomatic-swift
description: Build and review Swift and SwiftUI code using current language conventions and native Apple platform behaviors. Use for Swift implementation, refactoring, or review, especially lists, forms, navigation, selection, gestures, focus, accessibility, concurrency, persistence, and performance. Apply before introducing custom UI controls or interaction handling.
---

# Idiomatic Swift and SwiftUI

Make the result feel like an Apple-platform app and like Swift written by an experienced Swift developer. Preserve the product requirements; use the platform implementation that already supplies the required semantics whenever one exists.

## Establish the platform contract

Before designing an interaction or changing architecture:

1. Read the repository guidance, issue acceptance criteria, existing architecture, deployment target, Swift language mode, and Xcode/SDK versions.
2. Look up the relevant API in current first-party documentation. Start with Apple Developer Documentation and the Human Interface Guidelines for SwiftUI or UIKit behavior, and Swift.org for language semantics and API design. Do not rely on memory when an API is unfamiliar, version-sensitive, deprecated, or would replace custom code.
3. Check availability against the minimum deployment target. Compile a small use in the project when documentation and the installed SDK disagree.
4. Inspect nearby code for an established native pattern before adding another abstraction.

Read [references/native-patterns.md](references/native-patterns.md) when the task affects interaction design, state ownership, accessibility, concurrency, testing, or performance.

## Prefer semantic system components

Choose the control whose meaning matches the requirement. A native control brings platform gestures, animation, accessibility, focus, keyboard support, layout adaptation, and future OS behavior with it.

- Use `NavigationStack`, `NavigationLink`, `TabView`, toolbars, sheets, popovers, alerts, and `confirmationDialog` for their corresponding navigation and presentation jobs.
- Use `List`, `Form`, `Section`, `ForEach`, `ContentUnavailableView`, `searchable`, and `refreshable` for structured collections and forms.
- Use `Button`, `Toggle`, `Picker`, `TextField`, `TextEditor`, `Stepper`, `Menu`, `Label`, and SF Symbols instead of tap gestures on styled containers.
- Use `List(selection:)`, stable `.tag` values, `EditMode` or `EditButton`, `onDelete`, `onMove`, `swipeActions`, and `contextMenu` for list editing and batch selection.
- Use `@FocusState` with `focused` or `searchFocused` for programmatic focus. Let the product requirement decide whether a field initially receives focus.
- Use destructive button roles for destructive actions. Let the system provide destructive styling unless the product explicitly requires an additional supported tint.

Do not recreate an OS-owned interaction with gesture recognizers, geometry tracking, overlays, timers, or manual corner/background animation merely to approximate standard behavior. Examples include row selection, range selection, swipe actions, scrolling, reordering, keyboard avoidance, focus, navigation transitions, and Dynamic Type layout.

## Require evidence for custom behavior

Custom views are appropriate for product-specific presentation or behavior that the supported SDK does not provide. Before adding one:

1. Name the unmet requirement precisely.
2. Record the native APIs evaluated and the concrete gap in each.
3. Prototype the closest native composition and test it on the oldest supported OS and the current SDK.
4. Check VoiceOver, Voice Control, Switch Control where relevant, Dynamic Type, Reduce Motion, keyboard/focus, localization, appearance, and standard gestures.
5. Keep the custom layer as small as possible. Retain native semantic controls inside custom layout and avoid taking ownership of scrolling or gesture arbitration.

Prefer a documented UIKit bridge when UIKit has the canonical behavior that SwiftUI lacks. Isolate the bridge and explain when it can be removed. Do not use custom code solely to force identical pixels across OS releases.

## Write Swift that exposes intent

- Follow Swift API Design Guidelines and optimize for clarity at the call site.
- Prefer value types for values, reference types for shared identity, `let` for immutable bindings, and `guard` for early exits.
- Model finite state with enums and associated values rather than loosely related booleans and optionals.
- Use optionals, `throws`, and typed errors to represent absence and failure. Avoid sentinel values and ignored errors when behavior depends on success.
- Preserve stable identity in collections. Do not use an array index as identity for mutable or persisted rows.
- Avoid `AnyView`, type erasure, wrappers, and protocols until they solve a demonstrated composition or substitution problem.
- Keep one source of truth. Derive display state when cheap; cache or materialize it deliberately when measurement shows recomputation is expensive.
- Keep SwiftUI `body` and frequently evaluated properties cheap. Fetch related data in batches and compute grouping, filtering, and sorting once per input change instead of once per row.
- Keep UI state on the main actor. Move measurable CPU or blocking work away from the main actor with structured concurrency, while respecting persistence-context and `Sendable` boundaries.

## Validate behavior at the right level

Use previews for representative visual states and focused tests for domain behavior. Use unit tests for pure logic, hosted integration tests for persistence and framework boundaries, UI tests for user-visible flows, and Instruments or performance tests for responsiveness. Organize test selection with schemes, test plans, and test traits/tags where supported; do not change product semantics with simulator-only compilation branches.

Test observable behavior rather than the private shape of a custom workaround. Include the oldest supported OS and a current OS when native behavior or availability differs. For interaction work, validate touch, keyboard, accessibility, Dynamic Type, Reduce Motion, localization, and destructive confirmations in proportion to the change.

## Review existing code

During review, search for custom gestures, `contentShape`, geometry readers, fixed frames, manual edit state, type erasure, UIKit bridges, compile-time platform branches, synchronous persistence or file access, and sorting/filtering inside row builders. Each occurrence is a prompt to inspect, not an automatic defect. Keep it when it has a documented need and passes the relevant platform checks; replace it when a native API provides the required behavior.

In the review summary, state which first-party APIs and guidance informed the decision, which custom code remains and why, the supported OS range, and the validation performed.
