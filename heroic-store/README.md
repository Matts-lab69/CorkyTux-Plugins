# Heroic Store — Tienda Epic y GOG (guía)

Plugin `heroic-store`: Epic Games + GOG dentro de CorkyTux usando binarios
`legendary` / `gogdl` **propios** (no necesitas tenerlos instalados).

## Instalación del plugin

1. En CorkyTux ve a **Settings > Plugins** e instala **Heroic Store**,
   o descarga `heroic-store-*.tar.gz` de
   [Releases](https://github.com/Matts-lab69/CorkyTux-Plugins/releases)
   y extráelo en `~/.local/share/CorkyTux/plugins/heroic-store/`
   (`heroic-store` + `plugin.json`, con permiso de ejecución).
2. Reinicia el launcher (`pkill -x corkytux`) y abre la página **Tienda**.

## Primer paso: `setup` (obligatorio una vez)

El plugin descarga sus propios `legendary` / `gogdl` en:

```text
~/.local/share/CorkyTux/plugins/heroic-store/bin/
```

- Desde la UI se ejecuta solo la primera vez.
- Manual:
  ```bash
  ./heroic-store setup
  ./heroic-store status   # verifica binarios + sesión
  ```

## Iniciar sesión

### Epic Games (login embebido)

1. En la pestaña **Epic** pulsa iniciar sesión.
2. Se abre una ventana WebKit embebida con la web de Epic.
3. Inicia sesión normal (usuario/contraseña/2FA de Epic).
4. El plugin **autocaptura** el código de autorización solo, sin que copies nada.
5. Verás tu avatar + nombre en la cabecera. Para salir: logout.

Alternativa por terminal (si el embebido falla):

```bash
./heroic-store login-window --store epic
./heroic-store auth --store epic --code TU_CODIGO
```

### GOG (token propio)

1. En la pestaña **GOG** pulsa iniciar sesión.
2. Se abre la web de GOG para autorizar; el plugin captura el token propio.
3. Verás tu perfil en la cabecera. Para salir: logout.

```bash
./heroic-store login-window --store gog
./heroic-store auth --store gog --code TU_CODIGO
./heroic-store logout    # cierra la sesión actual
```

## Biblioteca, promos y ofertas

| Acción | Dónde | Comando |
|--------|-------|---------|
| Ver biblioteca | Tabs Epic/GOG (portadas + ficha View con cover+desc) | `./heroic-store library --store epic` / `--store gog` (`--refresh` para forzar) |
| Juegos gratis | Sección Free games (solo 100% vigentes) | `./heroic-store free-promos` |
| Ofertas Epic | Sección Deals (%, precio y fin verificados) | `./heroic-store epic-deals` |
| Buscar/comprar GOG | Buscador + Buy con precios | `./heroic-store gog-store-search --query "hollow knight"` |
| Buscar Epic | Botón que abre el navegador (Epic no tiene search API pública) | — |
| Detalle GOG | Ficha del juego | `./heroic-store game-info --store gog --app-id ID` (la descripción solo llega vía gameDetails) |

## Instalar y jugar

1. En la ficha pulsa **Instalar** (o `install --store epic --app-id ID [--path DIR]`).
   Por defecto van a `~/Games/Heroic` y aparecen en la **biblioteca nativa**
   con el Proton/prefix del launcher.
2. Para lanzar Epic se usa `legendary launch` con game token, epicapp y sandbox
   (compatible EAC/EOS). Ejemplo Fall Guys verificado.
3. Ver datos de lanzamiento: `./heroic-store launch-info --store epic --app-id ID`
4. Desinstalar: `./heroic-store uninstall --store epic --app-id ID`
5. Importar lo ya instalado (Heroic u otra ruta):
   `./heroic-store heroic-scan` (usa sesión propia + Heroic, solo `~/Games/Heroic`)

## EOS / EAC / umu

- Código EOS: `./heroic-store eos-code`
- Estado umu: `./heroic-store umu-status` · instalar umu 1.4.4 en `tools/umu`:
  `./heroic-store umu-setup`
- EAC/BattlEye y EOS se configuran por juego en CorkyTux (ajustes del juego).

## Problemas comunes

- **Login Epic no captura**: reintenta `login-window`; completa el 2FA en la ventana.
- **GOG sin descripción**: normal, solo llega vía gameDetails del juego concreto.
- **Juego Epic no arranca**: revisa `launch-info`, prueba otro Proton, revisa EAC/EOS.
- **Pendiente de probar**: login GOG embebido, instalar Epic desde Stores,
  EAC en prefix fresco, Deals/Claim con ofertas nuevas — reporta en
  [Issues](https://github.com/Matts-lab69/CorkyTux-Plugins/issues).
