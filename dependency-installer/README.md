# Dependency Installer (guide)

The `dependency-installer` plugin scans a Windows game directory for imported
DLLs, compares them with what Wine/Proton provides, and installs only the
missing runtimes.

## Install

Copy `dependency-installer` and `plugin.json` to
`~/.local/share/CorkyTux/plugins/dependency-installer/` and keep the executable
bit set. The launcher can also install it from Settings > Plugins.

## Commands

```bash
./dependency-installer scan /path/to/game
./dependency-installer scan /path/to/game --prefix /path/to/prefix
./dependency-installer install --prefix /path/to/prefix --proton /path/to/proton vcrun2019 dxvk
```

`scan` is read-only and returns the detected dependencies. `install` writes to
the supplied Wine prefix and may download components, so review the prefix
before running it.

## Output

One JSON document on stdout. Errors use `{"ok": false, "error": "..."}` and
exit code `2` for usage/invalid paths or `3` for a failed install.

## Notes

- Supported components include Visual C++ redistributables, DirectX, .NET, XNA,
  OpenAL and PhysX.
- The launcher calls this plugin with absolute paths; no shell is involved.
- Report bugs in [Issues](https://github.com/Matts-lab69/CorkyTux-Plugins/issues).
