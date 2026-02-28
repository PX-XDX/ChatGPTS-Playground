# Echoes of Aetherfall: Sovereign Edition

A premium, long-form terminal RPG + trade sim in Python. It is designed for a deep single-player run (roughly 8-12 hours depending on pacing and side activities).

## Features
- **Long campaign arc** with 6 chapters, relic progression, and multi-stage finale.
- **Dynamic economy** across five regions with buy/sell cargo gameplay.
- **Money-focused systems**: contracts, trading profit tracking, caravan expansion.
- **Tactical combat** with stamina actions, heavy attacks, guard play, and boss mechanics.
- **Progression systems**: leveling, renown gates, crafting, upgrades, and title changes.
- **Persistent saves**: 3 JSON save slots with market state + player state.


## Run
```bash
python3 epic_odyssey.py
```

## Save files
The game creates:
- `saves/slot_1.json`
- `saves/slot_2.json`
- `saves/slot_3.json`

## Notes
- This repo work is on your current branch (`work`). If you don't see files in `main`, merge the PR from this branch into `main`.
- Saves from older versions may not load due to schema/version upgrades.
