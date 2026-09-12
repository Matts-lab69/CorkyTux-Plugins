# AppImage Launcher (guide)

The `appimage-launcher` plugin runs and organizes your `.AppImage` files
(great for preserving emulators and loose games).

## Commands

```bash
./appimage-launcher status
./appimage-launcher scan ~/AppImages
./appimage-launcher integrate ~/AppImages/Dolphin.AppImage  # copies to ~/Applications
./appimage-launcher run ~/Applications/Dolphin.AppImage
./appimage-launcher icon ~/Applications/Dolphin.AppImage    # extracts the icon
./appimage-launcher remove ~/Applications/Dolphin.AppImage
```

## From CorkyTux

1. Install the plugin (Settings > Plugins) or copy `appimage-launcher` +
   `plugin.json` to `~/.local/share/CorkyTux/plugins/appimage-launcher/`.
2. Scan your AppImage folder, integrate the ones you use into `~/Applications`
   and launch them detached from the library.

## Notes

- Don't forget the executable bit (`chmod +x *.AppImage`).
- If an AppImage needs `--no-sandbox` or `libfuse2`, the plugin will tell you.
- Report bugs in [Issues](https://github.com/Matts-lab69/CorkyTux-Plugins/issues).
