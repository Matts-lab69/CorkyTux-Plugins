# AppImage Launcher (guía)

Plugin `appimage-launcher`: ejecuta y organiza tus `.AppImage`
(ideal para preservar emuladores y juegos sueltos).

## Comandos

```bash
./appimage-launcher status
./appimage-launcher scan ~/AppImages
./appimage-launcher integrate ~/AppImages/Dolphin.AppImage  # copia a ~/Applications
./appimage-launcher run ~/Applications/Dolphin.AppImage
./appimage-launcher icon ~/Applications/Dolphin.AppImage    # extrae icono
./appimage-launcher remove ~/Applications/Dolphin.AppImage
```

## Desde CorkyTux

1. Instala el plugin (Settings > Plugins) o copia `appimage-launcher` +
   `plugin.json` a `~/.local/share/CorkyTux/plugins/appimage-launcher/`.
2. Escanea tu carpeta de AppImages, integra en `~/Applications` los que uses
   y lánzalos detached desde la biblioteca.

## Notas

- No olvides el permiso de ejecución (`chmod +x *.AppImage`).
- Si un AppImage pide `--no-sandbox` o `libfuse2`, el plugin te lo indicará.
- Reporta errores en [Issues](https://github.com/Matts-lab69/CorkyTux-Plugins/issues).
