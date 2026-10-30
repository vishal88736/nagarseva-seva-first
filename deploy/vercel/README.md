# Manual deployment: Vercel frontend + AWS backend

> **Alternative configuration, not the current deployment.** UrbanSaarthi is
> currently hosted entirely on AWS through CloudFront and EC2. Use the
> [AWS operations guide](../aws/README.md) for the active setup. The Vercel project
> and domain mentioned below describe an earlier preparation session; the old
> `urbansaarthi.vercel.app` address returned 404 when checked on 31 October 2026.
> Do not assume that project still exists or configure CORS for it unnecessarily.
> Every reference to that frontend domain below is historical: replace it with
> the actual HTTPS origin you control before using this alternative configuration.

This alternative uses AWS CloudFront + EC2 + Docker + persistent SQLite for the
backend. During an earlier preparation session a Vercel project was created and
linked, but its frontend was not published then. The user subsequently deployed
the full application on AWS. If choosing split hosting in future, verify/link the
intended Vercel project and use its actual domain and environment settings.

## 1. Publish the current application source — your local terminal

AWS can obtain only published commits. Review local changes and publish any
intended application updates before deploying. Skip committing when already up to
date; inspect the actual Git status instead of assuming an uncommitted version.
The following paths exclude databases, local credential files and runtime artifacts:

```bash
cd "/home/vishal/D DRIVE/seva first/nagarseva-seva-first"
git status --short
git add .dockerignore .gitignore .vercelignore vercel.json README.md .env.example deploy/aws deploy/vercel nagarseva/model/api nagarseva/model/requirements-urban.txt nagarseva/website nagarseva/shared
git diff --cached --stat
```

Review `git diff --cached` privately. Ensure only intended source changes are staged
and no `.env.local`, private credentials or SQLite files are included. Then:

```bash
git commit -m "Prepare UrbanSaarthi for Vercel frontend and AWS backend"
git push origin main
```

These commands are for you to run; the assistant has not committed or pushed them.

## 2. Find your existing AWS stack — AWS console and CloudShell

Sign into your AWS account yourself. Confirm the remaining credit balance and expiry
in Billing. Credits are finite, not a promise of a permanently free service. Select
the region containing your existing stack (previously `us-east-1`). Open CloudShell:

```bash
aws cloudformation describe-stacks --region us-east-1 --stack-name urbansaarthi-demo --query 'Stacks[0].Outputs' --output table
```

Note `InstanceId` and `WebsiteUrl`. The HTTPS `WebsiteUrl` is the AWS backend origin.
The frontend API base will be that URL followed by `/api`.

**If the stack already exists, do not create another instance or delete the stack.**
Continue with step 3. If it genuinely does not exist in the selected region, use the
initial launcher after checking credits and the documented resources:

```bash
git clone https://github.com/vishal88736/nagarseva-seva-first.git urbansaarthi-aws
cd urbansaarthi-aws
URBANSAARTHI_AWS_REGION=us-east-1 bash deploy/aws/launch.sh
```

If that checkout already exists, update that clean checkout instead of cloning
again. The initial launcher can create EC2, EBS, a public IPv4 and CloudFront; it
is not an existing-instance code updater. Passing its old health check does not
prove the current civic API was deployed.

## 3. Build the current backend — existing EC2 Session Manager terminal

In the AWS console, open EC2 → select the stack's instance → Connect → Session
Manager → Connect. No SSH port needs opening. This section assumes the existing
repository deployment layout under `/opt/urbansaarthi` and `/etc/urbansaarthi`.
Stop if those paths or the named container are missing; do not fabricate new keys
or recreate storage to bypass the mismatch.

```bash
sudo -i
cd /opt/urbansaarthi/source
git status --short
```

If that remote checkout has local edits, stop and preserve/review them before
checkout. For a clean checkout:

```bash
git fetch origin main
git checkout --detach FETCH_HEAD
URBAN_REVISION=$(git rev-parse HEAD)
docker build --file deploy/aws/Dockerfile --tag "urbansaarthi:$URBAN_REVISION" .
```

Leave the old service running while the new image builds. This can take several
minutes on a micro instance. The existing Dockerfile keeps its non-root runtime
and the previous restrictive-checkout permission repair.

## 4. Back up the database and allow your frontend — same EC2 terminal

Create a consistent database backup using the existing image and bind mount. This
works even if the old container is stopped, provided its image and storage exist:

```bash
URBAN_OLD_IMAGE=$(docker inspect --format '{{.Image}}' urbansaarthi)
docker run --rm --entrypoint python --env-file /etc/urbansaarthi/runtime.env --mount type=bind,source=/var/lib/urbansaarthi,target=/data "$URBAN_OLD_IMAGE" -c "import os,sqlite3; from pathlib import Path; from datetime import datetime,timezone; p=Path(os.getenv('URBANSAARTHI_DB_PATH','/data/urbansaarthi.sqlite3')); assert p.is_file(),'Existing database not found; stop and inspect storage'; target='/data/backup-before-update-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.sqlite3'; src=sqlite3.connect(p); dst=sqlite3.connect(target); src.backup(dst); dst.close(); src.close(); print(target)"
cp -p /etc/urbansaarthi/runtime.env /etc/urbansaarthi/runtime.env.before-vercel
```

Keep wanted backups off-instance through a private transfer too; this on-volume
backup does not survive instance/volume deletion. Do not upload it to GitHub.

Add the exact Vercel production origin, preserving existing allowed origins and
all existing secret values. Do not print the private runtime file:

