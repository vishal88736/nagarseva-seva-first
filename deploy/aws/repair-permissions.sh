#!/bin/bash
# Run as root on the existing demo instance. No source/app rebuild or DB reset.
set -euo pipefail
umask 077
[[ $(id -u) == 0 ]] || { echo 'Run this repair with sudo on the EC2 instance.' >&2; exit 1; }
urban_container=urbansaarthi
urban_env=/etc/urbansaarthi/runtime.env
urban_data=/var/lib/urbansaarthi
[[ -r "$urban_env" && -d "$urban_data" ]] || { echo 'Existing runtime configuration or data directory missing; refusing to recreate it.' >&2; exit 1; }
urban_mount=$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Source}}{{end}}{{end}}' "$urban_container")
[[ "$urban_mount" == "$urban_data" ]] || { echo 'Unexpected data mount; inspect the container before repairing it.' >&2; exit 1; }
urban_image=$(docker inspect --format '{{.Image}}' "$urban_container")
[[ "$urban_image" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo 'Could not determine the existing immutable image.' >&2; exit 1; }
urban_short=${urban_image:7:12}
urban_base="urbansaarthi:permission-base-$urban_short"
urban_fixed="urbansaarthi:permissions-fixed-$urban_short"
urban_backup="urbansaarthi-before-permissions-$(date -u +%Y%m%dT%H%M%SZ)"
urban_tmp=$(mktemp -d)
trap 'rm -rf -- "$urban_tmp"' EXIT

echo 'Building a permission-only layer from the already installed image. No npm or pip reinstall.'
docker image tag "$urban_image" "$urban_base"
printf '%s\n' "FROM $urban_base" 'USER 0:0' 'RUN chmod -R a+rX /app' 'USER 10001:10001' > "$urban_tmp/Dockerfile"
docker build --file "$urban_tmp/Dockerfile" --tag "$urban_fixed" "$urban_tmp"

# Check the image as the runtime UID before changing containers. Import's
# SQLite store uses temporary memory, not the saved records, for this probe.
docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=32m \
  --cap-drop ALL --security-opt no-new-privileges \
  --env URBANSAARTHI_DB_PATH=/tmp/permission-check.sqlite3 \
  --entrypoint python "$urban_fixed" -c \
  'import os; from pathlib import Path; import hosted; assert os.getuid()==10001; [(p.open("rb").read(1)) for p in Path("/app").rglob("*") if p.is_file()]; print("Repaired image imports and application files are readable as UID 10001.")'

echo 'Keeping the previous container and reusing the existing private env file and data mount.'
docker stop --time 15 "$urban_container" >/dev/null
docker rename "$urban_container" "$urban_backup"
docker run --detach --name "$urban_container" --restart unless-stopped \
  --publish 80:8080 --env-file "$urban_env" \
  --mount "type=bind,source=$urban_data,target=/data" \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=32m \
  --cap-drop ALL --security-opt no-new-privileges \
  --log-driver json-file --log-opt max-size=10m --log-opt max-file=3 \
  "$urban_fixed" >/dev/null

for urban_attempt in $(seq 1 60); do
  if docker exec "$urban_container" python -c '
import json,os,urllib.error,urllib.request
base="http://127.0.0.1:8080"
headers={"X-Origin-Verify":os.environ["URBANSAARTHI_ORIGIN_SECRET"]}
def get(path):
    return urllib.request.urlopen(urllib.request.Request(base+path,headers=headers),timeout=4)
with get("/api/urban/health") as response:
    health=json.load(response)
assert health.get("status")=="ok" and health.get("officer_auth_required") is True
with get("/") as response:
    assert b"<html" in response.read().lower()
try:
    get("/api/urban/state")
except urllib.error.HTTPError as exc:
    assert exc.code==401
else:
    raise AssertionError("Operational state must require officer access")
' >/dev/null 2>&1; then
    printf 'Local app health, frontend and officer protection passed. Saved data and keys were reused.\nPrevious container retained as: %s\n' "$urban_backup"
    echo 'Return to CloudShell and rerun the existing launcher to verify the public HTTPS endpoint.'
    exit 0
  fi
  sleep 2
done
echo 'Replacement container did not pass local checks. Previous container and data remain available.' >&2
docker logs --tail 60 "$urban_container" >&2
exit 1
