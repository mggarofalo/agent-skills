---
name: marvelcdb
description: >
  MarvelCDB command-line client — Marvel Champions card, pack, faction, FAQ, decklist
  and deck data, piped locally from a disk cache.
  TRIGGER when: the user mentions Marvel Champions, MarvelCDB, marvelcdb, card codes like
  01001a, heroes/allies/aspects/upgrades/villains as game data, deckbuilding, decklists,
  taboo lists, or asks to look up, filter, export or script against Marvel Champions cards.
  Also when a project reads card data from JSON/CSV that came from MarvelCDB.
  Covers install, the command tree, output formats, jq pipelines and OAuth2 deck editing.
allowed-tools: Bash, Read
user_invocable: false
---

# MarvelCDB CLI

`marvelcdb` is a Go client for [MarvelCDB](https://marvelcdb.com). Reads need no
account. The whole card corpus is one ~7 MB download that it caches on disk and
revalidates conditionally, so after the first query everything is local and fast.

Source: `github.com/mggarofalo/marvelcdb-cli`.

## Onboarding

```bash
command -v marvelcdb || go install github.com/mggarofalo/marvelcdb-cli/cmd/marvelcdb@latest
export PATH="$PATH:$(go env GOPATH)/bin"   # if it is not there already

marvelcdb cache warm            # download cards, packs and factions once
marvelcdb cards search hulk     # confirm it works
```

Needs Go 1.26+ and nothing else. `cache warm --encounter` also caches the
encounter-side corpus; do that if the project touches villains or modular sets,
because it is a separate download.

Optional but worth it — shell completion for card codes, packs, factions, types
and sets is filled from the cache:

```bash
marvelcdb completion zsh > "${fpath[1]}/_marvelcdb"
```

Set a project-wide default so every call is pipeable without repeating `-o`:

```bash
marvelcdb config set output json
```

## Quick start

```bash
marvelcdb cards list --faction leadership --type ally --max-cost 2
marvelcdb cards get 01001a -o text          # readable card sheet
marvelcdb cards list --set gambit -o ids    # bare codes, one per line
marvelcdb decklists popular -o json
marvelcdb packs list
```

## Output formats

`-o` / `--output` takes `table` (default), `json`, `yaml`, `csv`, `tsv`, `ids`
or `text`. For scripting:

| Format | Use it for |
|---|---|
| `json` | Anything structured. Verbatim — see below. |
| `tsv` + `--no-headers` | Two columns into `cut`, no alignment to parse. |
| `ids` | First column only. Feeds `xargs` and `while read`. |
| `text` | Human-readable card sheets and deck lists. |

**JSON is verbatim.** The models round-trip fields this build has never heard
of, so `-o json` reproduces exactly what MarvelCDB sent, including nulls and
empty strings, and stays correct when the site adds a field. Trust it as the
source of truth.

## Command tree

| Command | What it does |
|---|---|
| `cards list` | Filter by pack, set, faction, type, trait, cost, name, text |
| `cards search <query>` | Shorthand for `cards list --search`; matches name, text, traits, flavour |
| `cards get <code>...` | Full detail for one or more cards |
| `cards image <code>...` | Image URLs (`--back` for the reverse face) |
| `packs list` / `packs get` | Products, release dates, how complete the data is |
| `factions list` | Aspects and pseudo-factions (`--primary` for deckbuilding aspects only) |
| `faq <code>...` | Rules clarifications |
| `taboos list` | Banned/restricted list — **broken upstream**, see Gotchas |
| `decklists get/by-date/popular` | Published decklists |
| `decks get <id>...` | A shared but unpublished deck |
| `mydecks list/get/new/save/publish/delete` | Your own decks; needs sign-in |
| `auth`, `cache`, `config` | Credentials, cache, settings |

Full flags for any of these: `marvelcdb <command> --help`.

### `cards list` filters

`--pack`, `--set`, `--faction`, `--type` and `--trait` are all repeatable, and
**repeating one widens the match** while different flags narrow it. So
`--faction leadership --faction justice --type ally` means "allies in either
aspect".

Also: `--name`, `--text`, `--search`, `--cost` (exact, repeatable), `--min-cost`,
`--max-cost`, `--unique`, `--permanent`, `--duplicates`, `--hide-spoilers`,
`--limit`, `--sort` (code, name, cost, faction, type, pack, set, position),
`--reverse`, `--wide`.

Filtering happens locally against the cached corpus, so extra filters cost
nothing. Codes for `--faction`, `--type`, `--pack` and `--set` are in
[references/codes.md](references/codes.md).

## Gotchas

1. **A single result is a JSON object, a multiple result is an array.**
   `cards get 01050 -o json` gives `{...}`; `cards get 01050 01051` gives
   `[{...},{...}]`. Same for `decklists get`, `decks get`, `mydecks get`. Handle
   both with `jq '[.] | flatten'`, or always pass two codes when scripting.
2. **Encounter cards are excluded by default.** `cards list` returns 2,155
   player cards. `--encounter` widens it to 4,105 including villains, minions,
   main schemes and modular sets.
3. **Fields are sparse.** A hero has no `cost`; a resource has no `health`.
   Default before comparing — `select((.health // 0) >= 3)` — or jq errors on
   null.
4. **`--with-cards` only affects `-o text`.** In JSON output it is silently a
   no-op; the slots stay as card codes. Resolve them yourself (see
   [references/recipes.md](references/recipes.md)).
5. **Unknown ids return exit 4, not an empty result.** MarvelCDB answers with
   HTTP 500 and the CLI translates it. That 500 is never retried.
6. **Saving a deck replaces the whole slot list.** There is no "add one card".
   Read, edit, write back — and use `--dry-run` first.
7. **`taboos list` fails server-side for everyone.** The command exists for when
   upstream fixes it; expect an error today.
8. **`mydecks publish --precedent` fails upstream.** Leave it unset.
9. **Traits split on `". "`, not `"."`** — otherwise `S.H.I.E.L.D.` shreds. The
   CLI handles this; anything parsing `real_traits` yourself should too.

## Cache and network

| Flag | Effect |
|---|---|
| `--refresh` | Revalidate even fresh entries |
| `--no-cache` | Neither read nor write |
| `--offline` | Cache only; exit 5 if a response is missing |
| `--cache-ttl 24h` | Freshness window |

```bash
marvelcdb cache info                    # where it lives, how big
marvelcdb cache warm [--encounter]      # pre-fetch
marvelcdb cache prune --older-than 30d
marvelcdb cache clear
```

Requests are spaced 100 ms apart by default (`--rate-limit`). MarvelCDB is a
community-run site — do not batch hundreds of single-card fetches when one
corpus download and a local filter would do.

## Signing in (only needed for `mydecks`)

MarvelCDB issues OAuth2 client credentials to registered applications by email
request; see <https://marvelcdb.com/api/>. Ask for the redirect URI
`http://127.0.0.1:8765/callback`, which is what the CLI listens on by default —
MarvelCDB matches redirect URIs exactly.

```bash
marvelcdb auth client set --id <client-id>   # prompts for the secret
marvelcdb auth login                         # opens a browser, captures the callback
marvelcdb auth status
```

Secrets go to the OS keyring, never to the config file. On a machine with no
keyring — CI, a container, a headless box — set `MARVELCDB_CLIENT_ID`,
`MARVELCDB_CLIENT_SECRET`, `MARVELCDB_ACCESS_TOKEN` and
`MARVELCDB_REFRESH_TOKEN` instead; the environment wins over the keyring.

Authenticated responses are never cached.

## Configuration

Precedence, lowest to highest: defaults, config file, environment, flags.

```bash
marvelcdb config path
marvelcdb config list
marvelcdb config set output json
marvelcdb config set cache_ttl 24h
```

Settings: `base_url`, `locale` (`en`, `de`, `es`, `fr`, `it`, `ko`), `output`,
`color`, `cache_dir`, `cache_ttl`, `rate_limit`, `timeout`, `max_retries`,
`redirect_uri`, `keyring_service`. Environment equivalents are
`MARVELCDB_CONFIG`, `MARVELCDB_BASE_URL`, `MARVELCDB_LOCALE`,
`MARVELCDB_OUTPUT`, `MARVELCDB_CACHE_DIR`, `MARVELCDB_CACHE_TTL`,
`MARVELCDB_USER_AGENT`.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | General failure |
| 3 | Not signed in, or credentials rejected |
| 4 | Not found |
| 5 | `--offline` and no cached response |
| 130 | Interrupted |

## References

- [references/recipes.md](references/recipes.md) — pipeline recipes: corpus
  dumps, jq filters, image downloads, slot resolution, CI use, deck editing
- [references/codes.md](references/codes.md) — faction, type, pack and card-set
  codes, and how to regenerate them
