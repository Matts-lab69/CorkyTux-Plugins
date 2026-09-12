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
./minecraft-launcher manifest-java
```

## Accounts

| Type | UI | Terminal |
|------|----|----------|
| Offline (any name) | Header > account | `./minecraft-launcher offline --name Steve` |
| Microsoft | Header > account (Azure: placeholder, partial flow) | `./minecraft-launcher auth ...` |
| Ely.by | Header > account | `./minecraft-launcher ely-auth --login USER --password PASS` |

Management:

```bash
./minecraft-launcher auth-config       # show current account
./minecraft-launcher unaccount         # log out
./minecraft-launcher ely-refresh       # refresh Ely.by token
./minecraft-launcher ely-validate      # validate session
./minecraft-launcher ely-skin --show   # show skin
```

## Versions and instances

```bash
./minecraft-launcher versions          # available versions
./minecraft-launcher install --version 1.20.1   # installs the client
./minecraft-launcher loader-versions --loader fabric --mc 1.20.1
```

In the UI: **ADD INSTANCE** (Custom / Modpack / Import) with a Modrinth/CurseForge
dropdown, Library tiles + detail (Overview / Addons / Logs / Settings).
An empty `installed_versions` at first is **normal**.

## Mods: Modrinth

Browse with multi-select + queue + progress (tile size + preview + Compact under Appearance):

```bash
./minecraft-launcher mod-search --query sodium --mc 1.20.1
./minecraft-launcher mod-versions --project-ID --mc 1.20.1
./minecraft-launcher mod-install --project-ID --version-ID --instance MY_ENV
./minecraft-launcher mods-list --instance MY_ENV
./minecraft-launcher mod-toggle --instance MY_ENV --mod sodium --off
./minecraft-launcher mod-check-updates --instance MY_ENV
./minecraft-launcher mod-update --instance MY_ENV --all
./minecraft-launcher modpack-install --pack-ID --version-ID
./minecraft-launcher modpack-import --file pack.mrpack
```

## Mods: CurseForge

Uses the **integrated public key** (the user's personal key errored — don't use one):

```bash
./minecraft-launcher curse-test
./minecraft-launcher cf-search --query jei --mc 1.20.1
./minecraft-launcher cf-versions --project-ID --mc 1.20.1
./minecraft-launcher cf-install --project-ID --file-ID --instance MY_ENV
./minecraft-launcher cf-modpack-install --project-ID --file-ID
```

## Play

```bash
./minecraft-launcher launch --instance MY_ENV
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
