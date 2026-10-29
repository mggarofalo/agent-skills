# Native Swift and SwiftUI patterns

Use this reference to choose an implementation and to review a proposed custom interaction. Confirm signatures and availability in the project's installed SDK.

## First-party sources

- [Swift API Design Guidelines](https://www.swift.org/documentation/api-design-guidelines/) for naming and call-site clarity.
- [The Swift Programming Language: Concurrency](https://docs.swift.org/swift-book/documentation/the-swift-programming-language/concurrency/) for tasks, actors, isolation, and `Sendable`.
- [SwiftUI documentation](https://developer.apple.com/documentation/swiftui/) and [SwiftUI updates](https://developer.apple.com/documentation/updates/swiftui) for current and newly introduced APIs.
- [Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/) for platform behavior and presentation choices.
- [List](https://developer.apple.com/documentation/swiftui/list) and [EditMode](https://developer.apple.com/documentation/swiftui/editmode) for selection, deletion, and reordering.
- [Input and event modifiers](https://developer.apple.com/documentation/swiftui/view-input-and-events) for `swipeActions`, `refreshable`, focus, keyboard, and interaction APIs.
- [FocusState](https://developer.apple.com/documentation/swiftui/focusstate) for programmatic field focus.
- [Model data](https://developer.apple.com/documentation/swiftui/model-data) for state, bindings, Observation, and environment ownership.
- [Accessibility fundamentals](https://developer.apple.com/documentation/swiftui/accessibility-fundamentals) for built-in semantics and targeted enhancements.
- [Performance analysis](https://developer.apple.com/documentation/swiftui/performance-analysis) and [Improving app responsiveness](https://developer.apple.com/documentation/xcode/improving-app-responsiveness) for SwiftUI updates, hangs, hitches, and Instruments.

Prefer the documentation page for the exact symbol over a blog post or remembered sample. Use WWDC sessions and Apple sample code when the symbol page does not explain interaction semantics.

## Requirement-to-primitive guide

| Requirement | Start with | Common mistake to avoid |
| --- | --- | --- |
| Hierarchical navigation | `NavigationStack`, typed destinations, `NavigationLink` | Boolean navigation webs or tap gestures that push views manually |
| Modal create/edit flow | `sheet` or `fullScreenCover` containing `Form`; toolbar actions | A hand-built overlay or duplicated navigation shell |
| Primary field focus | `@FocusState` and `focused` set from presentation lifecycle | UIKit responder searches, arbitrary delays, or globally forcing focus |
| Search | `searchable`, suggestions, `searchFocused` | A custom text field that imitates navigation search |
| Editable collection | `List`, `ForEach`, `EditMode`, `EditButton`, `onDelete`, `onMove` | Owning scroll gestures or drawing editing controls over rows |
| Multiple selection | `List(selection:)` with stable hashable tags and edit mode | Long-press/drag gesture state machines for platform selection |
| Row actions | `swipeActions` with `Button`, `contextMenu`, accessibility actions | Custom offset/clip/corner animations that imitate swipe cells |
| Destructive confirmation | `Button(role: .destructive)`, `confirmationDialog` or `alert` | Color alone, an untyped action menu, or immediate irreversible work |
| Empty/filter-empty state | `ContentUnavailableView` | Spacer-based bespoke placeholders that do not adapt |
| Refresh | `refreshable` with an async operation | A custom pull gesture or blocking refresh on the main actor |
| Text and symbols | `Text`, `Label`, semantic fonts, SF Symbols | Font shrinking, fixed text heights, or decorative images without semantics |
| View state | `State`, `Binding`, Observation/environment based on ownership | Duplicated sources of truth synchronized by chains of `onChange` |
| Background work | `Task`, async functions, actors, task groups where appropriate | Blocking I/O or repeated CPU-heavy transforms in `body` |

## Custom-code decision record

When native composition does not satisfy the requirement, leave a short explanation in the issue, PR, architecture note, or code comment that answers:

- What user-visible requirement is missing from the native API?
- Which API and OS versions were evaluated?
- Why is styling or composition insufficient?
- Who owns accessibility, keyboard, scrolling, gesture arbitration, animation, and state restoration after customization?
- Which tests demonstrate both the missing native behavior and the custom behavior?
- What future API or deployment-target change would allow removal?

The explanation should justify behavior, not taste. “More control,” pixel matching, or uncertainty about the framework is not enough.

## Review signals

These searches help locate code that deserves examination:

```sh
rg -n 'DragGesture|LongPressGesture|simultaneousGesture|highPriorityGesture|gesture\(' .
rg -n 'GeometryReader|PreferenceKey|contentShape|clipShape|cornerRadius|offset\(' .
rg -n 'AnyView|UIViewRepresentable|UIViewControllerRepresentable|UIHostingController' .
rg -n '#if.*(os|targetEnvironment)|DispatchQueue\.main|Task\.detached' .
rg -n 'ForEach.*indices|\.sorted\(|\.filter\(|Dictionary\(grouping:' .
```

Treat matches as questions. `contentShape`, custom `Layout`, bridges, and manual derived-state caches all have valid uses. Inspect the requirement, surrounding native container, performance evidence, and platform tests before changing them.

## Lessons reflected from Shopping

- Native list selection and edit mode preserve platform multi-selection gestures and row behavior better than a parallel selection concept.
- `swipeActions` should own the row reveal and corner animation; custom clipping around each item can fragment a grouped list and break edge animations.
- `FocusState` can express create-versus-edit focus policy without responder workarounds.
- Repeated grouping, filtering, or relationship traversal during `body` evaluation can become a visible hang at realistic data volumes. Batch fetch and recompute when inputs change, then verify with Instruments.
- Simulator and device test data can differ because app and test-runner sandboxes differ. Resolve capabilities and writable locations at runtime rather than compiling different product semantics for simulator and hardware.
