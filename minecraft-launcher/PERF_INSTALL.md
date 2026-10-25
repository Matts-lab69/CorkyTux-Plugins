# Minecraft install performance

Measured 2026-10-24. Linux, Python 3.14.6, `minecraft-launcher-lib` from the
user site, no CurseForge API key. Every run used a temporary `HOME`, `XDG_*`
directories and a temporary Minecraft directory; the real launcher state was
only read.

## Method

- Harness: `/tmp/opencode/perf_harness.py`. It starts the plugin, timestamps
  every JSON event, and reads stdout in two modes:
  - `fast`: drain the pipe as fast as possible. This is the plugin time.
  - `ui`: consume at most one event every 50 ms. This models
    `pump_to_idle` in the launcher (`src/backend/plugin_process.rs:655`).
- Vanilla: Minecraft 1.12.2 in a fresh directory (`install --version 1.12.2`).
- Modpack: Modrinth "Optimized fps" 1.12.2 1.5.6, 13 mods (28,399,847 B),
  2,489,584 B of overrides, Forge 14.23.5.2860. It was installed into the
  already populated 1.12.2 directory, so the vanilla base is warm.
- Baseline: the 13 mod files with `requests`, one connection and eight
  connections, no hashing, no writes.
- Events were grouped by the plugin stage; bytes and files were counted on
  disk after the run.

## Vanilla 1.12.2, cold directory (main before the throttle)

| Phase | Files | Bytes | Seconds | % of wall |
|---|---:|---:|---:|---:|
| Manifest + libraries | 35 | 41,056,434 | 5.19 | 13.6 |
| Assets (objects) | 1,290 | 129,367,550 | 15.24 | 39.8 |
| Client jar | 1 | 10,180,113 | 1.40 | 3.7 |
| Java runtime | 304 | 235,179,149 | 13.85 | 36.2 |
| Metadata, index, gaps | 9 | 1,846,081 | 2.61 | 6.8 |
| **Total** | **1,639** | **417,629,327** | **38.29** | **100** |

The run emitted 3,357 events. At one event per 50 ms the progress dialog
needs 167.9 s for a 38.3 s install, 4.4 times the plugin time.

The Java runtime is the surprise: 235 MB for 1.12.2, installed inside the
instance directory. On this machine the real state shows 105 MB
(`neoforge-21.1.218`) and 111 MB (`fabric-loader-0.19.5-26.3`) per instance,
plus a leaked `.staging-*/runtime` of 111 MB. PolyMC shares one runtime; this
plugin does not.

## Modpack, warm 1.12.2 base

| Phase | Files | Bytes | Seconds |
|---|---:|---:|---:|
| `.mrpack` download | 1 | 1,710,715 | 0.96 |
| Mod downloads (13, sequential) | 13 | 28,399,847 | 8.13 |
| Overrides extraction | - | 2,489,584 | 0.02 |
| Forge loader + base checks | - | about 50,970,000 | 23.4 |
| **Total** | - | - | **34.85** |

Baseline for the same 28.4 MB of mods: 15.65 s with one connection
(1.81 MB/s) and 5.70 s with eight (4.98 MB/s). The plugin's 8.13 s is
3.5 MB/s, consistent with sequential per-file downloads.

## Event count before and after

| Run | Plugin seconds | Events | UI model seconds |
|---|---:|---:|---:|
| Plugin 1.1.1, warm base | 19.5 | 10,454 | 522.7 |
| main before the change | 34.8 | 10,505 | 526.9 (measured) |
| main with the throttle | 20.2 | 128 | 17.9 (measured) |

The same warm pack went from a 527 s dialog to 17.9 s. The plugin itself
changed little; the event volume did. Vanilla warm shows the same shape:
1,726 events with 1.1.1 against 18 with the throttle. A cold vanilla run
with the throttle was not repeated to avoid a second 417 MB download; at
10 events/s it would emit about 400 events, so about 20 s of UI drain
instead of 168 s.

## Findings

1. **The launcher pump is the main bottleneck.** `pump_to_idle` reads one
   event per 50 ms (`src/backend/plugin_process.rs:655-663`). It has been
   like this since the 3.0.0 rewrite (`da1d4ab`), so it is not a 3.2.0
   regression. The plugin is not blocked: the fast reader finishes in 35 s
   while the UI model needs 527 s, because the pipe reader is a separate
   thread and the channel is unbounded.
2. **The plugin forwards every mll per-file callback.** `_install_callbacks`
   used to emit one status and one progress event per library and asset, in
   every install pass. A 13-mod pack produced 10,375 `downloading` events.
   mll emits them in `install.py` around lines 93-142.
3. **The Java runtime is copied into every instance.** 105-235 MB per
   instance, plus staging and backup copies.
