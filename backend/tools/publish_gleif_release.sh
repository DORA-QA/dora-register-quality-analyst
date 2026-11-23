#!/usr/bin/env bash
# Publishes a GLEIF copy built by tools/build_gleif.py as a release of the repository
# (branch feature/gleif-local). The gleif-updater container installs the latest release whose tag
# starts with "gleif-".
#
#   backend/tools/publish_gleif_release.sh <folder with manifest.json, lei.parquet, rr.parquet>
#
# Needs the GitHub CLI (gh), logged in with the right to create releases.
set -euo pipefail

folder="${1:?usage: publish_gleif_release.sh <folder>}"
repo="${ROI_GLEIF_REPO:-stephanealpha/roi-quality-engine}"
for file in manifest.json lei.parquet rr.parquet; do
  [[ -f "$folder/$file" ]] || { echo "missing: $folder/$file" >&2; exit 1; }
done

published="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["content_date"])' "$folder/manifest.json")"
# 2026-11-08T09:00:01Z -> gleif-20261108-0900
tag="gleif-$(echo "$published" | sed -E 's/^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}).*/\1\2\3-\4\5/')"

gh release create "$tag" \
  --repo "$repo" \
  --target "${ROI_GLEIF_TARGET:-main}" \
  --title "Copie GLEIF du ${published%%T*}" \
  --notes "Copie GLEIF (LEI et relations) publiée par le GLEIF le $published, mise en forme par backend/tools/build_gleif.py. Installée automatiquement au démarrage par le conteneur gleif-updater." \
  "$folder/manifest.json" "$folder/lei.parquet" "$folder/rr.parquet"
echo "published $tag"
