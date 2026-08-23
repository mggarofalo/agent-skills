---
name: qlmarkdown
description: >
  Render Markdown to standalone styled HTML with qlmarkdown_cli (QLMarkdown.app, cmark-gfm).
  TRIGGER when: converting .md to HTML, previewing Markdown in a browser, producing a
  self-contained HTML file from Markdown, or checking how a file will look in Finder's
  Quick Look. Not for reading Markdown — just cat it.
allowed-tools: Bash, Read
user_invocable: true
argument: "<file.md> [output.html] — render Markdown to styled HTML"
---

# qlmarkdown_cli

Ships inside QLMarkdown.app. Parses with cmark-gfm (same engine as GitHub), highlights
code with André Simon's Highlight, and emits one self-contained HTML file.

## Always pass --app

The stylesheet lives in the app bundle, and the tool finds it relative to argv[0]. The
Homebrew symlink on `PATH` therefore emits **unstyled HTML with an empty `<style>` block**
— silently, exit 0.

```bash
qlmarkdown_cli --app /Applications/QLMarkdown.app in.md > out.html
```

`a.md` → 1,356 bytes bare via the symlink, 15,673 bytes styled with `--app`. Invoking the
real path (`/Applications/QLMarkdown.app/Contents/Resources/qlmarkdown_cli`) also works.

## Defaults worth overriding

Check any of these with `--show-settings`; flags override the app's saved settings.

| Flag | Default | Override when |
|---|---|---|
| `--yaml` | `rmd` (only .rmd/.qmd) | **Any file with front matter.** In a `.md` the `---` becomes an `<hr>` and the keys render as a stray `<h2>`. Pass `--yaml all` for a clean key/value table. |
| `--appearance` | `auto` | Baked in at generation time, not a media query — pass `light` or `dark` for deterministic output. |
| `--math-embed` / `--mermaid-embed` | `off` (CDN `<script>`) | Output must work offline. |
| `--strikethrough` | `single` tilde | Matching GitHub: `--strikethrough double`. |
| `--inline-images` | `on` | Already self-contained; turn `off` only to keep the file small. |

`--highlight` (`==mark==` spans, off) and `--syntax-highlight` (fenced code, on) are
different flags. Don't confuse them.

## Invocation shapes

```bash
# stdout
qlmarkdown_cli --app /Applications/QLMarkdown.app --yaml all in.md

# one file to a path, or many to a directory (-o dir is required for 2+ inputs)
qlmarkdown_cli --app /Applications/QLMarkdown.app -o out.html in.md
qlmarkdown_cli --app /Applications/QLMarkdown.app -o build/ *.md

# open a preview
qlmarkdown_cli --app /Applications/QLMarkdown.app in.md > /tmp/p.html && open /tmp/p.html
```

**No stdin.** Piping prints the help text and exits 0. Write a temp file first.

Exit 1 on a missing file, or on 2+ inputs without `-o <dir>`. `-v` is only meaningful
with `-o`, and its banner goes to stdout — redirect it away when capturing HTML.

## Where this skill stops

Output carries a QLMarkdown footer link; strip it downstream if unwanted. Themes,
custom CSS, and the Quick Look extension itself are configured in the GUI app, not here.
