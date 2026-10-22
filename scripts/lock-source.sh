#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ ! -e upstream ]] || { echo 'upstream already exists; refusing overwrite'; exit 1; }
mkdir -p artifacts
git clone --filter=blob:none --no-checkout https://github.com/ONLYOFFICE/DocumentServer.git upstream
git -C upstream checkout --detach v10.0.0
git -C upstream submodule update --init --recursive --jobs 1
{ git -C upstream rev-parse HEAD; git -C upstream submodule status --recursive; } > artifacts/source-lock.txt
# Inspect the RELEASE gitlinks, not master branches.
rg -n 'LICENSE_CONNECTIONS|connectionsView|connections:' upstream/server/Common/sources/{constants,license}.js > artifacts/license-code.txt
rg -n 'mobile|isMobile|license|connections' upstream/web-apps/build > artifacts/mobile-build.txt || true
find upstream -type f \( -iname 'license*' -o -iname 'copying*' -o -iname 'notice*' \) -print > artifacts/license-paths.txt
printf '%s\n' 'Source fetched and gitlinks recorded. No compilation or feature claim made.'
