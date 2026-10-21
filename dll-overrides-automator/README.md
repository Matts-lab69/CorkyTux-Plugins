# DLL Overrides Automator (guide)

The `dll-overrides-automator` plugin scans a game directory, generates a
`WINEDLLOVERRIDES` value, and applies or removes the DLL patches a game needs.

## Install

Copy `dll-overrides-automator` and `plugin.json` to
`~/.local/share/CorkyTux/plugins/dll-overrides-automator/` and keep the
executable bit set. The launcher can also install it from Settings > Plugins.

## Commands

```bash
./dll-overrides-automator scan /path/to/game
./dll-overrides-automator patch /path/to/game
./dll-overrides-automator status /path/to/game
./dll-overrides-automator unpatch /path/to/game
./dll-overrides-automator install --game /path/to/game --prefix /path/to/prefix --installdir /path/to/game /path/to/installer.exe
```

`scan` and `status` are read-only. `patch` and `install` modify files in the
game directory; `unpatch` restores the backups it created.

## Output

One JSON document on stdout. Errors use `{"ok": false, "error": "..."}` and
exit code `2` for usage/invalid paths or `3` for a failed operation.

## Notes

- Backups are kept next to the patched files; do not delete them manually.
- The Launcher passes the game path as a separate argument, so spaces are safe.
- Report bugs in [Issues](https://github.com/Matts-lab69/CorkyTux-Plugins/issues).
