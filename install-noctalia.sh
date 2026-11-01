#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -Eeuo pipefail
theme_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$theme_root/scripts/install-noctalia.py" "$@"
