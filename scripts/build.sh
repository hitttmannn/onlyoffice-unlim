#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${BASE_IMAGE:?Export a verified digest-pinned 10.0 image}"
: "${SOURCE_URL:?Export approved repository URL}"
: "${CANDIDATE_IMAGE:?Export local candidate image name}"
[[ "$BASE_IMAGE" =~ ^onlyoffice/documentserver@sha256:[a-f0-9]{64}$ ]] || { echo 'Invalid base digest'; exit 1; }
mkdir -p artifacts
# No floating tags, package installs, feature patches, or production actions.
docker pull "$BASE_IMAGE"
docker build --network=none --build-arg BASE_IMAGE="$BASE_IMAGE" --build-arg SOURCE_URL="$SOURCE_URL" -t "$CANDIDATE_IMAGE" .
docker image inspect "$CANDIDATE_IMAGE" --format '{{.Id}}' > artifacts/candidate-image-id.txt
docker run --rm --network=none --memory=256m --memory-swap=256m --entrypoint dpkg-query "$CANDIDATE_IMAGE" -W 'onlyoffice-documentserver*' > artifacts/packages.txt
grep -Eq '[[:space:]]10\.' artifacts/packages.txt || { echo 'STOP: version 10 not confirmed'; exit 1; }
sha256sum Dockerfile compose.yaml > artifacts/recipe.sha256