```bash
python3 - <<'PY'
from pathlib import Path
p=Path('/etc/urbansaarthi/runtime.env')
lines=p.read_text().splitlines()
prefix='NAGARSEVA_CORS_ORIGINS='
existing=next((line[len(prefix):] for line in lines if line.startswith(prefix)),'')
origins=[value.strip() for value in existing.split(',') if value.strip()]
origin='https://urbansaarthi.vercel.app'
if origin not in origins: origins.append(origin)
lines=[line for line in lines if not line.startswith(prefix)]
lines.append(prefix+','.join(origins))
p.write_text('\n'.join(lines)+'\n')
p.chmod(0o600)
print('Frontend origin added; existing credentials preserved.')
PY
```

If you use another frontend/custom domain later, add its exact HTTPS origin too.
Do not put the backend officer/origin keys into Vercel build variables.

## 5. Start the new container — same EC2 terminal

The earlier environment and `/var/lib/urbansaarthi` database are reused. Keep the
stopped old container as a rollback option:

```bash
URBAN_PREVIOUS_CONTAINER="urbansaarthi-before-$(date -u +%Y%m%dT%H%M%SZ)"
docker stop urbansaarthi
docker rename urbansaarthi "$URBAN_PREVIOUS_CONTAINER"
docker run --detach --name urbansaarthi --restart unless-stopped --publish 80:8080 --env-file /etc/urbansaarthi/runtime.env --mount type=bind,source=/var/lib/urbansaarthi,target=/data --read-only --tmpfs /tmp:rw,noexec,nosuid,size=32m --cap-drop ALL --security-opt no-new-privileges --log-driver json-file --log-opt max-size=10m --log-opt max-file=3 "urbansaarthi:$URBAN_REVISION"
docker logs --tail 50 urbansaarthi
docker inspect --format '{{.State.Health.Status}}' urbansaarthi
```

Wait for Healthy. Check actual logs if startup fails. Do not disclose runtime.env,
keys or private database contents. If the new container fails and you need to restore
the old image in this same shell:

```bash
docker stop urbansaarthi
docker rename urbansaarthi "urbansaarthi-failed-$(date -u +%Y%m%dT%H%M%SZ)"
cp -p /etc/urbansaarthi/runtime.env.before-vercel /etc/urbansaarthi/runtime.env
docker rename "$URBAN_PREVIOUS_CONTAINER" urbansaarthi
docker start urbansaarthi
```

This restores the prior container/environment without deleting the database.
Database backups are retained for separately reviewed recovery if ever needed.

## 6. Forward CORS headers — CloudFront console

Vercel and AWS are different browser origins. In CloudFront → Policies → Origin
request, find the custom policy attached to this distribution, normally
`urbansaarthi-demo-api`. Edit its included-header list to contain:

- `Content-Type`
- `X-Officer-Key`
- `Idempotency-Key`
- `Origin`
- `Access-Control-Request-Method`
- `Access-Control-Request-Headers`

Keep the existing private `X-Origin-Verify` origin header and network restrictions
unchanged. Keep caching disabled. Confirm the behavior allows OPTIONS and POST/PATCH.
Wait for CloudFront to finish deploying the policy change. The template now includes
these headers for new stacks; changing the local template does not automatically
update an existing distribution.

## 7. Verify AWS — browser or your own terminal

Take the actual `WebsiteUrl` from CloudFormation. Open its path:

```text
/api/urban/demo/health
```

It must return JSON with `adapter: sqlite-synthetic`, `synthetic: true` and
`externalConnected: false`. A 403, 404, HTML page or error is not success. Test a
preflight with the real URL substituted below:

```bash
curl -i -X OPTIONS 'YOUR_ACTUAL_HTTPS_WEBSITE_URL/api/urban/demo/commands' -H 'Origin: https://urbansaarthi.vercel.app' -H 'Access-Control-Request-Method: POST' -H 'Access-Control-Request-Headers: content-type,x-officer-key'
```

Expect HTTP 200 and `access-control-allow-origin: https://urbansaarthi.vercel.app`.
The URL above is a replacement instruction, not a configured example endpoint.

## 8. Deploy Vercel — your Vercel dashboard

Open the linked `urbansaarthi` project. Root directory is the repository root (`.`),
Framework is Other; the root `vercel.json` supplies install/build/output settings.
Node 24.x has been selected to match the tested local environment.

Set **VITE_API_BASE_URL** for Production (and Preview only if its origin is explicitly
allowed by the backend) to the actual AWS `WebsiteUrl` followed by `/api`. Do not
append `/urban`. This URL is public; it must not contain a secret.

Use the current source: import/connect the updated GitHub repository for deployment,
or use the local authenticated Vercel CLI from the repository root. The app is not
auto-connected to the old GitHub commit just because the Vercel project exists.

```bash
cd "/home/vishal/D DRIVE/seva first/nagarseva-seva-first"
npm exec --yes --package vercel@65.8.0 -- vercel --prod
```

The configured build checks the real AWS API before compiling. It fails if the URL
is missing or the API does not return the expected health contract. Missing API
paths/assets are not rewritten to a false HTTP-200 HTML page. Local development
continues using `bash start-local.sh` and the original local SQLite store.

After deployment, check the public site: explore/select polygons, switch languages,
submit a clearly labelled Demo data issue, reload, verify the saved report, inspect
projects/visits and export a report. Verify restart persistence before calling the
whole deployment ready. Imported datasets and local records are not automatically
transferred to AWS. No official data connection is claimed.

## Documentation checked 30 October 2026

- [Vercel and local SQLite](https://vercel.com/kb/guide/is-sqlite-supported-in-vercel)
- [Vercel build settings](https://vercel.com/docs/builds/configure-a-build)
- [CloudFront CORS forwarding](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/header-caching.html)
- [Existing AWS architecture, credits and backup limits](../aws/README.md)
