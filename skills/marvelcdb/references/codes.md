# Code Vocabularies

Generated from the live corpus on 2026-08-22. Regenerate with the commands shown
in each section — MarvelCDB adds packs and sets regularly, so treat any code you
do not find here as possibly new rather than invalid.

## Factions

`marvelcdb factions list`

| Code | Name | Deckbuilding aspect |
|---|---|---|
| `aggression` | Aggression | yes |
| `justice` | Justice | yes |
| `encounter` | Encounter | no |
| `hero` | Hero | no |
| `basic` | Basic | yes |
| `leadership` | Leadership | yes |
| `protection` | Protection | yes |
| `campaign` | Campaign | no |
| `pool` | 'Pool | yes |

## Card types

`marvelcdb cards list -o json | jq -r ".[].type_code" | sort -u`

Player-side types (the default corpus):

- `ally`
- `alter_ego`
- `attachment`
- `environment`
- `event`
- `hero`
- `minion`
- `obligation`
- `player_side_scheme`
- `resource`
- `side_scheme`
- `support`
- `treachery`
- `upgrade`

Encounter-side types appear only with `--encounter`:

- `evidence_means`
- `evidence_motive`
- `evidence_opportunity`
- `leader`
- `main_scheme`
- `villain`

## Packs

`marvelcdb packs list` — the `--pack` filter takes these codes.

| Code | Name | Released |
|---|---|---|
| `core` | Core Set | 2019-11-01 |
| `gob` | The Green Goblin | 2019-12-20 |
| `twc` | The Wrecking Crew | 2020-02-07 |
| `cap` | Captain America | 2019-12-20 |
| `msm` | Ms. Marvel | 2019-12-20 |
| `thor` | Thor | 2020-03-06 |
| `bkw` | Black Widow | 2020-05-06 |
| `drs` | Doctor Strange | 2020-06-06 |
| `hlk` | Hulk | 2020-08-07 |
| `trors` | The Rise of Red Skull | 2020-09-04 |
| `toafk` | The Once and Future Kang | 2020-10-02 |
| `ant` | Ant-Man | 2020-11-06 |
| `wsp` | Wasp | 2021-01-22 |
| `qsv` | Quicksilver | 2021-02-05 |
| `scw` | Scarlet Witch | 2021-03-05 |
| `gmw` | The Galaxy's Most Wanted | 2021-04-02 |
| `stld` | Star-Lord | 2021-05-14 |
| `gam` | Gamora | 2021-05-14 |
| `drax` | Drax | 2021-06-18 |
| `vnm` | Venom | 2021-07-16 |
| `mts` | The Mad Titan's Shadow | 2021-09-01 |
| `nebu` | Nebula | 2021-09-17 |
| `warm` | War Machine | 2021-11-05 |
| `hood` | The Hood | 2021-11-26 |
| `valk` | Valkyrie | 2021-11-26 |
| `vision` | Vision | 2022-01-14 |
| `sm` | Sinister Motives | 2022-04-08 |
| `nova` | Nova | 2022-05-20 |
| `ironheart` | Ironheart | 2022-05-20 |
| `spiderham` | Spider-Ham | 2022-07-15 |
| `spdr` | SP//dr | 2022-07-15 |
| `mut_gen` | Mutant Genesis | 2022-09-30 |
| `cyclops` | Cyclops | 2022-09-30 |
| `phoenix` | Phoenix | 2022-09-30 |
| `wolv` | Wolverine | 2022-11-11 |
| `storm` | Storm | 2022-11-11 |
| `gambit` | Gambit | 2023-02-24 |
| `rogue` | Rogue | 2023-02-24 |
| `mojo` | Mojo Mania | 2022-11-11 |
| `next_evol` | NeXt Evolution | 2023-08-18 |
| `psylocke` | Psylocke | 2023-09-22 |
| `angel` | Angel | 2023-09-22 |
| `x23` | X-23 | 2023-11-17 |
| `deadpool` | Deadpool | 2023-11-17 |
| `aoa` | Age of Apocalypse | 2024-03-29 |
| `iceman` | Iceman | 2024-05-17 |
| `jubilee` | Jubilee | 2024-07-19 |
| `ncrawler` | Nightcrawler | 2024-09-20 |
| `magneto` | Magneto | 2024-11-15 |
| `aos` | Agents of S.H.I.E.L.D. | 2025-02-20 |
| `bp` | Black Panther | 2025-04-18 |
| `silk` | Silk | 2025-04-18 |
| `falcon` | Falcon | 2025-06-20 |
| `winter` | Winter Soldier | 2025-06-20 |
| `tt` | Trickster Takeover | 2025-08-15 |
| `cw` | Civil War | 2025-10-17 |
| `synthezoid` | Synthezoid Smackdown | 2025-12-05 |
| `wonder_man` | Wonder Man | 2026-02-20 |
| `hercules` | Hercules | 2026-02-20 |
| `fne` | Fear No Evil | 2026-07-24 |
| `jj` | Jessica Jones | 2026-08-21 |
| `luke_cage` | Luke Cage | 2026-08-21 |
| `ron` | Ronan Modular Set | 2020-08-02 |

