<p align="center">
  <img src="https://raw.githubusercontent.com/Matts-lab69/CorkyTux-Launcher/main/qml/assets/corkytux.png" width="120" alt="CorkyTux Logo">
</p>

<h1 align="center">CorkyTux Plugins</h1>

<p align="center">
  <strong>Official plugins for CorkyTux Launcher</strong><br>
  Extend functionality with dependency installation, DLL overrides, and emulator management.
</p>

<p align="center">
  <a href="#available-plugins">Plugins</a> •
  <a href="#installation">Installation</a> •
  <a href="#plugin-documentation">Documentation</a> •
  <a href="#developing-plugins">Develop</a> •
  <a href="#license">License</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Plugin--Count-3-blue" alt="Plugins">
  <img src="https://img.shields.io/badge/Emulators-12%2B-green" alt="Emulators">
  <img src="https://img.shields.io/badge/License-AGPL--3.0-purple" alt="License">
</p>

---

## What is this?

CorkyTux Plugins is a collection of **official plugins** that extend the capabilities of the [CorkyTux Launcher](https://github.com/Matts-lab69/CorkyTux-Launcher). Each plugin is a standalone executable that integrates with CorkyTux via a simple JSON protocol.

---

## Available Plugins

### 1. Dependency Installer

**Version:** 2.1.0 | **Capabilities:** `scan`, `install`

Smart dependency detection for Windows games running via Proton/Wine.

| Feature | Description |
|---------|-------------|
| **DLL import scanning** | Analyzes game executables to detect which DLLs they import |
| **Wine/Proton analysis** | Checks what Wine/Proton already provides natively |
| **Smart recommendations** | Only suggests dependencies that are truly needed |
| **63 dependencies** | Supports VC++, DirectX, .NET, and more |
| **Auto-install** | Downloads and installs missing components automatically |

**Usage:**
```bash
# Scan a game directory for missing dependencies
dependency-installer scan /path/to/game

# Scan with a specific Wine prefix
dependency-installer scan /path/to/game --prefix /path/to/prefix

# Install specific dependencies
dependency-installer install --prefix /path/to/prefix --proton /path/to/proton vcrun2019 dxvk
```

**Supported Dependencies:**
- Visual C++ Redistributables (2005-2022)
- DirectX Runtime
- .NET Framework (3.5, 4.0, 4.8)
- XNA Framework
- OpenAL
- PhysX
- And more...

---

### 2. DLL Overrides Automator

**Version:** 1.1.0 | **Capabilities:** `scan`, `patch`, `unpatch`, `status`, `install`

Automatically configures DLL overrides for Windows games. Scans game directories, generates `WINEDLLOVERRIDES`, and manages DLL patching when your game needs custom DLLs.

| Feature | Description |
|---------|-------------|
| **Directory scanning** | Analyzes game folders for DLL files |
| **Override generation** | Creates proper WINEDLLOVERRIDES strings |
| **DLL patching** | Applies custom DLL replacements |
| **Status tracking** | Shows current override state |
| **Undo support** | Remove patches and restore originals |

**Usage:**
```bash
# Scan a game for DLL issues
dll-overrides-automator scan /path/to/game

# Apply recommended overrides
dll-overrides-automator patch /path/to/game

# Check current status
dll-overrides-automator status /path/to/game

# Remove all patches
dll-overrides-automator unpatch /path/to/game
```

---

### 3. Emulator Manager

**Version:** 1.1.0 | **Capabilities:** `emulators`

Manage retro emulators from one place. Install AppImages or link existing installs (Flatpak, native, compiled).

| Feature | Description |
|---------|-------------|
| **AppImage install** | Download emulator AppImages from GitHub releases |
| **Link existing** | Use emulators you already have installed |
| **Custom executables** | Point to any binary, not just AppImages |
| **ROM detection** | Auto-detects game files by extension |
| **Flatpak support** | Link Flatpak-installed emulators |

**Supported Emulators:**

| Emulator | System | Extensions |
|----------|--------|------------|
| Dolphin | GameCube / Wii | `.iso`, `.gcm`, `.wbfs`, `.rvz`, `.wia` |
| PCSX2 | PlayStation 2 | `.iso`, `.bin`, `.img`, `.mdf`, `.nrg` |
| PPSSPP | PlayStation Portable | `.iso`, `.cso` |
| RPCS3 | PlayStation 3 | `.pkg`, `.iso` |
| Ryujinx | Nintendo Switch | `.nca`, `.xci`, `.nsp` |
| melonDS | Nintendo DS | `.nds`, `.srl`, `.dsi` |
| DeSmuME | Nintendo DS | `.nds`, `.srl`, `.dsi` |
| Mupen64Plus | Nintendo 64 | `.z64`, `.n64`, `.v64`, `.rom` |
| DuckStation | PlayStation 1 | `.iso`, `.bin`, `.cue`, `.img`, `.mdf` |
| Cemu | Wii U | `.wud`, `.wua`, `.rpx`, `.wux` |
| Vita3K | PlayStation Vita | `.vpk` |
| Azahar | Nintendo 3DS | `.3ds`, `.cia`, `.3dsx` |

**Usage:**
```bash
# Install an emulator via AppImage
emulator-manager corky-install Dolphin

# Link an existing emulator
emulator-manager corky-link Dolphin /usr/bin/dolphin-emu

# Link with custom launch args
emulator-manager corky-link PCSX2 /usr/bin/pcsx2 "\-nofs -fullscreen {rom}"

# Link a Flatpak emulator
emulator-manager corky-link Dolphin /usr/bin/flatpak "run org.DolphinEmu.dolphin-emu -e {rom}"

# List linked emulators
emulator-manager corky-linked

# Unlink an emulator
emulator-manager corky-unlink Dolphin
```

---

## Installation

### Via CorkyTux Launcher (Recommended)

1. Open CorkyTux Launcher
2. Go to **Settings** → **Plugins**
3. Browse **Available Plugins**
4. Click **Install** on the desired plugin
5. Enable the plugin with the toggle switch

### Manual Installation

1. Download the plugin from the [Releases page](https://github.com/Matts-lab69/CorkyTux-Plugins/releases)
2. Extract to `~/.config/CorkyTux/plugins/`
3. Restart CorkyTux Launcher
4. Enable the plugin in Settings → Plugins

---

## Plugin Protocol

All plugins communicate with CorkyTux via a simple **JSON protocol** over stdout.

### Input

Plugins receive arguments via command-line:
```bash
./plugin <command> [args...]
```

### Output

Plugins return a single JSON document on stdout:
```json
{
  "ok": true,
  "type": "done",
  "installed": ["vcrun2019", "dxvk"],
  "failed": []
}
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `2` | Usage error / invalid path |
| `3` | Install failed |

---

## Developing Plugins

### Plugin Structure

```
my-plugin/
├── my-plugin          # Executable (bash, Python, compiled binary, etc.)
├── plugin.json        # Manifest file
└── README.md          # Documentation
```

### plugin.json

```json
{
  "name": "My Plugin",
  "version": "1.0.0",
  "entry": "my-plugin",
  "description": "Description of what the plugin does",
  "capabilities": ["scan", "install"],
  "protocol": {
    "stdout": "single JSON document per invocation",
    "exitCodes": { "0": "ok", "2": "usage error", "3": "install failed" }
  }
}
```

### Capabilities

| Capability | Description |
|------------|-------------|
| `scan` | Can scan/analyze game directories |
| `install` | Can install dependencies or components |
| `patch` | Can apply patches to games |
| `unpatch` | Can remove patches from games |
| `status` | Can report current state |
| `emulators` | Provides emulator management |

### Testing Locally

```bash
# Test your plugin directly
./my-plugin scan /path/to/game

# Check output format
./my-plugin scan /path/to/game | jq .
```

---

## Plugin Registry

CorkyTux fetches available plugins from the GitHub releases of this repository. To publish a plugin:

1. Create a release on GitHub
2. Include the plugin executable and `plugin.json` in the release assets
3. CorkyTux will automatically detect and list it in Settings → Plugins

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-plugin`)
3. Commit your changes (`git commit -m 'Add amazing plugin'`)
4. Push to the branch (`git push origin feature/amazing-plugin`)
5. Open a Pull Request

### Plugin Ideas

- **Save game manager** — Backup and restore save files
- **Controller configurator** — Map and configure gamepads
- **Shader manager** — Apply custom shaders to games
- **Audio configurator** — Set up audio devices per game
- **Performance monitor** — Real-time FPS and resource usage

---

## License

This project is licensed under the **GNU Affero General Public License v3.0** — see the [LICENSE](../LICENSE) file for details.

---

## Acknowledgments

- [CorkyTux Launcher](https://github.com/Matts-lab69/CorkyTux-Launcher) — The launcher these plugins extend
- [Wine](https://www.winehq.org/) — Windows compatibility layer
- [Proton](https://github.com/ValveSoftware/Proton) — Valve's compatibility layer
- All the emulator developers who make Linux gaming possible

---

<p align="center">
  Made with care for the Linux gaming community.
</p>
