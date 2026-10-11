#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Download the complete theme; preserve sources for inspection and restoration.
set -Eeuo pipefail
if (( EUID == 0 )); then
    echo 'Запускайте команду обычным пользователем в KDE, без sudo.' >&2
    exit 1
fi
for tool in curl tar python3; do
    if ! command -v "$tool" >/dev/null; then
        echo "Нужна команда $tool. Установите её средствами дистрибутива." >&2
        exit 1
    fi
done
RODIP_GLASS_CACHE="${XDG_DATA_HOME:-$HOME/.local/share}/rodip-glass"
mkdir -p -- "$RODIP_GLASS_CACHE"
RODIP_GLASS_DOWNLOAD=$(mktemp -d "$RODIP_GLASS_CACHE/source.XXXXXXXX")
trap 'rm -rf -- "$RODIP_GLASS_DOWNLOAD"' EXIT
curl -fsSL --retry 3 https://github.com/Swart-G/my-theme/archive/refs/heads/main.tar.gz -o "$RODIP_GLASS_DOWNLOAD/source.tar.gz"
tar -xzf "$RODIP_GLASS_DOWNLOAD/source.tar.gz" --strip-components=1 -C "$RODIP_GLASS_DOWNLOAD"
rm -- "$RODIP_GLASS_DOWNLOAD/source.tar.gz"
test -f "$RODIP_GLASS_DOWNLOAD/install.sh"
test -f "$RODIP_GLASS_DOWNLOAD/scripts/install.py"
trap - EXIT
echo "Исходники темы: $RODIP_GLASS_DOWNLOAD"
exec bash "$RODIP_GLASS_DOWNLOAD/install.sh" "$@"
