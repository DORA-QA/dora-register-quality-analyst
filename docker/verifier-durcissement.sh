#!/usr/bin/env bash
# Checks the hardened Docker stack on the machine of the user (review S5 and S7).
#
#   ./docker/verifier-durcissement.sh            # build, start, check, leave the stack running
#   ./docker/verifier-durcissement.sh --down     # same, then stop the stack
#   ./docker/verifier-durcissement.sh --big FILE # also import a large package (memory limit)
#
# Needs: Docker Desktop (docker compose v2) and curl. Works with the bash 3.2 of macOS.
# Uses only the fictitious files of sample-data/. Prints OK / KO per check and a summary.

set -u
cd "$(dirname "$0")/.." || exit 1

DOWN=0
BIG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --down) DOWN=1 ;;
    --big) shift; BIG="${1:-}" ;;
    *) echo "unknown option: $1"; exit 2 ;;
  esac
  shift
done

GOLDEN="sample-data/529900P784EKW7VFMQ21.CON_FR_DORA010100_DORA_2026-12-31_20261029182948489.zip"
MULTI="sample-data/package-multi-defects.sample.zip"
API="http://localhost:8000"
WEB="http://localhost:3000"
PASSED=0
FAILED=0

ok() { PASSED=$((PASSED + 1)); printf '  OK  %s\n' "$1"; }
ko() { FAILED=$((FAILED + 1)); printf '  KO  %s\n' "$1"; [ -n "${2:-}" ] && printf '      %s\n' "$2"; }
check() { # check "label" command...
  local label="$1"; shift
  if "$@" >/dev/null 2>&1; then ok "$label"; else ko "$label"; fi
}
contains() { printf '%s' "$1" | grep -q -- "$2"; }

echo "== 1. Construction et démarrage"
docker compose build || { echo "build impossible"; exit 1; }
docker compose up -d --wait || { echo "démarrage impossible"; docker compose ps; docker compose logs --tail 50; exit 1; }
docker compose ps

BACKEND=$(docker compose ps -q backend)
FRONTEND=$(docker compose ps -q frontend)

echo
echo "== 2. Durcissement des conteneurs (S7)"
for name in backend frontend; do
  id=$(docker compose ps -q "$name")
  [ "$(docker inspect -f '{{.HostConfig.ReadonlyRootfs}}' "$id")" = "true" ] \
    && ok "$name : système de fichiers en lecture seule" || ko "$name : système de fichiers en lecture seule"
  contains "$(docker inspect -f '{{.HostConfig.CapDrop}}' "$id")" "ALL" \
    && ok "$name : aucune capacité Linux (cap_drop ALL)" || ko "$name : cap_drop ALL"
  contains "$(docker inspect -f '{{.HostConfig.SecurityOpt}}' "$id")" "no-new-privileges" \
    && ok "$name : no-new-privileges" || ko "$name : no-new-privileges"
  [ "$(docker inspect -f '{{.HostConfig.Memory}}' "$id")" != "0" ] \
    && ok "$name : limite de mémoire" || ko "$name : limite de mémoire"
  uid=$(docker exec "$id" id -u 2>/dev/null)
  [ -n "$uid" ] && [ "$uid" != "0" ] && ok "$name : utilisateur non root (uid $uid)" || ko "$name : utilisateur non root" "uid=$uid"
done
if docker exec "$BACKEND" sh -c 'touch /app/essai' >/dev/null 2>&1; then
  ko "backend : écriture refusée hors de /tmp"
else
  ok "backend : écriture refusée hors de /tmp"
fi
check "backend : écriture permise dans /tmp (mémoire)" docker exec "$BACKEND" sh -c 'touch /tmp/essai && rm /tmp/essai'
if docker exec "$BACKEND" sh -c 'test -d /app/tests || test -d /app/tools'; then
  ko "backend : tests et outils absents de l'image"
else
  ok "backend : tests et outils absents de l'image"
fi

echo
echo "== 3. Hôtes autorisés (S5)"
check "API : /health sur localhost" curl -fsS "$API/health"
check "API : /health sur 127.0.0.1" curl -fsS "http://127.0.0.1:8000/health"
check "page : http://localhost:3000" curl -fsS "$WEB/"
code=$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: attacker.example' "http://127.0.0.1:8000/health")
[ "$code" = "000" ] && ok "API : autre nom d'hôte sans réponse (444)" || ko "API : autre nom d'hôte sans réponse" "code HTTP $code"
code=$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: attacker.example' "http://127.0.0.1:3000/")
[ "$code" = "000" ] && ok "page : autre nom d'hôte sans réponse (444)" || ko "page : autre nom d'hôte sans réponse" "code HTTP $code"
contains "$(curl -sI "$WEB/")" "Content-Security-Policy" \
  && ok "page : en-tête Content-Security-Policy" || ko "page : en-tête Content-Security-Policy"

echo
echo "== 4. Fonctionnement"
version=$(curl -fsS "$API/health")
echo "  version : $version"
body=$(curl -fsS -H "X-ROI-Client: verifier" -F "file=@$GOLDEN" "$API/api/import?lang=fr")
contains "$body" '"status":"SUCCESS_WITH_WARNINGS"' \
  && ok "golden : SUCCESS_WITH_WARNINGS" || ko "golden : SUCCESS_WITH_WARNINGS" "$(printf '%s' "$body" | cut -c1-200)"
contains "$body" '"concentration":{' && ok "golden : indicateurs de concentration" || ko "golden : indicateurs de concentration"
body=$(curl -fsS -H "X-ROI-Client: verifier" -F "file=@$MULTI" "$API/api/import?lang=en")
contains "$body" '"status":"FAILED"' && contains "$body" '"code":"REL-012"' && contains "$body" '"code":"DAT-033"' \
  && ok "multidéfauts : FAILED avec REL-012 et DAT-033" || ko "multidéfauts : FAILED avec REL-012 et DAT-033"
if [ -n "$BIG" ]; then
  start=$(date +%s)
  body=$(curl -sS -H "X-ROI-Client: verifier" -F "file=@$BIG" "$API/api/import")
  seconds=$(( $(date +%s) - start ))
  contains "$body" '"status"' && ok "gros package : analysé en ${seconds} s" || ko "gros package" "$(printf '%s' "$body" | cut -c1-200)"
fi

echo
echo "== 5. Journaux"
logs=$(docker compose logs backend 2>&1)
contains "$logs" "Traceback" && ko "journaux : aucune trace d'exception" || ok "journaux : aucune trace d'exception"
contains "$logs" "PSEUDO FOURNISSEUR" && ko "journaux : aucune valeur du registre" || ok "journaux : aucune valeur du registre"

echo
echo "== 6. Ressources"
docker stats --no-stream --format '  {{.Name}} : mémoire {{.MemUsage}}, processus {{.PIDs}}' "$BACKEND" "$FRONTEND"

echo
echo "== 7. Empreintes des images de base (pour les épingler)"
# BuildKit (Docker Desktop) does not keep the base images in the local store: ask the registry.
for image in python:3.13-slim node:22-slim nginxinc/nginx-unprivileged:stable-alpine; do
  digest=$(docker buildx imagetools inspect "$image" 2>/dev/null | awk '/^Digest:/ {print $2; exit}')
  echo "  $image@${digest:-inconnue}"
done

echo
echo "== Résultat : $PASSED OK, $FAILED KO"
[ "$DOWN" = "1" ] && docker compose down
[ "$FAILED" = "0" ]
