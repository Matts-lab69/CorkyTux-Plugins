# Minecraft Launcher (guía)

Plugin `minecraft-launcher`: Minecraft Java completo dentro de CorkyTux
(cuentas, versiones, instancias aisladas, loaders, mods, logs).

## Requisitos

```bash
python3 --version                 # 3.10+
pip install --user requests minecraft_launcher_lib psutil
java -version                     # Java 8/17/21/25 según versión del juego
```

El plugin detecta Java en `~/jdk`, `/opt/jvm`, `/usr/lib/jvm` y
`update-alternatives` (versiones cacheadas):

```bash
./minecraft-launcher java-detect
./minecraft-launcher java-required --version 1.20.1  # qué Java pide esa versión
./minecraft-launcher manifest-java
```

## Cuentas

| Tipo | UI | Terminal |
|------|----|----------|
| Offline (cualquier nombre) | Header > cuenta | `./minecraft-launcher offline --name Steve` |
| Microsoft | Header > cuenta (Azure: placeholder, flujo parcial) | `./minecraft-launcher auth ...` |
| Ely.by | Header > cuenta | `./minecraft-launcher ely-auth --login USER --password PASS` |

Gestión:

```bash
./minecraft-launcher auth-config       # ver cuenta actual
./minecraft-launcher unaccount         # cerrar sesión
./minecraft-launcher ely-refresh       # refrescar token Ely.by
./minecraft-launcher ely-validate      # validar sesión
./minecraft-launcher ely-skin --show   # ver skin
```

## Versiones e instancias

```bash
./minecraft-launcher versions          # versiones disponibles
./minecraft-launcher install --version 1.20.1   # instala cliente
./minecraft-launcher loader-versions --loader fabric --mc 1.20.1
```

En la UI: **ADD INSTANCE** (Custom / Modpack / Import) con dropdown
Modrinth/CurseForge, tiles de Library + detalle (Overview / Addons / Logs / Settings).
`installed_versions` vacío al principio es **normal**.

## Mods: Modrinth

Browse con multiselección + cola + progreso (tile size + preview + Compact en Appearance):

```bash
./minecraft-launcher mod-search --query sodium --mc 1.20.1
./minecraft-launcher mod-versions --project-ID --mc 1.20.1
./minecraft-launcher mod-install --project-ID --version-ID --instance MI_ENTORNO
./minecraft-launcher mods-list --instance MI_ENTORNO
./minecraft-launcher mod-toggle --instance MI_ENTORNO --mod sodium --off
./minecraft-launcher mod-check-updates --instance MI_ENTORNO
./minecraft-launcher mod-update --instance MI_ENTORNO --all
./minecraft-launcher modpack-install --pack-ID --version-ID
./minecraft-launcher modpack-import --file pack.mrpack
```

## Mods: CurseForge

Usa la **key pública integrada** (la key personal del usuario daba error, no la uses):

```bash
./minecraft-launcher curse-test
./minecraft-launcher cf-search --query jei --mc 1.20.1
./minecraft-launcher cf-versions --project-ID --mc 1.20.1
./minecraft-launcher cf-install --project-ID --file-ID --instance MI_ENTORNO
./minecraft-launcher cf-modpack-install --project-ID --file-ID
```

## Jugar

```bash
./minecraft-launcher launch --instance MI_ENTORNO
./minecraft-launcher status            # estado / jugando
./minecraft-launcher stop              # detener
./minecraft-launcher setup             # primera configuración
```

Todas las peticiones llevan timeout de 120s (antes había cuelgues silenciosos de 30min).

## Problemas comunes

- **Sin Java correcto**: `java-detect` y fija el path con `java-use`.
- **Microsoft no completa**: Azure en placeholder — usa offline o Ely.by mientras tanto.
- **CurseForge 403**: verifica con `curse-test`; no pongas key manual.
- Reporta errores en [Issues](https://github.com/Matts-lab69/CorkyTux-Plugins/issues).
