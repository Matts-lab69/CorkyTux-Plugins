# RPG Maker: what changed upstream and what I adopt

Comparison of the vendor (`box-rpg` 26.9.21, Sep 2026) against the current
upstream (`box-project`, tag 26.9.138, 2026-09-27). Sources: the tag tarball,
`docs/box-rpg/api.md`, `README.md` and the releases via the GitLab API.

## What changed upstream (the parts that matter)

- The `christvh/box-rpg` repo moved into the `christvh/box-project` monorepo
  (301 redirect); the backend lives in `box-rpg/src/`, not in `src/`.
- New stable `box.api` layer (inspect, diagnose, runtime, launch, cleanup,
  interaction): the blessed surface for frontends. The CLI (`box.cli`) is a
  thin client on top of it.
- Supervised launching: one game = one session (`game already running`),
  `stop_session`, `poll_launch_status`, EasyRPG saves migrated to `save/`,
  private Chromium profiles per game.
- New `launch` flags: `--gamemode`, `--sdk`, `--ci-mount` (on top of
  `--allow-network`, `--allow-game-writes`, `--x11`, `--copy-root-file`,
  `--runtime` — those I already had).
- `runtime remove`, `cleanup remove/all`, `uninstall`, `version_info`, AppImage
  updates, i18n (es), its own extensive tests.
- Isolation without design changes: Bubblewrap mandatory, no unsandboxed mode;
  network, writes and X11 behind per-launch consent.

## What I don't adopt (and why)

- In-process `box.api`: NO. The plugin is a separate process with a
  "one JSON per invocation" protocol; importing `box.api` in-process would
  break the contract with the launcher. I keep using the CLI through a
  subprocess (syntax verified identical in 26.9.138).
- Session `stop`: NO. The CLI doesn't expose stop/sessions (only `box.api`
  does), and without a subprocess surface there's no faithful passthrough.
  Documented here instead.
- box's own GUI (`box-gui`): NO. CorkyTux is already the frontend.

## What I did adopt

- Vendor updated to 26.9.138 (84 files, LICENSE BSD-3 untouched).
- `install box` fixed: the new repo plus both layouts (`box-rpg/src`, legacy
  `src`). It used to fail with "no usable box-rpg sources".
- `run` forwards `--gamemode`, `--sdk`, `--ci-mount` (opt-in, upstream still
  denies them by default).
- Real sessions: `sessions` / `stop` (through `box.api` in a child process:
  stable identifier, PID-reuse-safe flock), `runtime remove`, `config show`.
  The launcher gives RPG games Play↔Stop, elapsed time and Stop (Stop used to
  be a no-op).
- Per-game consents in the UI (upstream model: explicit opt-in, off by
  default): network and writes, persisted as a visible standing consent.
- The `available` regex tolerates the format with sizes
  (`1. v0.117.0 (195.7 MB)`); before this every install failed.
- My own tests (`tests/test_rpgmaker.py`, 26), NOTICE with attribution,
  README with the version and the new flags.
- No user migration: config and cache already live under CorkyTux and the
  box-rpg formats are compatible (verified `status`, `scan`, `diagnose`,
  `cleanup list` live).

## Verification

- `status`: bundled 26.9.138, empty lists OK.
- `scan` in /tmp: MZ authoritative with title+entrypoint (valid package.json),
  MV by hint, 2k authoritative, unknown on an empty folder.
- `diagnose`: actionable messages without runtimes (no downloads: out of scope
  here).
- Existing installs: `~/.cache/CorkyTux/box-rpg` (runtimes, profiles,
  sessions) untouched; no legacy dirs to migrate.
