# AWS deployment: credit-funded demonstration

This deploys the existing five-screen UrbanSaarthi app and its FastAPI API on one `t3.micro` EC2 instance in Mumbai (`ap-south-1`). CloudFront supplies an HTTPS `cloudfront.net` address; no purchased domain is needed. SQLite records, including uploaded demo evidence, live on the instance's encrypted 20 GiB gp3 EBS root volume. No RDS, NAT Gateway, load balancer, Kubernetes or model training is provisioned.

**Status:** deployment files and automated readiness checks are prepared. An AWS account deployment is not established by these files or by passing CI. Only the launcher's successful live checks establish app readiness. This session has no AWS credentials or connected console, and cannot provision the account itself.

## Cost boundary before launching

The user confirmed active AWS Free Tier credits. Their amount, expiry, covered services and account plan have not been independently verified in this session. Check **Billing → Credits / Free Tier**, or the current account's **Settings Portal → Billing**, before running the command. AWS changed its sign-up experience in October 2026; the exact screen depends on the account.

- EC2 compute, EBS storage and **one public IPv4/Elastic IP** can consume credits and incur charges when credits are insufficient or inapplicable. An Elastic IP is not assumed free just because it is attached. CPU credit mode is `standard`, avoiding T3 Unlimited surplus-credit charges; exhausted CPU credits can throttle the demo.
- This template creates **pay-as-you-go CloudFront**, using the applicable monthly free allowances/credits. It does **not** enroll the account in the separate flat-rate CloudFront Free plan and does not promise no overages. The latter has different eligibility and cannot be assumed available to a Free account.
- AWS's current Free plan and a Paid account with promotional credits have different exhaustion behavior. Do not upgrade the account or enable a paid feature just to bypass a provisioning restriction.
- Set a small **AWS Budgets** notification in the console and inspect gross service usage as well as credit balance. A normal budget alert is **not a hard spending cap**. The script does not create an email subscription, a budget or a guaranteed ₹0 enforcement policy. It attempts an informational Free Tier plan/credit API check and stops if that API reports zero credits or expiry; a failed/unavailable check is reported, not silently treated as proof of coverage.
- Stopping EC2 stops its compute consumption, but EBS and the Elastic IP remain chargeable. Remove the stack after backing up any wanted records when the demo is finished. No automatic expiry/deletion job is installed.

Do not treat generic “Free tier eligible” labels as confirmation that every resource or all traffic is free. No monthly price or credit lifetime is fabricated here.

## Launch in AWS CloudShell

