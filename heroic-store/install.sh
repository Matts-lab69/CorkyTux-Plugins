#!/usr/bin/env bash
# Sync the canonical heroic-store plugin from this repo to the runtime
# locations the launcher and the plugin use.
#
# The repo copy (this directory) is the SINGLE source of truth. Never edit
# the runtime copies by hand: edit here and run this script.
#
# Destinations:
#   ~/.local/share/CorkyTux/plugins/heroic-store/
#       The executable the launcher spawns (see
#       src/backend/plugin_process.rs::plugin_exe).
#   ~/.config/CorkyTux/plugins/heroic-store/
#       The plugin's CONFIG_DIR: runtime state (descriptions.json,
#       installs.json, gog_token.json, bin/legendary, bin/gogdl,
#       .status_cache.json, .steam_throttle). Only the script and its
#       metadata are overwritten here; state is never touched.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENTRY="heroic-store"

dest_data="$HOME/.local/share/CorkyTux/plugins/$ENTRY"
dest_config="$HOME/.config/CorkyTux/plugins/$ENTRY"

for dest in "$dest_data" "$dest_config"; do
    mkdir -p "$dest"
    install -m 0755 "$REPO_DIR/$ENTRY" "$dest/$ENTRY"
    for meta in plugin.json README.md; do
        [ -f "$REPO_DIR/$meta" ] && install -m 0644 "$REPO_DIR/$meta" "$dest/$meta"
    done
    echo "synced $ENTRY -> $dest"
done

# Fail loudly if the copies ever diverge.
md5sum "$REPO_DIR/$ENTRY" "$dest_data/$ENTRY" "$dest_config/$ENTRY"
