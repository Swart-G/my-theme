#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -Eeuo pipefail
RODIP_GLASS_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if ! command -v python3 >/dev/null; then
    echo 'Нужен Python 3. Установите его средствами вашего дистрибутива.' >&2
    exit 1
fi
exec python3 "$RODIP_GLASS_ROOT/scripts/install.py" "$@"
