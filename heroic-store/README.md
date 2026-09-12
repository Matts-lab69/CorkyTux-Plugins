# Heroic Store — Epic & GOG shop (guide)

The `heroic-store` plugin brings Epic Games + GOG into CorkyTux using its
**own** `legendary` / `gogdl` binaries (you don't need them installed).

## Plugin installation

1. In CorkyTux go to **Settings > Plugins** and install **Heroic Store**,
   or download `heroic-store-*.tar.gz` from
   [Releases](https://github.com/Matts-lab69/CorkyTux-Plugins/releases)
   and extract it to `~/.local/share/CorkyTux/plugins/heroic-store/`
   (`heroic-store` + `plugin.json`, executable bit set).
2. Restart the launcher (`pkill -x corkytux`) and open the **Store** page.

## First step: `setup` (required once)

The plugin downloads its own `legendary` / `gogdl` to:

```text
~/.local/share/CorkyTux/plugins/heroic-store/bin/
```

- From the UI it runs automatically the first time.
- Manual:
  ```bash
  ./heroic-store setup
  ./heroic-store status   # checks binaries + session
  ```

## Log in

### Epic Games (embedded login)

1. On the **Epic** tab press log in.
2. An embedded WebKit window opens with the Epic website (needs PyGObject
   WebKitGTK 6.0 for GTK4 — e.g. `net-libs/webkit-gtk:6` on Gentoo; if it
   fails, paste the code manually below).
3. Log in normally (Epic username/password/2FA).
4. The plugin **auto-captures** the authorization code — nothing to copy.
5. You'll see your avatar + name in the header. To leave: logout.

Terminal fallback (if the embedded window fails):

```bash
./heroic-store login-window --store epic
./heroic-store auth --store epic --code YOUR_CODE
```

### GOG (own token)

1. On the **GOG** tab press log in.
2. The GOG website opens to authorize; the plugin captures its own token.
3. You'll see your profile in the header. To leave: logout.

```bash
./heroic-store login-window --store gog
./heroic-store auth --store gog --code YOUR_CODE
./heroic-store logout    # closes the current session
```

## Library, promos and deals

| Action | Where | Command |
|--------|-------|---------|
| View library | Epic/GOG tabs (covers + View sheet with cover+desc) | `./heroic-store library --store epic` / `--store gog` (`--refresh` to force) |
| Free games | Free games section (100% off only) | `./heroic-store free-promos` |
| Epic deals | Deals section (%, price and end date verified) | `./heroic-store epic-deals` |
| Search/buy GOG | Search + Buy with prices | `./heroic-store gog-store-search --query "hollow knight"` |
| Search Epic | Button opening the browser (Epic has no public search API) | — |
| GOG details | Game sheet | `./heroic-store game-info --store gog --app-id ID` (description only arrives via gameDetails) |

## Install and play

1. Press **Install** on the sheet (or `install --store epic --app-id ID [--path DIR]`).
   Games default to `~/Games/Heroic` and show up in the **native library**
   with the launcher's Proton/prefix.
2. Epic launches via `legendary launch` with game token, epicapp and sandbox
   (EAC/EOS compatible). Fall Guys verified working.
3. Check launch data: `./heroic-store launch-info --store epic --app-id ID`
4. Uninstall: `./heroic-store uninstall --store epic --app-id ID`
5. Import what's already installed (Heroic or another path):
   `./heroic-store heroic-scan` (own session + Heroic, `~/Games/Heroic` only)

## EOS / EAC / umu

- EOS code: `./heroic-store eos-code`
- umu status: `./heroic-store umu-status` · install umu 1.4.4 into `tools/umu`:
  `./heroic-store umu-setup`
- EAC/BattlEye and EOS are configured per game in CorkyTux (game settings).

## Troubleshooting

- **Epic login doesn't capture**: retry `login-window`; complete 2FA in the window.
- **GOG without description**: normal, it only arrives via the game's gameDetails.
- **Epic game won't start**: check `launch-info`, try another Proton, check EAC/EOS.
- **Still to test**: embedded GOG login, installing Epic games from Stores,
  EAC on a fresh prefix, Deals/Claim with new offers — report in
  [Issues](https://github.com/Matts-lab69/CorkyTux-Plugins/issues).
