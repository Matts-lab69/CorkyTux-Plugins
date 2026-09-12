# RPG Maker Runtime (guide)

The `rpgmaker-runtime` plugin runs RPG Maker **MV/MZ** (NW.js) and
**2000/2003** (EasyRPG) games thanks to the `box-rpg` logic bundled in `vendor/`
(see credits in the main README).

## How it works

- `scan` finds RPG Maker games in a folder (detects MV/MZ vs 2000/2003).
- `diagnose` tells you which runtime is missing and how to fix it.
- `install` downloads/installs the needed runtime.
- `run` launches the game with the right profile.

```bash
./rpgmaker-runtime status
./rpgmaker-runtime scan /path/to/my/games
./rpgmaker-runtime diagnose "/path/to/my game"
./rpgmaker-runtime install --runtime easyrpg
./rpgmaker-runtime run "/path/to/my game"
```

## Supported engines

| Engine | Runtime | Notes |
|--------|---------|-------|
| RPG Maker MV / MZ | NW.js | resolved/installed via `box-rpg` |
| RPG Maker 2000 / 2003 | EasyRPG Player | resolved/installed via `box-rpg` |

## From CorkyTux

1. Install the plugin (Settings > Plugins) or copy `rpgmaker-runtime`,
   `plugin.json` and the `vendor/` folder to
   `~/.local/share/CorkyTux/plugins/rpgmaker-runtime/`.
2. Register your games folder and use scan/diagnose/run from the UI.

## Troubleshooting

- **Missing NW.js or EasyRPG**: run `diagnose`, then `install`.
- **Game inside ZIP/RAR**: extract it to a folder first.
- Report bugs in [Issues](https://github.com/Matts-lab69/CorkyTux-Plugins/issues).
