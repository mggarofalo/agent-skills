# Pipeline Recipes

Every command here was run against the live CLI, except the deck-editing section
at the end — that one needs credentials and is marked as unverified. Card codes
and decklist ids in the examples are real.

## Building a local corpus for a project

The whole corpus is one download. Dump it once and query the file, rather than
shelling out per card:

```bash
marvelcdb cards list --encounter -o json > cards.json   # 4,105 — everything
marvelcdb cards list --duplicates -o json > corpus.json # 2,155 — player side incl. reprints
marvelcdb cards list -o json > player-cards.json        # 1,814 — player side, no reprints
marvelcdb packs list -o json > packs.json
```

Rebuild when a new pack lands:

```bash
marvelcdb cards list --encounter --refresh -o json > cards.json
```

A code-to-name lookup, handy for resolving deck slots:

```bash
marvelcdb cards list --encounter -o json | jq 'map({(.code): .name}) | add' > names.json
```

## Feeding a shell loop

`-o ids` prints the first column and nothing else:

```bash
marvelcdb cards list --set spider_man -o ids | while read -r code; do
  echo "processing $code"
done
```

`xargs` works because `cards get`, `cards image` and `faq` all take many codes:

```bash
marvelcdb cards list --faction pool -o ids | xargs marvelcdb cards get -o json
```

## Two columns without parsing a table

Table output is aligned for humans and painful to cut. Use `tsv` with
`--no-headers`:

```bash
marvelcdb cards list --type hero -o tsv --no-headers | cut -f1,2
# 01001a	Spider-Man
# 01010a	Captain Marvel
# 01019a	She-Hulk
```

## Downloading card images

```bash
marvelcdb cards list --set spider_man -o ids \
  | xargs marvelcdb cards image -o tsv --no-headers \
  | cut -f2 \
  | xargs -n1 -P4 curl -sO
```

`--back` switches to the printed reverse image, but only 59 cards site-wide have
one (57 are Main Schemes) and it exits 1 on any card that does not — so it is not
useful across a whole set. For a hero's alter-ego, you want the linked card
instead, which is a separate code:

```bash
marvelcdb cards get 01001a --with-linked -o json | jq -r '[.] | flatten | .[].code'
# 01001a
# 01001b
```

## Filtering beyond what the flags cover

The flags handle pack, set, faction, type, trait, cost, name and text. Anything
else, filter the JSON:

```bash
# Allies with 3 or more health
marvelcdb cards list --type ally -o json \
  | jq -r '.[] | select((.health // 0) >= 3) | "\(.code)\t\(.name)\t\(.health)"'

# Cards whose text mentions a keyword, with their aspect
marvelcdb cards list -o json \
  | jq -r '.[] | select(.text? // "" | test("Overkill")) | [.code, .name, .faction_name] | @tsv'

# Every unique upgrade costing 1 or less, by aspect
marvelcdb cards list --type upgrade --max-cost 1 --unique -o json \
  | jq -r 'group_by(.faction_name) | .[] | "\(.[0].faction_name): \(length)"'
```

Fields are sparse — a hero has no `cost`, a resource has no `health`. String
functions such as `test()` error on the missing key, which is why `.text?  // ""`
appears above. Numeric comparison is worse: it does not error, it just treats the
missing key as lower than every number, so `select(.cost < 3)` silently includes
every costless card. Default explicitly on both sides.

## Resolving a decklist's slots

`slots` is an object of `{"card_code": quantity}`:

```bash
marvelcdb decklists get 65174 -o json | jq -r '.slots | to_entries[] | "\(.key)\t\(.value)"'
```

Joined against the lookup built above:

```bash
marvelcdb decklists get 65174 -o json \
  | jq -r --slurpfile n names.json '.slots | to_entries[] | "\(.value)x \($n[0][.key] // .key)"'
# 1x Med Team
# 1x Energy
# 1x Genius
```

For a human-readable version, the CLI already does this:

```bash
marvelcdb decklists get 65174 -o text --with-cards
```

`--with-cards` downloads the card list once to resolve names, so it costs a
cached corpus fetch on first use.

## Counting and grouping

```bash
# Cards per pack
marvelcdb cards list -o json | jq -r 'group_by(.pack_name)[] | "\(length)\t\(.[0].pack_name)"' | sort -rn

# Aspect distribution of a hero's signature set
marvelcdb cards list --set gambit -o json | jq -r 'group_by(.type_name)[] | "\(length) \(.[0].type_name)"'
```

## Watching for new cards

`packs list` reports `known` against `total`, so incomplete packs are visible:

```bash
marvelcdb packs list --refresh -o json \
  | jq -r '.[] | select(.known < .total) | "\(.name): \(.known)/\(.total)"'
```

## Working offline or in CI

Warm the cache in a setup step, then run everything with `--offline` so a
network blip fails loudly instead of hanging:

```bash
marvelcdb cache warm --encounter
marvelcdb cards list --offline --set wolverine -o json
```

`--offline` exits 5 when a response is not cached. Pin the cache somewhere
predictable with `MARVELCDB_CACHE_DIR` if the CI runner's cache directory is not
persisted between steps.

## Editing one of your decks

**Unverified.** These need OAuth2 credentials, which were not available when this
skill was written, so they are derived from `marvelcdb mydecks save --help` and
`internal/cli/mydecks.go` rather than executed. Use `--dry-run` first.

MarvelCDB replaces the whole slot list on every save, so read, edit, write back:

```bash
marvelcdb mydecks get 12345 -o json > deck.json
jq '.slots["01050"] = 2' deck.json > deck.new.json && mv deck.new.json deck.json
marvelcdb mydecks save 12345 --slots-file deck.json --dry-run   # check first
marvelcdb mydecks save 12345 --slots-file deck.json
```

`--slot CODE=QUANTITY` layers on top of `--slots-file` for small edits, and a
quantity of `0` removes the card:

```bash
marvelcdb mydecks save 12345 --slots-file deck.json --slot 01050=2 --slot 01053=0
```

`--slots-file -` reads from stdin, so a jq transform can go straight in:

```bash
marvelcdb mydecks get 12345 -o json \
  | jq '.slots |= with_entries(select(.value > 0))' \
  | marvelcdb mydecks save 12345 --slots-file -
```