## Card sets

A *set* is finer-grained than a pack: it is the signature group a card belongs to
(a hero and their signature cards, a modular encounter set, a campaign). The
`--set` filter takes these codes. Cards with no set — most Basic cards — have no
`card_set_code` field at all.

```bash
marvelcdb cards list --encounter -o json \
  | jq -r "[.[].card_set_code, .[].card_set_name] | @tsv" # or see the table below
```

| Code | Name |
|---|---|
| `a_mess_of_things` | A Mess of Things |
| `a.i.m._abduction` | A.I.M. Abduction |
| `a.i.m._science` | A.I.M. Science |
| `absorbing_man` | Absorbing Man |
| `acolytes` | Acolytes |
| `age_of_apocalypse` | Age of Apocalypse |
| `all_versus_all` | All Versus All |
| `anachronauts` | Anachronauts |
| `angel` | Angel |
| `angel_nemesis` | Angel Nemesis |
| `ant` | Ant-Man |
| `ant_nemesis` | Ant-Man Nemesis |
| `aoa_basic_campaign` | Campaign |
| `aoa_campaign` | Campaign |
| `aoa_mission` | Mission |
| `apocalypse` | Apocalypse |
| `arcade` | Arcade |
| `armadillo` | Armadillo |
| `armies_of_titan` | Armies of Titan |
| `atlanteans` | Atlanteans |
| `bad_publicity` | Bad Publicity |
| `badoon_headhunter` | Badoon Headhunter |
| `band_of_badoon` | Band of Badoon |
| `baron_zemo` | Baron Zemo |
| `batroc` | Batroc |
| `batrocs_brigade` | Batroc's Brigade |
| `beasty_boys` | Beasty Boys |
| `bishop` | Bishop |
| `bishop_nemesis` | Bishop Nemesis |
| `black_order` | Black Order |
| `black_panther` | Black Panther |
| `black_panther_nemesis` | Black Panther Nemesis |
| `black_panther_shuri` | Black Panther (Shuri) |
| `black_panther_shuri_nemesis` | Black Panther (Shuri) Nemesis |
| `black_tom_cassidy` | Black Tom Cassidy |
| `black_widow` | Black Widow |
| `black_widow_nemesis` | Black Widow Nemesis |
| `black_widow_villain` | Black Widow |
| `blue_moon` | Blue Moon |
| `bomb_scare` | Bomb Scare |
| `brawler` | Brawler |
| `brotherhood` | Brotherhood |
| `brotherhood_of_badoon` | Brotherhood Of Badoon |
| `brothers_grimm` | Brothers Grimm |
| `bulldozer` | Bulldozer |
| `cable` | Cable |
| `cable_nemesis` | Cable Nemesis |
| `cape_killer` | Cape-Killer |
| `captain_america` | Captain America |
| `captain_america_leader` | Captain America |
| `captain_america_nemesis` | Captain America Nemesis |
| `captain_marvel` | Captain Marvel |
| `captain_marvel_leader` | Captain Marvel |
| `captain_marvel_nemesis` | Captain Marvel Nemesis |
| `celestial_tech` | Celestial Tech |
| `challenge` | Challenge |
| `children_of_thanos` | Children of Thanos |
| `city_in_chaos` | City in Chaos |
| `clan_akkaba` | Clan Akkaba |
| `cloak_and_dagger_modular` | Cloak & Dagger |
| `colossus` | Colossus |
| `colossus_nemesis` | Colossus Nemesis |
| `commander` | Commander |
| `community_service` | Community Service |
| `crazy_gang` | Crazy Gang |
| `crime` | Crime |
| `crossbones` | Crossbones |
| `crossfire_crew` | Crossfire's Crew |
| `cyclops` | Cyclops |
| `cyclops_nemesis` | Cyclops Nemesis |
| `dangerous_recruits` | Dangerous Recruits |
| `daredevil` | Daredevil |
| `daredevil_nemesis` | Daredevil Nemesis |
| `daredevil_sense_deck` | Sense Deck |
| `dark_beast` | Dark Beast |
| `dark_riders` | Dark Riders |
| `deadly_duo` | Deadly Duo |
| `deadpool` | Deadpool |
| `deadpool_nemesis` | Deadpool Nemesis |
| `deathstrike` | Deathstrike |
| `defender` | Defender |
| `defenders` | Defenders |
| `doctor_strange` | Doctor Strange |
| `doctor_strange_invocation_deck` | Invocation |
| `doctor_strange_nemesis` | Doctor Strange Nemesis |
| `domino` | Domino |
| `domino_nemesis` | Domino Nemesis |
| `down_to_earth` | Down to Earth |
| `drax` | Drax |
| `drax_nemesis` | Drax Nemesis |
| `dreadpool` | Dreadpool |
| `dystopian_nightmare` | Dystopian Nightmare |
| `ebony_maw` | Ebony Maw |
| `echo` | Echo |
| `echo_nemesis` | Echo Nemesis |
| `en_sabah_nur` | En Sabah Nur |
| `enchantress` | Enchantress |
| `enchantress_villain` | Enchantress |
| `escape_the_museum` | Escape the Museum |
| `executive_board_evidence` | Executive Board Evidence |
| `exodus` | Exodus |
| `exp_kang` | Expert Kang |
| `expcamp` | Expert Campaign |
| `exper_weapon` | Experimental Weapons |
| `expert` | Expert |
| `expert_ii` | Expert II |
| `extreme_measures` | Extreme Measures |
| `extreme_risk` | Extreme Risk |
| `falcon` | Falcon |
| `falcon_nemesis` | Falcon Nemesis |
| `fantasy` | Fantasy |
| `flight` | Flight |
| `four_horsemen` | Four Horsemen |
| `frost_giants` | Frost Giants |
| `future_past` | Future Past |
| `galactic_artifacts` | Galactic Artifacts |
| `gam` | Gamora |
| `gam_nemesis` | Gamora Nemesis |
| `gambit` | Gambit |
| `gambit_nemesis` | Gambit Nemesis |
| `genosha` | Genosha |
| `ghost_spider` | Ghost-Spider |
| `ghost_spider_nemesis` | Ghost-Spider Nemesis |
| `goblin_gear` | Goblin Gear |
| `goblin_gimmicks` | Goblin Gimmicks |
| `god_of_lies` | God of Lies |
| `gravitational_pull` | Gravitational Pull |
| `groot` | Groot |
| `groot_nemesis` | Groot Nemesis |
| `growing_strong` | Growing Strong |
| `guerrilla_tactics` | Guerrilla Tactics |
| `hard_sound` | Hard Sound |
| `hawkeye` | Hawkeye |
| `hawkeye_nemesis` | Hawkeye Nemesis |
| `hela` | Hela |
| `hellfire` | Hellfire |
| `hells_kitchen` | Hell's Kitchen |
| `hercules` | Hercules |
| `hercules_gift_deck` | Gift Deck |
| `hercules_labor_deck` | Labor Deck |
| `hercules_nemesis` | Hercules Nemesis |
| `heroes_for_hire` | Heroes for Hire |
| `hope_summers` | Hope Summers |
| `horror` | Horror |
| `hounds` | Hounds |
| `hulk` | Hulk |
| `hulk_nemesis` | Hulk Nemesis |
| `hulkling` | Hulkling |
| `hulkling_nemesis` | Hulkling Nemesis |
| `hydra_assault` | Hydra Assault |
| `hydra_camp` | Hydra Campaign |
| `hydra_patrol` | Hydra Patrol |
| `iceman` | Iceman |
| `iceman_frostbite` | Frostbite |
| `iceman_nemesis` | Iceman Nemesis |
| `infiltrate_the_museum` | Infiltrate the Museum |
| `infinites` | Infinites |
| `infinity_gauntlet` | Infinity Gauntlet |
| `inheritors` | The Inheritors |
| `iron_man` | Iron Man |
| `iron_man_leader` | Iron Man |
| `iron_man_nemesis` | Iron Man Nemesis |
| `ironheart` | Ironheart |
| `ironheart_nemesis` | Ironheart Nemesis |
| `ironspider_sinister` | Iron Spider's Sinister Six |
| `jessica_jones` | Jessica Jones |
| `jessica_jones_nemesis` | Jessica Jones Nemesis |
| `jubilee` | Jubilee |
| `jubilee_nemesis` | Jubilee Nemesis |
| `juggernaut` | Juggernaut |
| `kang` | Kang |
| `klaw` | Klaw |
| `kree_fanatic` | Kree Fanatic |
| `kree_militant` | Kree Militants |
| `legions_of_hel` | Legions of Hel |
| `legions_of_hydra` | Legions of Hydra |
| `loki` | Loki |
| `longshot` | Longshot |
| `luke_cage` | Luke Cage |
| `luke_cage_nemesis` | Luke Cage Nemesis |
| `m.o.d.o.k.` | M.O.D.O.K |
| `magik` | Magik |
| `magik_nemesis` | Magik Nemesis |
| `magneto` | Magneto |
| `magneto_nemesis` | Magneto Nemesis |
| `magneto_villain` | Magneto |
| `magog` | Magog |
| `mansion_attack` | Mansion Attack |
| `marauders` | Marauders |
| `maria_hill` | Maria Hill |
| `maria_hill_modular` | Maria Hill |
| `maria_hill_nemesis` | Maria Hill Nemesis |
| `martial_law` | Martial Law |
| `master_mold` | Master Mold |
| `masters_of_evil` | Masters of Evil |
| `menagerie_medley` | Menagerie Medley |
| `mighty_avengers` | Mighty Avengers |
| `military_grade` | Military Grade |
| `mister_hyde` | Mister Hyde |
| `mister_sinister` | Mister Sinister |
| `mojo` | Mojo |
| `moon_knight_modular` | Moon Knight |
| `morlock_siege` | Morlock Siege |
| `mot` | Master of Time |
| `ms_marvel` | Ms. Marvel |
| `ms_marvel_nemesis` | Ms. Marvel Nemesis |
| `mts_campaign` | The Mad Titan's Shadow Campaign |
| `mut_gen_campaign` | Mutant Genesis Campaign |
| `mutagen_formula` | Mutagen Formula |
| `mutant_insurrection` | Mutant Insurrection |
| `mutant_slayers` | Mutant Slayers |
| `mysterio` | Mysterio |
| `mystique` | Mystique |
| `namor_modular` | Namor |
| `nasty_boys` | Nasty Boys |
| `nebu` | Nebula |
| `nebu_nemesis` | Nebula Nemesis |
| `nebula` | Nebula |
| `new_avengers` | New Avengers |
| `next_evol_campaign` | Next Evolution Campaign |
| `nick_fury` | Nick Fury |
| `nick_fury_nemesis` | Nick Fury Nemesis |
| `nightcrawler` | Nightcrawler |
| `nightcrawler_nemesis` | Nightcrawler Nemesis |
| `nova` | Nova |
| `nova_nemesis` | Nova Nemesis |
| `on_the_run` | On the Run |
| `osborn_tech` | Osborn Tech |
| `overseer` | Overseer |
| `paladin` | Paladin |
| `pale_little_spider` | Pale Little Spider |
| `peacekeeper` | Peacekeeper |
| `personal_nightmare` | Personal Nightmare |
| `phoenix` | Phoenix |
| `phoenix_nemesis` | Phoenix Nemesis |
| `piledriver` | Piledriver |
| `power_drain` | Power Drain |
| `power_of_the_atom` | Power of the Atom |
| `power_stone` | Power Stone |
| `prelates` | Prelates |
| `project_wideawake` | Project Wideawake |
| `psylocke` | Psylocke |
| `psylocke_nemesis` | Psylocke Nemesis |
| `qsv` | Quicksilver |
| `qsv_nemesis` | Quicksilver Nemesis |
| `ransacked_armory` | Ransacked Armory |
| `reavers` | Reavers |
| `red_skull` | Red Skull |
| `registration` | Registration |
| `resistance` | Resistance |
| `rhino` | Rhino |
| `risky_business` | Risky Business |
| `rocket` | Rocket Raccoon |
| `rocket_nemesis` | Rocket Raccoon Nemesis |
| `rogue` | Rogue |
| `rogue_nemesis` | Rogue Nemesis |
| `ronan` | Ronan the Accuser |
| `royal_guard` | Royal Guard |
| `running_interference` | Running Interference |
| `s.h.i.e.l.d.` | S.H.I.E.L.D. |
| `s.h.i.e.l.d._executive_board` | S.H.I.E.L.D. Executive Board |
| `sabretooth` | Sabretooth |
| `sandman` | Sandman |
| `sauron` | Sauron |
| `savage_land` | Savage Land |
| `scarlet_twins` | Scarlet Twins |
| `sci-fi` | Sci-Fi |
| `scientist_supreme` | Scientist Supreme |
| `scw` | Scarlet Witch |
| `scw_nemesis` | Scarlet Witch Nemesis |
| `secret_avengers` | Secret Avengers |
| `sentinels` | Sentinels |
| `shadow_king` | Shadow King |
| `shadowcat` | Shadowcat |
| `shadowcat_nemesis` | Shadowcat Nemesis |
| `she_hulk` | She-Hulk |
| `she_hulk_leader` | She-Hulk |
| `she_hulk_nemesis` | She-Hulk Nemesis |
| `shield_ops` | S.H.I.E.L.D. Ops |
| `shield_tech` | Shield Tech |
| `ship_command` | Ship Command |
| `silk` | Silk |
| `silk_nemesis` | Silk Nemesis |
| `sinister_assault` | Sinister Assault |
| `sinister_six` | The Sinister Six |
| `sinister_syndicate` | Sinister Syndicate |
| `sitcom` | Sitcom |
| `snitches_get_stitches` | Snitches get Stitches |
| `space_pirates` | Space Pirates |
| `spdr` | SP//dr |
| `spdr_nemesis` | SP//dr Nemesis |
| `spectrum` | Spectrum |
| `spectrum_nemesis` | Spectrum Nemesis |
| `spider_man` | Spider-Man |
| `spider_man_modular` | Spider-Man |
| `spider_man_morales` | Spider-Man - Miles Morales |
| `spider_man_morales_nemesis` | Spider-Man - Morales Nemesis |
| `spider_man_nemesis` | Spider-Man Nemesis |
| `spider_woman` | Spider-Woman |
| `spider_woman_leader` | Spider Woman |
| `spider_woman_nemesis` | Spider-Woman Nemesis |
| `spiderham` | Spider-Ham |
| `spiderham_nemesis` | Spider-Ham Nemesis |
| `spiral` | Spiral |
| `standard` | Standard |
| `standard_ii` | Standard II |
| `standard_iii` | Standard III |
| `standard_pvp` | Standard PVP |
| `state_of_emergency` | State of Emergency |
| `stld` | Star-Lord |
| `stld_nemesis` | Star-Lord Nemesis |
| `storm` | Storm |
| `storm_nemesis` | Storm Nemesis |
| `storm_weather_deck` | Weather Deck |
| `streets_of_mayhem` | Streets of Mayhem |
| `stryfe` | Stryfe |
| `super_strength` | Super Strength |
| `supersonic` | Supersonic |
| `symbiotic_strength` | Symbiotic Strength |
| `synthezoid_registration` | Registration |
| `synthezoid_resistance` | Resistance |
| `taskmaster` | Taskmaster |
| `taskmaster_modular` | Taskmaster |
| `techno` | Techno |
| `telepathy` | Telepathy |
| `temporal` | Temporal |
| `thanos` | Thanos |
| `the_doomsday_chair` | The Doomsday Chair |
| `the_hood` | The Hood |
| `the_initiative` | The Initiative |
| `the_leaper` | The Leaper |
| `the_market` | The Market |
| `thor` | Thor |
| `thor_nemesis` | Thor Nemesis |
| `thunderball` | Thunderball |
| `thunderbolts` | Thunderbolts |
| `thunderbolts_modular` | Thunderbolts |
| `tigra` | Tigra |
| `tigra_nemesis` | Tigra Nemesis |
| `tower_defense` | Tower Defense |
| `trickster_magic` | Trickster Magic |
| `ultron` | Ultron |
| `under_attack` | Under Attack |
| `unus` | Unus |
| `valk` | Valkyrie |
| `valk_nemesis` | Valkyrie Nemesis |
| `venom` | Venom |
| `venom_goblin` | Venom Goblin |
| `vision` | Vision |
| `vision_leader` | Vision |
| `vision_nemesis` | Vision Nemesis |
| `vnm` | Venom |
| `vnm_nemesis` | Venom Nemesis |
| `warlock` | Adam Warlock |
| `warlock_nemesis` | Adam Warlock Nemesis |
| `warm` | War Machine |
| `warm_nemesis` | War Machine Nemesis |
| `weap_master` | Weapon Master |
| `western` | Western |
| `whispers_of_paranoia` | Whispers of Paranoia |
| `whiteout` | Whiteout |
| `winter_soldier` | Winter Soldier |
| `winter_soldier_nemesis` | Winter Soldier Nemesis |
| `wolverine` | Wolverine |
| `wolverine_nemesis` | Wolverine Nemesis |
| `wonder_man` | Wonder Man |
| `wonder_man_nemesis` | Wonder Man Nemesis |
| `wrecker` | Wrecker |
| `wrecking_crew` | Wrecking Crew |
| `wrecking_crew_modular` | Wrecking Crew |
| `wsp` | Wasp |
| `wsp_nemesis` | Wasp Nemesis |
| `x23` | X-23 |
| `x23_nemesis` | X-23 Nemesis |
| `young_avengers` | Young Avengers |
| `zero_tolerance` | Zero Tolerance |
| `zola` | Zola |
| `zzzax` | Zzzax |
