#!/bin/bash
# Called by CloudFormation UserData, as root, after its parameters are set.
set -euo pipefail
umask 077
exec > >(tee -a /var/log/urbansaarthi-bootstrap.log) 2>&1

retry() {
  local attempt
  for attempt in 1 2 3 4 5 6; do
    if "$@"; then return 0; fi
    sleep 10
  done
  return 1
}

# The Elastic IP association can finish a few seconds after cloud-init starts.
retry dnf install -y docker git openssl
systemctl enable --now docker
systemctl enable --now amazon-ssm-agent

# Keep a small build from exhausting a 1 GiB t3.micro; swap is on encrypted EBS.
if [[ ! -f /swapfile ]]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile swap swap defaults 0 0' >> /etc/fstab
fi

install -d -m 700 /etc/urbansaarthi
install -d -m 750 -o 10001 -g 10001 /var/lib/urbansaarthi
if [[ ! -f /etc/urbansaarthi/runtime.env ]]; then
  officer_key=$(openssl rand -hex 32)
  {
    printf 'NAGARSEVA_OFFICER_KEY=%s\n' "$officer_key"
    printf 'URBANSAARTHI_ORIGIN_SECRET=%s\n' "$URBAN_ORIGIN_SECRET"
    printf 'NAGARSEVA_MODE=hosted-demo\n'
  } > /etc/urbansaarthi/runtime.env
  chmod 600 /etc/urbansaarthi/runtime.env
  unset officer_key
fi

install -d -m 755 /opt/urbansaarthi
cd /opt/urbansaarthi
if [[ ! -d source/.git ]]; then
  retry git clone --no-checkout https://github.com/vishal88736/nagarseva-seva-first.git source
fi
cd source
git checkout --detach "$URBAN_SOURCE_REVISION"
docker build --file deploy/aws/Dockerfile --tag urbansaarthi:"$URBAN_SOURCE_REVISION" .

# This bootstrap is for initial installation, not an unattended update service.
docker run --detach --name urbansaarthi --restart unless-stopped \
  --publish 80:8080 --env-file /etc/urbansaarthi/runtime.env \
  --mount type=bind,source=/var/lib/urbansaarthi,target=/data \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=32m \
  --cap-drop ALL --security-opt no-new-privileges \
  --log-driver json-file --log-opt max-size=10m --log-opt max-file=3 \
  urbansaarthi:"$URBAN_SOURCE_REVISION"
echo 'Container started. Inspect Docker health and the public HTTPS endpoint before treating deployment as ready.'