Sign in to your own AWS account. Open [AWS CloudShell](https://console.aws.amazon.com/cloudshell/home?region=ap-south-1). The signed-in principal needs permission to create/read the resources in the generated CloudFormation template, create/pass the EC2 instance role, and start a Session Manager session. **Do not create access keys, give the application an AdministratorAccess role, or paste AWS credentials into chat.** The instance receives only AWS's Session Manager core managed policy.

In a fresh CloudShell directory:

```bash
git clone https://github.com/vishal88736/nagarseva-seva-first.git urbansaarthi-aws
cd urbansaarthi-aws
bash deploy/aws/launch.sh
```

The script deploys the exact checkout commit from the public repository. Commit/push changed deployment or app files before use. If the directory already exists, use that checkout after inspecting/pulling its updates instead of repeating the clone into it. The default stack name is `urbansaarthi-demo`. An existing successful/in-progress stack is resumed; failed stacks are not automatically destroyed or replaced. Changing the source checkout does not update an existing instance: this is an initial-deployment script, not a CI release manager.

Allow several minutes for CloudFront and the first Docker build; a throttled micro instance can take longer. The script waits for the HTTPS API health, frontend HTML and an unauthenticated `401` on operational state. **Infrastructure `CREATE_COMPLETE` alone does not establish application readiness.** Only after those checks pass does it print `Verified website: https://…cloudfront.net`.

If your account's allowed region differs, set `URBANSAARTHI_AWS_REGION` to that enabled commercial AWS region before launching. No region is enabled automatically. `URBANSAARTHI_AWS_INSTANCE_TYPE=t3.small` is an optional more expensive 2 GiB instance; default is `t3.micro` with 2 GiB encrypted-volume swap for the build. Do not enlarge it without checking credit consumption. The script does not turn on account advanced features or upgrade its plan.

## Open officer access

The officer key is randomly generated **on EC2** and kept in `/etc/urbansaarthi/runtime.env`, readable by root. It is not a frontend build variable or GitHub secret. CloudFormation's separate origin token is a `NoEcho` parameter.

After the launcher gives the instance ID:

```bash
aws ssm start-session --region ap-south-1 --target INSTANCE_ID_FROM_OUTPUT
```

In that instance session:

```bash
sudo sed -n 's/^NAGARSEVA_OFFICER_KEY=//p' /etc/urbansaarthi/runtime.env
```

Enter the displayed key in the site's **Officer access** panel. Keep it private. Visitors can inspect the synthetic planning demo without this key; server records, writes and evidence downloads require it. Existing browser sandbox records stay separate and are not uploaded automatically.

## Network, storage and privacy limits

- Only CloudFront's AWS-managed origin-facing IPv4 prefix list can reach EC2 port 80. SSH/8000/8080 are not exposed. Maintenance uses Session Manager. A second origin header blocks other CloudFront distributions; it is separate from the officer key. Security-group prefix-list quota limitations can cause creation failure; review events rather than broadening ingress to the world.
- Viewers use HTTPS. **CloudFront → EC2 uses HTTP** within AWS with network/header restrictions; this is not end-to-end TLS or a private VPC origin. Use synthetic demo data only. Before any real pilot, design origin TLS/private connectivity, authenticated roles, privacy/retention, backups, abuse protection and agency approval. An EBS encrypted volume does not encrypt that network hop.
- CloudFront caching is disabled for the entire prototype, including errors. The wrapper sends `Cache-Control: no-store` and keeps `/api` errors separate from frontend files. `X-Officer-Key` and JSON content type are forwarded. Upload requests have a 3,000,000-byte envelope limit; existing individual files remain capped at 2 MiB.
- Container filesystem is read-only except `/data` and temporary memory. It runs as UID 10001 with Linux capabilities dropped. No models, `.env`, credentials or local databases are copied into the image.
- SQLite survives container restart, EC2 reboot and stop/start with the existing EBS volume. The Elastic IP keeps the origin address stable across stop/start. **Termination, instance replacement or stack deletion removes the configured root volume and its records.** There is no managed backup or high availability. Evidence file bytes are inside SQLite; this is not an S3 upload system.
- Shared-key protection and typed reviewer names are demonstration controls, not authenticated independent officers or production RBAC. All geography/deficit/scenario inputs retain their existing synthetic labels; deployment does not create field evidence.

## Diagnose a failed first launch

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

## Backup and shut down

Before deleting or replacing the instance, create a consistent SQLite backup inside the container and copy it off the instance using an approved private transfer/storage path. In Session Manager, this creates a snapshot file in the persistent bind mount:

```bash
sudo docker exec urbansaarthi python -c "import sqlite3; from datetime import datetime,timezone; p='/data/backup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.sqlite3'; src=sqlite3.connect('/data/urbansaarthi.sqlite3'); dst=sqlite3.connect(p); src.backup(dst); dst.close(); src.close(); print(p)"
```

A backup on that same EBS volume will also be deleted with it; verify an off-instance copy before deletion. Never publish it to GitHub or make an S3 backup bucket public. An EBS snapshot/private S3 backup has separate storage costs.

When you deliberately want to remove this demo, delete **only `urbansaarthi-demo`** in CloudFormation (or your explicitly chosen stack name), after retaining any wanted data. This destroys its app records. Its CloudFront distribution and Elastic IP are managed by the stack and should also be removed. Check for `DELETE_FAILED`, retained resources/snapshots and remaining Billing usage afterward. No deletion command is automatically executed by the launcher.

## Validation boundary and primary references

[AWS readiness workflow](../../.github/workflows/aws-readiness.yml) performs pinned-runtime ASGI wrapper tests, CloudFormation schema lint for Mumbai and `us-east-1`, an actual Docker production build, HTTP/auth/calculation/upload checks and a container restart/persistence check. It now builds from deliberately restrictive 0600-file/0700-directory checkout modes, reproduces the original image's reported failure, validates the fixed Dockerfile, then exercises the actual repair script against the broken image while checking that seeded records, evidence and officer access survive. These checks use synthetic CI records and no AWS credentials; they do not launch EC2, validate this account's credits, test CloudFront networking or prove public availability. The normal app calculation/browser validation remains in `integration/`.

Sources accessed **18 October 2026**:

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
