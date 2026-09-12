# RPG Maker Runtime (guía)

Plugin `rpgmaker-runtime`: ejecuta juegos RPG Maker **MV/MZ** (NW.js) y
**2000/2003** (EasyRPG) gracias a la lógica `box-rpg` incluida en `vendor/`
(ver créditos en el README principal).

## Cómo funciona

- `scan` encuentra juegos RPG Maker en una carpeta (detecta MV/MZ vs 2000/2003).
- `diagnose` dice qué runtime falta y cómo arreglarlo.
- `install` descarga/instala el runtime necesario.
- `run` lanza el juego con el perfil adecuado.

```bash
./rpgmaker-runtime status
./rpgmaker-runtime scan /ruta/a/mis/juegos
./rpgmaker-runtime diagnose "/ruta/a/mi juego"
./rpgmaker-runtime install --runtime easyrpg
./rpgmaker-runtime run "/ruta/a/mi juego"
```

## Tipos soportados

| Motor | Runtime | Notas |
|-------|---------|-------|
| RPG Maker MV / MZ | NW.js | se resuelve/instala vía `box-rpg` |
| RPG Maker 2000 / 2003 | EasyRPG Player | se resuelve/instala vía `box-rpg` |

## Desde CorkyTux

1. Instala el plugin (Settings > Plugins) o copia `rpgmaker-runtime`,
   `plugin.json` y la carpeta `vendor/` a
   `~/.local/share/CorkyTux/plugins/rpgmaker-runtime/`.
2. Registra tu carpeta de juegos y usa scan/diagnose/run desde la UI.

## Problemas comunes

- **Falta NW.js o EasyRPG**: corre `diagnose` y luego `install`.
- **Juego en ZIP/RAR**: extráelo primero a una carpeta.
- Reporta errores en [Issues](https://github.com/Matts-lab69/CorkyTux-Plugins/issues).
