# RPG Maker: qué cambió upstream y qué se adopta

Comparación del vendor (`box-rpg` 26.9.21, sep-2026) con upstream actual
(`box-project`, tag 26.9.138, 2026-09-27). Fuente: tarball del tag,
`docs/box-rpg/api.md`, `README.md` y releases vía API de GitLab.

## Qué cambió upstream (relevante)

- El repo `christvh/box-rpg` se mudó al monorepo `christvh/box-project`
  (redirect 301); el backend vive en `box-rpg/src/`, no en `src/`.
- Nueva capa estable `box.api` (inspect, diagnose, runtime, launch,
  cleanup, interaction): la superficie bendecida para frontends. La CLI
  (`box.cli`) es un cliente delgado sobre ella.
- Lanzamiento supervisado: un juego = una sesión (`game already running`),
  `stop_session`, `poll_launch_status`, saves de EasyRPG migrados a
  `save/`, perfiles Chromium privados por juego.
- Nuevos flags de `launch`: `--gamemode`, `--sdk`, `--ci-mount`
  (además de `--allow-network`, `--allow-game-writes`, `--x11`,
  `--copy-root-file`, `--runtime` — esos ya los teníamos).
- `runtime remove`, `cleanup remove/all`, `uninstall`, `version_info`,
  updates de AppImage, i18n (es), tests propios extensos.
- Aislamiento sin cambios de diseño: Bubblewrap obligatorio, sin modo
  unsandboxed; red, escrituras y X11 con consentimiento por lanzamiento.

## Qué falta aquí (y por qué no se adopta)

- `box.api` en proceso: NO. El plugin es un proceso separado con
  protocolo "un JSON por invocación"; importar `box.api` en proceso
  rompería el contrato con el launcher. Se sigue usando la CLI por
  subprocess (sintaxis verificada idéntica en 26.9.138).
- `stop` de sesión: NO. La CLI no expone stop/sessions (solo `box.api`);
  sin superficie subprocess no hay passthrough fiel. Queda documentado.
- GUI propia de box (`box-gui`): NO. CorkyTux ya es el frontend.

## Qué se adopta (hecho)

- Vendor actualizado a 26.9.138 (84 ficheros + LICENSE BSD-3 intacta).
- `install box` reparado: repo nuevo + ambos layouts (`box-rpg/src`,
  `src` legacy). Antes fallaba con "no usable box-rpg sources".
- `run` reenvía `--gamemode`, `--sdk`, `--ci-mount` (opt-in, upstream
  sigue denegando por defecto).
- Tests propios (`tests/test_rpgmaker.py`), NOTICE con atribución,
  README con versión y flags nuevos.
- Sin migración de usuario: config/cache ya viven bajo CorkyTux y los
  formatos de box-rpg son compatibles (verificado `status`, `scan`,
  `diagnose`, `cleanup list` en vivo).

## Verificación

- `status`: bundled 26.9.138, listas vacías OK.
- `scan` en /tmp: MZ authoritative con título+entrypoint (package.json
  válido), MV por hint, 2k authoritative, unknown en vacío.
- `diagnose`: mensajes accionables sin runtimes (no se descargan:
  fuera de alcance en esta fase).
- Instalaciones existentes: `~/.cache/CorkyTux/box-rpg` (runtimes,
  profiles, sessions) intacto; sin dirs legacy que migrar.
