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
./rpgmaker-runtime run "/path/to/my game" --runtime 6.8.1 --allow-network
./rpgmaker-runtime cleanup list profiles   # what box-rpg accumulated
```

## Sandbox & display notes (box-rpg 26.9.20)

- Games run isolated under Bubblewrap: game assets are read-only, only saves,
  the profile and temp storage are writable. Network is **denied** unless you
  pass `run --allow-network`; self-updating games need `--allow-game-writes`
  (only for games you trust).
- On **X11** sessions box-rpg demands an interactive TTY confirmation (X11
  clients can keylog). The plugin auto-answers it through a PTY — your
  explicit choice when installing this plugin. On Wayland no prompt exists.
- Some NW.js exports need files from the game root: `run --copy-root-file
  game_messages.csv` (repeatable, files only — no dirs/symlinks).

## Cleanup & saves

- Each NW.js game keeps a private Chromium profile under the box-rpg cache;
  list them with `cleanup list profiles` and remove one (or `--all`) with
  `cleanup remove profiles SELECTOR --yes`. Game directories, configs,
  sessions and reports are never deleted.
- EasyRPG saves to `<game>/save/`. Copy existing `Save01.lsd`, `Save02.lsd`,
  etc. from the game root into that directory to continue old saves — the
  launcher does not move them automatically.

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

## Credits

- [christvh / box-rpg](https://gitlab.com/christvh/box-rpg) — I used the logic
  from this repository and adapted it to a UI (bundled under `vendor/`).
- [EasyRPG Player](https://easyrpg.org) — RPG Maker 2000/2003 runtime.
- [NW.js](https://nwjs.io) — RPG Maker MV/MZ runtime.
