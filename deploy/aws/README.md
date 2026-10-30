# AWS deployment and operations

This hosts the complete UrbanSaarthi React application and FastAPI API together in
Docker on EC2, with SQLite on the instance's encrypted 20 GiB gp3 root EBS volume.
CloudFront supplies the public HTTPS address. The default instance type is
`t3.micro`. No RDS, NAT Gateway, load balancer, Kubernetes or model training is
provisioned. The active workspace contains **Demo data**; controlled file imports
remain isolated and no government service is connected.

**Current deployment:** <https://d2nrwxy6sjb9o8.cloudfront.net/>. Website, housing
route, synthetic API health, workspace validation and integration-readiness HTTP
checks passed on **31 October 2026 (Asia/Kolkata)**. These were read-only checks;
they did not restart the public server or create/delete its records. Photo storage
was disabled and all seven real-data categories reported `not_provided`.

The current deployment is **AWS only**. Vercel setup and cross-domain CORS changes
are not required. Website assets and `/api` use the same CloudFront origin. This
guide describes the checked-in deployment layout; confirm the account, region,
stack and instance before operating on resources.

## Resource and path reference

| Item | Default or location |
| --- | --- |
| Stack | `urbansaarthi-demo` |
| Region | Launcher default `ap-south-1`; examples below explicitly select `us-east-1`. Use the region containing your stack. |
| Public entry | CloudFront HTTPS; direct origin requests are rejected. |
| Source checkout | `/opt/urbansaarthi/source` |
| Container | `urbansaarthi` |
| Image | `urbansaarthi:<40-character-source-commit>` |
| Private environment | `/etc/urbansaarthi/runtime.env`, root-only |
| Persistent bind mount | `/var/lib/urbansaarthi` on host → `/data` in container |
| Default database | `/data/urbansaarthi.sqlite3` in container |
| Bootstrap log | `/var/log/urbansaarthi-bootstrap.log` |
| Maintenance | EC2 Session Manager; no SSH port is opened. |

The deployed region cannot be inferred from a CloudFront domain. The source
revision selected at initial launch stays running until an explicit code update.

## Cost boundary before launching

The account owner reported AWS credits. Their current amount, expiry, service
coverage and account plan have not been independently verified. Check the AWS
Billing console before creating resources; console labels can vary by account.

- EC2 compute, EBS storage and **one public IPv4/Elastic IP** can consume credits and incur charges when credits are insufficient or inapplicable. An Elastic IP is not assumed free just because it is attached. CPU credit mode is `standard`, avoiding T3 Unlimited surplus-credit charges; exhausted CPU credits can throttle the demo.
- This template creates **pay-as-you-go CloudFront**, using the applicable monthly free allowances/credits. It does **not** enroll the account in the separate flat-rate CloudFront Free plan and does not promise no overages. The latter has different eligibility and cannot be assumed available to a Free account.
- AWS's current Free plan and a Paid account with promotional credits have different exhaustion behavior. Do not upgrade the account or enable a paid feature just to bypass a provisioning restriction.
- Set a small **AWS Budgets** notification in the console and inspect gross service usage as well as credit balance. A normal budget alert is **not a hard spending cap**. The script does not create an email subscription, a budget or a guaranteed ₹0 enforcement policy. It attempts an informational Free Tier plan/credit API check and stops if that API reports zero credits or expiry; a failed/unavailable check is reported, not silently treated as proof of coverage.
- Stopping EC2 stops its compute consumption, but EBS and the Elastic IP remain chargeable. Remove the stack after backing up any wanted records when the demo is finished. No automatic expiry/deletion job is installed.

Do not treat generic “Free tier eligible” labels as confirmation that every resource or all traffic is free. No monthly price or credit lifetime is fabricated here.

## Launch in AWS CloudShell

