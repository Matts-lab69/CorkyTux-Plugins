# Emulator Manager Plugin for CorkyTux

Manage retro emulators from one place. Install AppImages or link your existing installs.

## Features

- **AppImage install** — download emulator AppImages from GitHub releases
- **Link existing emulators** — use emulators you already have installed
- **Custom executables** — point to any binary, not just AppImages
- **ROM detection** — auto-detects game files by extension

## Supported Emulators

| Emulator | System | Extensions |
|----------|--------|------------|
| melonDS | Nintendo DS | .nds, .srl, .dsi |
| Dolphin | GameCube / Wii | .iso, .gcm, .wbfs, .rvz, .wia |
| Mupen64Plus | Nintendo 64 | .z64, .n64, .v64, .rom |
| PCSX2 | PlayStation 2 | .iso, .bin, .img, .mdf, .nrg |
| PPSSPP | PlayStation Portable | .iso, .cso |
| RPCS3 | PlayStation 3 | .pkg, .iso |
| Ryujinx | Nintendo Switch | .nca, .xci, .nsp |
| Vita3K | PlayStation Vita | .vpk |
| Azahar | Nintendo 3DS | .3ds, .cia, .3dsx |
| DuckStation | PlayStation 1 | .iso, .bin, .cue, .img, .mdf |
| Cemu | Wii U | .wud, .wua, .rpx, .wux |
| DeSmuME | Nintendo DS | .nds, .srl, .dsi |

## Usage

### Install via AppImage

The plugin downloads the latest AppImage from GitHub releases.

```bash
emulator-manager corky-install Dolphin
```

### Link Existing Emulators

If you already have an emulator installed (via Flatpak, native package, or compiled from source), you can link it instead of downloading an AppImage.

**Find your emulator path:**

```bash
# Flatpak
which flatpak
flatpak list | grep -i dolphin

# Native package
which dolphin-emu
which pcsx2
which duckstation-qt

# AppImage (manually placed)
ls ~/Applications/*.AppImage

# Compiled from source
ls ~/build/emulator/bin/
```

**Link the emulator:**

```bash
# Link by name (uses default launch args)
emulator-manager corky-link Dolphin /usr/bin/dolphin-emu

# Link with custom launch args
emulator-manager corky-link PCSX2 /usr/bin/pcsx2 "-nofs -fullscreen {rom}"

# Link custom emulator (not in built-in list)
emulator-manager corky-link my-emulator /path/to/emulator "{rom}"
```

**Unlink an emulator:**

```bash
emulator-manager corky-unlink Dolphin
```

**List linked emulators:**

```bash
emulator-manager corky-linked
```

### Flatpak Emulators

Flatpak apps are sandboxed. To link them, use the Flatpak run command:

```bash
# Find the Flatpak application ID
flatpak list | grep -i dolphin

# Link with flatpak run
emulator-manager corky-link Dolphin /usr/bin/flatpak "run org.DolphinEmu.dolphin-emu -e {rom}"
```

### AppImage Emulators (manually placed)

If you have AppImages in a custom location:

```bash
emulator-manager corky-link PCSX2 ~/Applications/pcsx2.AppImage
```

## Launch Arguments

Use `{rom}` as placeholder for the ROM path:

| Emulator | Default Args |
|----------|--------------|
| melonDS | `{rom}` |
| Dolphin | `-e {rom}` |
| Mupen64Plus | `{rom}` |
| PCSX2 | `-nofs -fullscreen {rom}` |
| PPSSPP | `{rom}` |
| RPCS3 | `{rom}` |
| Ryujinx | `{rom}` |
| Vita3K | `{rom}` |
| Azahar | `{rom}` |
| DuckStation | `-batch {rom}` |
| Cemu | `-f {rom}` |
| DeSmuME | `{rom}` |

Custom launch args override the defaults when linking.

## Game Registration

Register a game directory with an emulator to add it to the emulator's game list:

```bash
emulator-manager corky-register-game Dolphin /path/to/game
```

## Troubleshooting

### "File not executable"

Make the binary executable:

```bash
chmod +x /path/to/emulator
```

### Flatpak not launching

Flatpak apps may need additional permissions. Try running manually first:

```bash
flatpak run org.DolphinEmu.dolphin-emu
```

### ROM not detected

Check that your ROM file has the correct extension. The plugin detects files by extension, not by content.