4. **Mod downloads are sequential.** `mll.mrpack.install_mrpack` calls
   `download_file` once per mod (`mrpack.py:130`) and `download_file` uses
   `requests.get` when no session is passed. Eight connections reduce the
   sample from 15.7 s to 5.7 s; at 300 mods the per-file handshakes add up.
5. **The plugin's own downloader opens a new connection per file.**
   `_download_with_progress` calls `urllib.request.urlopen` for every mod
   (CurseForge path). There is no session and no keep-alive.
6. **Discarded as the main cause:** small read blocks (mll uses
   `shutil.copyfileobj`), hash checks (the warm 417 MB check takes 3.3 s),
   sleeps or retries (none observed), and the reduced plugin environment
   (the same code path runs at the same speed). DNS and proxy behavior of
   the user's network were not measured.

## Proposal

- Launcher, separate PR: drain the event channel in batches per 50 ms tick,
  keep the last progress per stage and every terminal event. This fixes old
  plugins and every other verbose plugin. Evidence above; not mixed with
  3.2.0.
- Plugin 1.3.0: the throttle is implemented in this branch. Next, bounded
  concurrency (8-16) with session reuse for mod downloads, `.part` plus size
  and hash plus `os.replace` (also closes P2), and a shared Java runtime
  instead of one per instance. None of those are implemented here.
- 1.2.0 stays as prepared (URL encoding only). The performance work does not
  enter the 3.2.0 release without approval.

## What the UI cost is (and what it is not)

The `ui` figures (526.9 s, 17.9 s) are a **model**, not a measurement of the
real application. The harness consumes one event every 50 ms, exactly like
`pump_to_idle` (`src/backend/plugin_process.rs:655`), but it does not render
GTK, does not call `drive_progress`, and does not touch the main loop. The
real app may spend more or less than 50 ms per event on rendering; the 50 ms
cadence is the hard ceiling either way, and the event count is the stable part
of the measurement. The plugin wall times (38.29 s, 20.2 s) are real.

## What the throttle preserves

The throttle is in `_install_callbacks` (status and progress) and keeps:

- every terminal event (`done`/`error` is outside the throttle),
- every change of stage category (manifest, libraries, assets, client jar,
  java runtime, installation complete),
- the first event of a burst and the last value when the burst ends,
- at most one progress event every 0.1 s and one status event every 0.25 s.

It drops intermediate per-file progress and per-file status only. The stage
text of non-file statuses is unchanged; per-file "Download <name>" statuses
are coalesced into "Downloading files" / "Extracting files".

## Installing the perf branch locally (code only, state intact)

No game, prefix, save or registry file is touched. Only the plugin entry
changes.

```
# 1. record before
P=~/.local/share/CorkyTux/plugins/minecraft-launcher
sha256sum "$P/minecraft-launcher" > /tmp/plugin-before.sha256
# 2. timestamped code backup (the existing .bak-20261011-223733 stays)
cp -a "$P/minecraft-launcher" "$P/minecraft-launcher.bak-$(date +%Y%m%d-%H%M%S)"
# 3. build from the perf branch in a worktree you own
mkdir -p ~/wt
git -C /home/mattsgaming/CorkyTux-Plugins worktree add ~/wt/a-perf origin/perf/minecraft-install
cd ~/wt/a-perf
tools/plugin-tarball.sh minecraft-launcher /tmp/opencode/rel-3.2.0/minecraft-launcher-throttle
# 4. extract over the installed dir (no delete; tests/ and state stay)
tar xzf /tmp/opencode/rel-3.2.0/minecraft-launcher-throttle/minecraft-launcher-1.2.0.tar.gz \
  -C "$P/.."
# 5. diff
sha256sum "$P/minecraft-launcher"
cat /tmp/plugin-before.sha256
```

Rollback: copy the timestamped backup back over the entry, or reinstall from
the published 1.2.0 tarball.

## What to compare visually

Use one vanilla instance and one modpack instance, before and after:

- total time from "Installing modpack" to the dialog closing,
- how the progress bar advances: with the flood it stalls and jumps; with
  the throttle it moves smoothly,
- whether the instance is usable afterwards (same files, same launch).

## Alternative tarball (not published)

`minecraft-launcher-1.2.0-throttle.tar.gz` is built from `perf/minecraft-install`
with the same 1.2.0 version string, so it can be swapped in for testing
without changing the manifest. sha256:
`81a6f9e64399149af9b5faa04d14635caa84d96113fad5a0b3a3e5995df84203`.
It is **not** published and does not replace the 1.2.0 release tarball. The
decision to ship the throttle in 1.2.0 or 1.3.0 is pending your test.

## Not measured

- The real CurseForge path and Karmaland (300 mods); no API key. The event
  pump and the base install are the same, and the mod count scales the
  per-file costs.
- The GTK rendering cost per event; the app was not run. The 50 ms pump is
  the hard ceiling regardless of rendering cost.
- The previous launcher binary; the pump code is unchanged since 3.0.0.
- CDN performance under load; one run per configuration.
