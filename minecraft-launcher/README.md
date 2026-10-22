# Minecraft Launcher (guide)

The `minecraft-launcher` plugin is full Minecraft Java inside CorkyTux
(accounts, versions, isolated instances, loaders, mods, logs).

## Requirements

```bash
python3 --version                 # 3.10+
pip install --user requests minecraft_launcher_lib psutil
java -version                     # Java 8/17/21/25 depending on the game version
```

The plugin detects Java in `~/jdk`, `/opt/jvm`, `/usr/lib/jvm` and
`update-alternatives` (cached versions):

```bash
./minecraft-launcher java-detect
./minecraft-launcher java-required --version 1.20.1  # which Java that version needs
./minecraft-launcher manifest-java --mc-version 1.20.1
```

## Accounts

| Type | UI | Terminal |
|------|----|----------|
| Offline (any name) | Header > account | `./minecraft-launcher offline --name Steve` |
| Microsoft | Header > account (Azure: placeholder, partial flow) | `./minecraft-launcher auth ...` |
| Ely.by | Header > account | `./minecraft-launcher ely-auth --username USER --password PASS` |

Management:

```bash
./minecraft-launcher auth-config --show          # show current account
./minecraft-launcher unaccount --account ID      # log out one account
./minecraft-launcher ely-refresh --account ID    # refresh Ely.by token
./minecraft-launcher ely-validate --account ID   # validate session
./minecraft-launcher ely-skin --name USER        # show skin
```

`ID` is the `account_id` returned by `offline`, `auth` or `ely-auth`.

## Versions and instances

```bash
./minecraft-launcher versions                       # available versions
./minecraft-launcher install --version 1.20.1       # installs the client
./minecraft-launcher loader-versions --loader fabric --mc-version 1.20.1
```

In the UI: **ADD INSTANCE** (Custom / Modpack / Import) with a Modrinth/CurseForge
dropdown, Library tiles + detail (Overview / Addons / Logs / Settings).
An empty `installed_versions` at first is **normal**.

The CLI addresses an instance with `--mc-dir PATH` (the instance directory), not
with an instance name. Use the path shown in the instance settings.

## Mods: Modrinth

Browse with multi-select + queue + progress (tile size + preview + Compact under Appearance):

```bash
./minecraft-launcher mod-search --query sodium --mc-version 1.20.1
./minecraft-launcher mod-versions --project-id PROJECT_ID --mc-version 1.20.1
./minecraft-launcher mod-install --project-id PROJECT_ID --version-id VERSION_ID --mc-dir PATH
./minecraft-launcher mods-list
./minecraft-launcher mod-toggle --file PATH
./minecraft-launcher mod-check-updates --mc-dir PATH
./minecraft-launcher mod-update --file PATH
./minecraft-launcher modpack-install --project-id PROJECT_ID --version-id VERSION_ID
./minecraft-launcher modpack-import --path pack.mrpack
```

Replace `PROJECT_ID`, `VERSION_ID` and `PATH` with real values. The uppercase
forms in the old examples were placeholders, not literal arguments.

## Mods: CurseForge

Uses the **integrated public key** (the user's personal key errored — don't use one):

```bash
./minecraft-launcher curse-test
./minecraft-launcher cf-search --query jei --mc-version 1.20.1
./minecraft-launcher cf-versions --mod-id MOD_ID --mc-version 1.20.1
./minecraft-launcher cf-install --mod-id MOD_ID --file-id FILE_ID --mc-dir PATH
./minecraft-launcher cf-modpack-install --pack-id PACK_ID --file-id FILE_ID
```

## Play

```bash
./minecraft-launcher launch --version 1.20.1 [--account ID]
./minecraft-launcher status            # state / playing
./minecraft-launcher stop              # stop
./minecraft-launcher setup             # first-time setup
```

All requests use 120s timeouts (previously silent 30min hangs).

## Troubleshooting

- **Wrong Java**: run `java-detect` and pin the path with `java-use`.
- **Microsoft never completes**: Azure is a placeholder — use offline or Ely.by meanwhile.
- **CurseForge 403**: check with `curse-test`; don't set a manual key.
- Report bugs in [Issues](https://github.com/Matts-lab69/CorkyTux-Plugins/issues).

## Credits

- [minecraft_launcher_lib](https://github.com/jakobkmar/minecraft_launcher_lib) (Python library) — install/launch backend.
- Mojang/Microsoft session servers, Ely.by auth, and the Modrinth + CurseForge APIs this plugin talks to.
