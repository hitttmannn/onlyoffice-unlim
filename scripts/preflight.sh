#!/usr/bin/env bash
set -euo pipefail
# Read only. Do not print inspect/config/env: those can contain secrets.
uname -m
free -m
df -h .
docker version --format '{{.Server.Version}}'
docker compose version
docker ps --format '{{.Names}} {{.Image}} {{.Status}}'
docker stats --no-stream --format '{{.Name}} {{.MemUsage}} {{.CPUPerc}}'
python3 - <<'CHECK'
from pathlib import Path
v={x.split(':')[0]:int(x.split()[1]) for x in Path('/proc/meminfo').read_text().splitlines() if ':' in x and len(x.split())>1 and x.split()[1].isdigit()}
if v['MemAvailable'] < 2300*1024: raise SystemExit('STOP: less than 2300 MiB available; do not start staging beside production')
if v['SwapTotal'] < 3800*1024: raise SystemExit('STOP: expected approximately 4 GiB swap')
CHECK