Sign in to your own AWS account. Open [AWS CloudShell](https://console.aws.amazon.com/cloudshell/home?region=us-east-1). The signed-in principal needs permission to create/read the resources in the generated CloudFormation template, create/pass the EC2 instance role, and start a Session Manager session. **Do not create access keys, give the application an AdministratorAccess role, or paste AWS credentials into chat.** The instance receives only AWS's Session Manager core managed policy.

In a fresh CloudShell directory:

```bash
git clone https://github.com/vishal88736/nagarseva-seva-first.git urbansaarthi-aws
cd urbansaarthi-aws
URBANSAARTHI_AWS_REGION=us-east-1 bash deploy/aws/launch.sh
```

The script deploys the exact checkout commit from the public repository. Commit/push changed deployment or app files before use. If the directory already exists, use that checkout after inspecting/pulling its updates instead of repeating the clone into it. The default stack name is `urbansaarthi-demo`. An existing successful/in-progress stack is resumed; failed stacks are not automatically destroyed or replaced. Changing the source checkout does not update an existing instance: this is an initial-deployment script, not a CI release manager.

Allow several minutes for CloudFront and the first Docker build; a throttled micro instance can take longer. The script waits for the HTTPS API health, frontend HTML and an unauthenticated `401` on operational state. **Infrastructure `CREATE_COMPLETE` alone does not establish application readiness.** Only after those checks pass does it print `Verified website: https://…cloudfront.net`.

If your account's allowed region differs, set `URBANSAARTHI_AWS_REGION` to that enabled commercial AWS region before launching. No region is enabled automatically. `URBANSAARTHI_AWS_INSTANCE_TYPE=t3.small` is an optional more expensive 2 GiB instance; default is `t3.micro` with 2 GiB encrypted-volume swap for the build. Do not enlarge it without checking credit consumption. The script does not turn on account advanced features or upgrade its plan.

## Verify the public application

Read the actual outputs in CloudShell; substitute your region/stack when different:

```bash
aws cloudformation describe-stacks --region us-east-1 \
  --stack-name urbansaarthi-demo --query 'Stacks[0].Outputs' --output table
```

Open the reported `WebsiteUrl` and its `/api/urban/demo/health` path. Expect JSON
including `adapter: sqlite-synthetic`, `synthetic: true` and
`externalConnected: false`. HTML, a 403/404, or merely `CREATE_COMPLETE` is not an
application health result. Use your own output rather than assuming the current
demonstration address belongs to a newly created stack.

After deployment, exercise map/list selection, languages, issue submission,
refresh persistence, projects, housing, visits and a report export. A deliberately
labelled test issue and an approved server restart are needed to verify writes and
restart persistence on that deployment. Keep this separate from local/CI fixtures.

## Demonstration administrator access

The officer key is randomly generated **on EC2** and kept in `/etc/urbansaarthi/runtime.env`, readable by root. It is not a frontend build variable or GitHub secret. CloudFormation's separate origin token is a `NoEcho` parameter.

After the launcher gives the instance ID:

```bash
aws ssm start-session --region us-east-1 --target INSTANCE_ID_FROM_OUTPUT
```

In that instance session:

```bash
sudo sed -n 's/^NAGARSEVA_OFFICER_KEY=//p' /etc/urbansaarthi/runtime.env
```

Retrieve the value only in your private terminal, with screen recording disabled.
Enter it in **Administration → Demo administrator access**, not a frontend build
variable. Do not publish or paste the value into chat, GitHub or logs.

Visitors can read the synthetic workspace and create demonstration issues, visits
and feedback without this key. Administrative status changes, project/milestone
edits, housing assessments, configuration/reset, controlled imports and private
downloads require it. It is a shared-key demonstration control, not production
user identity or government officer authentication. Local development records are
not copied into AWS automatically.

## Publish code updates manually

**Pushing to GitHub does not automatically update AWS.** The checked-in GitHub
workflows run validation and preserved source/evidence tasks, not an EC2 release
job. The initial launcher only verifies an existing successful stack. Neither
rerunning it nor restarting the old container installs a new application version.

First review and publish the intended source changes to GitHub. Exclude runtime
databases, credentials, environment files and backups. In EC2, use **Connect →
Session Manager** on the existing stack's instance. Run the following blocks in
order, in the same shell. Stop if a command fails; do not proceed with a failed
build or missing backup.

### 1. Inspect the source checkout

```bash
sudo -i
cd /opt/urbansaarthi/source
git status --short
```

If this prints local changes, preserve/review them before checkout. Do not discard
them. For a clean checkout, fetch the published branch and build while the current
application is still running:

```bash
git fetch origin main
git checkout --detach FETCH_HEAD
URBAN_NEXT_REVISION=$(git rev-parse HEAD)
URBAN_NEXT_IMAGE="urbansaarthi:$URBAN_NEXT_REVISION"
docker build --file deploy/aws/Dockerfile --tag "$URBAN_NEXT_IMAGE" .
docker image inspect "$URBAN_NEXT_IMAGE" --format '{{.Id}}'
```

This deploys the commit fetched from `main`. A reviewed release commit can be
checked out instead. An image build failure leaves the old container available;
fix the build before continuing. A micro instance may build slowly.

This procedure updates application code in the container. CloudFormation template
changes need a separately reviewed infrastructure update; building an image does
not change security groups, origin policies or volume lifecycle settings.

### 2. Back up existing state and configuration

This uses SQLite's online backup mechanism rather than copying an open database
file. It also works if the old container is stopped, provided its image and mount
still exist. An unexpected database path stops the backup instead of creating a
new empty database:

```bash
URBAN_RELEASE_STAMP=$(date -u +%Y%m%dT%H%M%SZ)
URBAN_EXISTING_IMAGE=$(docker inspect --format '{{.Image}}' urbansaarthi)
docker run --rm --entrypoint python \
  --env-file /etc/urbansaarthi/runtime.env \
  --mount type=bind,source=/var/lib/urbansaarthi,target=/data \
  "$URBAN_EXISTING_IMAGE" -c "import os,sqlite3; from pathlib import Path; from datetime import datetime,timezone; p=Path(os.getenv('URBANSAARTHI_DB_PATH','/data/urbansaarthi.sqlite3')); assert p.is_file(),'Existing database not found; stop and inspect storage'; target='/data/backup-before-update-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.sqlite3'; src=sqlite3.connect(p); dst=sqlite3.connect(target); src.backup(dst); dst.close(); src.close(); print(target)"
cp -p /etc/urbansaarthi/runtime.env "/etc/urbansaarthi/runtime.env.before-$URBAN_RELEASE_STAMP"
```

Keep a verified private copy outside the instance before deleting or replacing
storage. Backups on the root volume do not survive its deletion. Do not upload
databases or private environment files to GitHub.

### 3. Replace the container while retaining the volume

```bash
URBAN_PREVIOUS_CONTAINER="urbansaarthi-before-$URBAN_RELEASE_STAMP"
docker stop urbansaarthi
docker rename urbansaarthi "$URBAN_PREVIOUS_CONTAINER"
docker run --detach --name urbansaarthi --restart unless-stopped \
  --publish 80:8080 --env-file /etc/urbansaarthi/runtime.env \
  --mount type=bind,source=/var/lib/urbansaarthi,target=/data \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=32m \
  --cap-drop ALL --security-opt no-new-privileges \
  --log-driver json-file --log-opt max-size=10m --log-opt max-file=3 \
  "$URBAN_NEXT_IMAGE"
docker logs --tail 50 urbansaarthi
docker inspect --format '{{.State.Health.Status}}' urbansaarthi
```

Wait for `healthy`; `starting` immediately after launch is not success. Then check
the actual CloudFront `/api/urban/demo/health` response and exercise the application.
The old stopped container remains available for rollback. Do not delete images or
old containers until the new release and wanted backups have been checked.

The existing private environment and database mount are reused. Changing
`runtime.env`, for example to enable optional photo storage, takes effect when the
container is recreated with `--env-file`; `docker restart` alone does not reload it.
Normal AWS-only hosting leaves the frontend API prefix at `/api`.

### 4. Roll back the image if needed

In the same shell, if the new container exists but fails its checks:

```bash
docker stop urbansaarthi
docker rename urbansaarthi "urbansaarthi-failed-$(date -u +%Y%m%dT%H%M%SZ)"
cp -p "/etc/urbansaarthi/runtime.env.before-$URBAN_RELEASE_STAMP" /etc/urbansaarthi/runtime.env
docker rename "$URBAN_PREVIOUS_CONTAINER" urbansaarthi
docker start urbansaarthi
docker inspect --format '{{.State.Health.Status}}' urbansaarthi
```

If the session was lost, inspect `docker ps -a` and retained backup filenames first;
the variables above are shell-local. Select the actual prior container rather than
guessing a timestamp. If creation of the new container failed entirely, there may
be no new `urbansaarthi` container to stop/rename; restore the retained previous
container directly after inspecting names.

Image rollback leaves the current database in place. A future incompatible schema
change may require a separately reviewed restore during maintenance. Never copy a
backup over a running SQLite database or claim an image rollback restores data.

## Network, storage and privacy limits

- Only CloudFront's AWS-managed origin-facing IPv4 prefix list can reach EC2 port 80. SSH/8000/8080 are not exposed. Maintenance uses Session Manager. A second origin header blocks other CloudFront distributions; it is separate from the officer key. Security-group prefix-list quota limitations can cause creation failure; review events rather than broadening ingress to the world.
- Viewers use HTTPS. **CloudFront → EC2 uses HTTP** within AWS with network/header restrictions; this is not end-to-end TLS or a private VPC origin. Use synthetic demo data only. Before any real pilot, design origin TLS/private connectivity, authenticated roles, privacy/retention, backups, abuse protection and agency approval. An EBS encrypted volume does not encrypt that network hop.
- CloudFront caching is disabled for the entire prototype, including errors. The wrapper sends `Cache-Control: no-store` and keeps `/api` errors separate from frontend files. Its origin policy forwards `Content-Type`, `X-Officer-Key`, `Idempotency-Key`, `Origin`, `Access-Control-Request-Method` and `Access-Control-Request-Headers`. Ordinary request envelopes are limited to 3,000,000 bytes; only the explicit onboarding/legacy import paths accept up to 12 MiB for encoded files. Dataset source files remain capped at 5 MiB, and optional issue photos at 2 MiB.
- Container filesystem is read-only except `/data` and temporary memory. It runs as UID 10001 with Linux capabilities dropped. No models, `.env`, credentials or local databases are copied into the image.
- SQLite survives container restart, EC2 reboot and stop/start with the existing EBS volume. The Elastic IP keeps the origin address stable across stop/start. **Termination, instance replacement or stack deletion removes the configured root volume and its records.** There is no managed backup or high availability. Evidence file bytes are inside SQLite; this is not an S3 upload system.
- Shared-key protection and typed reviewer names are demonstration controls, not authenticated independent officers or production RBAC. All geography/deficit/scenario inputs retain their existing synthetic labels; deployment does not create field evidence.

## Troubleshooting

CloudFormation failure events are printed by the launcher. Use the console's Events tab for permission/plan/region/quota errors. Do not remove a resource whose ownership you have not checked.

For a created instance, use **EC2 → instance → Connect → Session Manager** or the command above. In its session:

```bash
sudo tail -n 80 /var/log/urbansaarthi-bootstrap.log
sudo docker ps -a
sudo docker logs --tail 80 urbansaarthi
sudo docker inspect --format '{{.State.Health.Status}}' urbansaarthi
df -h
```

The first build requires outbound access to Amazon Linux repositories, GitHub, Docker Hub and PyPI/npm registries. Rate limits, unavailable packages, build failure or account restrictions are deployment failures, not successful hosting. Inspect logs before retrying; the initial bootstrap is not safe to blindly rerun against an existing container. Do not post the runtime env file or secrets with logs.

### Repair the initial image's `/app/hosted.py` permission failure

The first deployment version (`565906ed79bee74b101cc7384f58007139f13879`) built from a root Git checkout made under `umask 077`. Its Dockerfile copied the resulting private source modes into a root-owned `/app`, then switched to UID 10001. This caused `PermissionError: [Errno 13] Permission denied: '/app/hosted.py'` on EC2. The original CI checkout was readable, so it did not expose that difference. The Dockerfile now explicitly grants read/traverse access to application assets before switching users. It does not grant access to the separate runtime secret file or saved database.

For this exact error, run in the **existing EC2 Session Manager shell**:

```bash
sudo git -C /opt/urbansaarthi/source fetch origin main
sudo git -C /opt/urbansaarthi/source show FETCH_HEAD:deploy/aws/repair-permissions.sh | sudo bash
```

The repair builds a permission-only layer from the installed image, probes imports as UID 10001, retains the stopped previous container, and starts the repaired image with the same private runtime env file, database bind mount and hardening. It does not rerun npm/pip, recreate the database, rotate keys or replace infrastructure. It validates the local frontend, health and operational `401`; public CloudFront readiness is a separate check.

After it reports local checks passed, use `exit` to return to CloudShell. From the existing `urbansaarthi-aws` checkout, run:

```bash
URBANSAARTHI_AWS_REGION=us-east-1 bash deploy/aws/launch.sh
```

Use your actual region if different. The launcher verifies the existing stack's HTTPS endpoint without launching another instance. Do not rerun the entire bootstrap as a substitute for this targeted repair.

## Backups and removal

Before deleting or replacing the instance, create a consistent SQLite backup inside the container and copy it off the instance using an approved private transfer/storage path. In Session Manager, this creates a snapshot file in the persistent bind mount:

```bash
sudo docker exec urbansaarthi python -c "import sqlite3; from datetime import datetime,timezone; p='/data/backup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.sqlite3'; src=sqlite3.connect('/data/urbansaarthi.sqlite3'); dst=sqlite3.connect(p); src.backup(dst); dst.close(); src.close(); print(p)"
```

A backup on that same EBS volume will also be deleted with it; verify an off-instance copy before deletion. Never publish it to GitHub or make an S3 backup bucket public. An EBS snapshot/private S3 backup has separate storage costs.

When you deliberately want to remove this demo, delete **only `urbansaarthi-demo`** in CloudFormation (or your explicitly chosen stack name), after retaining any wanted data. This destroys its app records. Its CloudFront distribution and Elastic IP are managed by the stack and should also be removed. Check for `DELETE_FAILED`, retained resources/snapshots and remaining Billing usage afterward. No deletion command is automatically executed by the launcher.

## Validation boundary and primary references

The main [testing guide](../../README.md#testing-and-verification) records checks
executed during the current documentation refresh. Public HTTP/schema checks are
read-only. Local browser acceptance uses disposable records; a CI definition or a
passing local unit test does not prove a live container restart or field outcome.

[AWS readiness workflow](../../.github/workflows/aws-readiness.yml) performs pinned-runtime ASGI wrapper tests, CloudFormation schema lint for Mumbai and `us-east-1`, an actual Docker production build, HTTP/auth/calculation/upload checks and a container restart/persistence check. It now builds from deliberately restrictive 0600-file/0700-directory checkout modes, reproduces the original permission failure using a complete current-source image with only the readability repair removed, validates the fixed Dockerfile, then exercises the actual repair script against the broken image while checking that seeded records, evidence and officer access survive. These checks use synthetic CI records and no AWS credentials; they do not launch EC2, validate this account's credits, test CloudFront networking or prove public availability. The normal app calculation/browser validation remains in `integration/`.

Primary references (the preserved deployment investigation originally accessed
these on **18 October 2026**; current resource settings are defined by the checked-in
template and scripts):

- [AWS Free Tier FAQ](https://aws.amazon.com/free/free-tier-faqs/) — plan, credit, expiry and October 2026 account-screen differences.
- [EC2 Free Tier usage](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html) — account-date-dependent offers; eligibility is not unlimited usage.
- [GetAccountPlanState](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_freetier_GetAccountPlanState.html) — reported plan status, remaining credits and expiry fields.
- [VPC/public IPv4 pricing](https://aws.amazon.com/vpc/pricing/) — public IPv4 charges.
- [CloudFront pricing](https://aws.amazon.com/cloudfront/pricing/) and [FAQ](https://aws.amazon.com/cloudfront/faqs/) — distinguish flat-rate plans from pay-as-you-go allowances.
- [Flat-rate plan account requirements](https://docs.aws.amazon.com/PricingPlanManager/latest/UserGuide/pricingplanmanager-ug.pdf) — do not assume Free account eligibility for flat-rate plans.
- [Managed cache policies](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-cache-policies.html) — `CachingDisabled` ID and zero TTLs.
- [EC2 CloudFormation resource](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ec2-instance.html) — instance, volume deletion and address behavior.
- [Amazon EBS storage](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Storage.html) — persistence and lifecycle distinctions.
- [Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html) — shell access without opening SSH.
