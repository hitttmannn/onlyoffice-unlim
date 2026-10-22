#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
mkdir -p artifacts
image=$(python3 - <<'READ'
import json
from pathlib import Path
lock=json.loads(Path('runtime-candidate.json').read_text())
print(lock['image'])
READ
)
[[ "$image" =~ ^onlyoffice/documentserver@sha256:[a-f0-9]{64}$ ]] || { echo 'Invalid image digest'; exit 1; }
python3 - <<'SPACE'
import shutil
if shutil.disk_usage('.').free < 12*1024**3:
    raise SystemExit('STOP: less than 12 GiB free in project filesystem')
SPACE
# Downloads an image. Does not start its entrypoint or mount production data.
echo "Pulling pinned candidate: $image"
docker pull --platform linux/amd64 "$image"
docker image inspect "$image" --format '{{.Id}} {{.Os}}/{{.Architecture}} {{.Size}}' | tee artifacts/runtime-image.txt
docker run --rm -i --platform linux/amd64 --network none --read-only   --cap-drop ALL --security-opt no-new-privileges   --memory 256m --memory-swap 256m --pids-limit 64   --entrypoint /bin/sh "$image" -s <<'INSPECT' | tee artifacts/runtime-audit.txt
set -eu
printf '\n== Installed Docs package ==\n'
dpkg-query -W -f='${binary:Package} ${Version}\n' 'onlyoffice-documentserver*'
printf '\n== Exposed source files (if packaged) ==\n'
for root in /var/www/onlyoffice/documentserver/server /usr/share/onlyoffice/documentserver/server; do
  if [ -d "$root" ]; then
    find "$root" -type f \( -name license.js -o -name constants.js \) -print
    for file in "$root/Common/sources/constants.js" "$root/Common/sources/license.js"; do
      if [ -f "$file" ]; then
        grep -nE 'LICENSE_CONNECTIONS|connections:|connectionsView:' "$file" || true
      fi
    done
  fi
done
printf '\n== Mobile entrypoints (existence only) ==\n'
for app in documenteditor spreadsheeteditor presentationeditor; do
  path="/var/www/onlyoffice/documentserver/web-apps/apps/$app/mobile/index.html"
  if [ -f "$path" ]; then echo "$app: present"; else echo "$app: absent at expected path"; fi
done
printf '\n== Package license locations ==\n'
find /usr/share/doc -maxdepth 2 -type f \( -name copyright -o -name LICENSE \) -path '*onlyoffice*' -print
INSPECT
if ! grep -Eq '^onlyoffice-documentserver(:amd64)? 10[.]' artifacts/runtime-audit.txt; then
  echo 'STOP: expected Community package version 10.x not confirmed.' >&2
  exit 1
fi
echo 'PASS: pinned image inspected and package major version confirmed.'
echo 'No Docs services started. Editing, limits, licenses and source correspondence remain unverified.'
