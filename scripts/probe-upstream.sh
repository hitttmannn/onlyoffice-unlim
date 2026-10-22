#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p artifacts
# Only registry metadata: no image pull, container start or production changes.
image=onlyoffice/documentserver:10.0
if ! docker manifest inspect "$image" > artifacts/upstream-manifest.json; then
  echo 'STOP: cannot inspect candidate tag; do not substitute latest or 9.x.' >&2
  exit 1
fi
python3 - <<'CHECK'
import json
from pathlib import Path
m=json.loads(Path('artifacts/upstream-manifest.json').read_text())
print('Candidate tag: onlyoffice/documentserver:10.0')
print('mediaType:',m.get('mediaType','unknown'))
if 'manifests' in m:
    for item in m['manifests']:
        p=item.get('platform',{})
        print(p.get('os'),p.get('architecture'),p.get('variant',''),item.get('digest'))
else:
    print('Single-image manifest; platform must be verified separately.')
print('Metadata only: package version, features, licenses and runtime are unverified.')
CHECK
