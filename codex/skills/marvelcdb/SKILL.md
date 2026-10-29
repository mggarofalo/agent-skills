---
name: marvelcdb
description: >
  MarvelCDB command-line client — Marvel Champions card, pack, faction, FAQ, decklist
  and deck data, piped locally from a disk cache.
  TRIGGER when: the user mentions Marvel Champions, MarvelCDB, marvelcdb, card codes like
  01001a, heroes/allies/aspects/upgrades/villains as game data, deckbuilding, decklists,
  taboo lists, or asks to look up, filter, export or script against Marvel Champions cards.
  Also when a project reads card data from JSON/CSV that came from MarvelCDB.
  Covers install, the command map, output formats, jq pipelines and OAuth2 deck editing.
---

# MarvelCDB CLI

`marvelcdb` is a Go client for [MarvelCDB](https://marvelcdb.com). Reads need no
account. The whole card corpus is one ~7 MB download that it caches on disk and
revalidates conditionally, so after the first query everything is local and fast.

Source: `github.com/mggarofalo/marvelcdb-cli`.

**Its per-command help is good — better than most.** `marvelcdb <command> --help`
explains the filter semantics, the deck-editing pattern, the credential story and
the known upstream bugs, in prose. Read it rather than guessing, and prefer it to
this skill wherever the two disagree. What follows is the part help does not
cover.

## Things the help does not tell you

These came from running the CLI, not from reading it.

**A single result is a JSON object; multiple results are an array.**
`cards get 01050 -o json` gives `{...}`, but `cards get 01050 01051` gives
`[{...},{...}]`. The same rule governs `decklists get`, `decks get` and
`mydecks get` (`internal/cli/decklists.go:210`). Normalise with `jq '[.] | flatten'`
when the count is not known ahead of time.

**`cards list` applies two exclusions before you filter anything.** It returns
1,814 rows by default. `--duplicates` takes it to 2,155 by adding reprints of
cards from earlier packs, and `--encounter` takes it to 4,105 by adding villains,
minions, main schemes and modular sets. 2,155 is the corpus size that
`cache warm` reports, so a count that "should" match the cache and does not is
usually the reprint filter, not a bug.

**Fields are sparse, and jq fails two different ways because of it.** A hero has
no `cost` key at all; a resource has no `health`. Numeric comparison does *not*
error — jq sorts a missing key below every number, so `select(.cost >= 3)` quietly
drops costless cards while `select(.cost < 3)` quietly sweeps them all in. On a
200-card sample that is 40 rows of silent contamination. String functions do
error outright: `.text | test("Overkill")` dies on the first card with no text.
Default on both sides — `(.cost // 0)` and `(.text? // "")` — and decide which
way you want missing keys to fall.

**"The other side of a card" means two different things, and `--back` is usually
the wrong one.** A hero and their alter-ego are two separate card codes linked by
`linked_to_code` — Spider-Man is `01001a`, Peter Parker is `01001b`, and both
report `double_sided: false`. Use `cards get 01001a --with-linked` to get the
pair. `--back` and `backimagesrc` are a different concept: a printed reverse
image, which only 59 of 4,105 cards have, 57 of them Main Schemes. Asking for
`cards image 01001a --back` is not a silent no-op — it exits 1 with "card 01001a
has no back image on MarvelCDB" — but running a whole hero set through `--back`
will fail on essentially every card.

**`--with-cards` only does anything with `-o text`.** In JSON it is silently a
no-op and slots stay as card codes. The help is actively misleading here:
`decks get --help` says "resolve card codes to names *in text output*", but
`decklists get --help` drops the caveat. Resolve the codes yourself — see
[references/recipes.md](references/recipes.md).

## Onboarding

```bash
command -v marvelcdb || go install github.com/mggarofalo/marvelcdb-cli/cmd/marvelcdb@latest
export PATH="$PATH:$(go env GOPATH)/bin"   # if it is not there already

marvelcdb cache warm            # download cards, packs and factions once
marvelcdb cards search hulk     # confirm it works
```

Needs Go 1.26+ and nothing else. Add `--encounter` to `cache warm` if the project
touches villains or modular sets, because that is a separate download.

To default a project to JSON without touching anything global, export
`MARVELCDB_OUTPUT=json`. (`marvelcdb config set output json` does the same thing
but writes a config file that changes the default for every project and for
interactive use, so leave that to the user.)

Shell completion for card codes, packs, factions, types and sets is filled from
the cache, so it is instant once warmed:

```bash
marvelcdb completion zsh > "${fpath[1]}/_marvelcdb"
```

## Command map

| Command | What it does |
|---|---|
| `cards list` | Filter by pack, set, faction, type, trait, cost, name, text |
| `cards search <query>` | Shorthand for `cards list --search`; name, text, traits, flavour |
| `cards get <code>...` | Full detail for one or more cards |
| `cards image <code>...` | Image URLs (`--back` only works on the 59 cards that have one) |
| `packs list` / `packs get` | Products, release dates, how complete the data is |
| `factions list` | Aspects and pseudo-factions (`--primary` for deckbuilding only) |
| `faq <code>...` | Rules clarifications |
| `taboos list` | Banned/restricted list — fails upstream today, see its help |
| `decklists get/by-date/popular` | Published decklists |
| `decks get <id>...` | A shared but unpublished deck |
| `mydecks list/get/new/save/publish/delete` | Your own decks; needs sign-in |
| `auth`, `cache`, `config` | Credentials, cache, settings |

Filtering happens locally against the cached corpus, so extra filters are free.
Codes for `--faction`, `--type`, `--pack` and `--set` are in
[references/codes.md](references/codes.md); `marvelcdb cards list --help` covers
what the filter flags mean.

## Output formats

`-o` takes `table` (default), `json`, `yaml`, `csv`, `tsv`, `ids` or `text`.
For scripting:

| Format | Use it for |
|---|---|
| `json` | Anything structured |
| `tsv` + `--no-headers` | Two columns into `cut`, with no alignment to parse |
| `ids` | First column only; feeds `xargs` and `while read` |
| `text` | Human-readable card sheets and deck lists |

JSON output is verbatim. The models round-trip fields this build has never heard
of, including nulls and empty strings, so it reproduces what MarvelCDB sent and
stays correct when the site adds a field. Treat it as the source of truth.

## Cache, network and exit codes

`--refresh` revalidates fresh entries, `--no-cache` bypasses the cache entirely,
`--offline` serves only what is cached and exits 5 otherwise, `--cache-ttl` sets
the freshness window. `marvelcdb cache info|warm|prune|clear` manages the store.
Authenticated responses are never cached.

Requests are spaced 100 ms apart by default. MarvelCDB is a community-run site
and the CLI's defaults are deliberately courteous, so prefer one corpus download
and a local filter over hundreds of single-card fetches.

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | General failure |
| 3 | Not signed in, or credentials rejected |
| 4 | Not found (MarvelCDB returns 500 for unknown ids; the CLI translates it) |
| 5 | `--offline` and no cached response |
| 130 | Interrupted |

## Signing in

Only `mydecks` needs it. MarvelCDB issues OAuth2 credentials to registered
applications by email request; `marvelcdb auth --help` explains the whole process,
including which redirect URI to ask for. Secrets go to the OS keyring, never to
the config file. On a machine with no keyring — CI, a container, a headless box —
set `MARVELCDB_CLIENT_ID`, `MARVELCDB_CLIENT_SECRET`, `MARVELCDB_ACCESS_TOKEN`
and `MARVELCDB_REFRESH_TOKEN`; the environment wins over the keyring.

## Where this skill stops

`--help` is the authority on flags and command behaviour; this skill is the
authority on nothing except the five findings above, which were verified by
running the CLI on 2026-08-22.

The code tables in `references/codes.md` are a snapshot. MarvelCDB adds packs and
sets several times a year, so a code that is missing there may be new rather than
wrong — check with `marvelcdb packs list` or the regeneration commands in that
file before telling a user something does not exist.

## References

- [references/recipes.md](references/recipes.md) — corpus dumps, jq filters,
  image downloads, deck slot resolution, CI use, deck editing
- [references/codes.md](references/codes.md) — faction, type, pack and card-set
  codes, and how to regenerate them
