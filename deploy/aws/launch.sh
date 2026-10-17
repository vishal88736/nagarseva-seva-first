#!/bin/bash
# Run in the user's authenticated AWS CloudShell, from a clean public checkout.
set -euo pipefail
umask 077
urban_repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
urban_region=${URBANSAARTHI_AWS_REGION:-ap-south-1}
urban_stack=${URBANSAARTHI_AWS_STACK:-urbansaarthi-demo}
urban_instance_type=${URBANSAARTHI_AWS_INSTANCE_TYPE:-t3.micro}
urban_tmp=$(mktemp -d)
trap 'rm -rf -- "$urban_tmp"' EXIT
cd "$urban_repo"

for urban_command in aws python3 git curl; do
  command -v "$urban_command" >/dev/null || { echo "Missing $urban_command. Use AWS CloudShell." >&2; exit 1; }
done
aws sts get-caller-identity --region "$urban_region" >/dev/null
urban_revision=$(git rev-parse HEAD)
if ! git diff --quiet HEAD -- deploy/aws .dockerignore nagarseva/website nagarseva/shared nagarseva/model/api nagarseva/model/src/urban_planning.py; then
  echo 'Commit and push deployment/app changes first: EC2 checks out the exact public Git commit.' >&2
  exit 1
fi
git ls-files --error-unmatch deploy/aws/build_template.py >/dev/null

printf 'Region: %s | stack: %s | instance: %s | commit: %s\n' "$urban_region" "$urban_stack" "$urban_instance_type" "$urban_revision"
echo 'Creates credit-funded EC2, 20 GiB encrypted EBS, one billed public IPv4 and pay-as-you-go CloudFront.'
echo 'This is not an unlimited free deployment. Check credit coverage and expiry in Billing; the script does not upgrade your account.'

# Informational only: this API may be unavailable on an older CLI/account.
if aws freetier get-account-plan-state --region us-east-1 --output json > "$urban_tmp/plan.json" 2> "$urban_tmp/plan-error.txt"; then
  python3 - "$urban_tmp/plan.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))
print('AWS plan:', p.get('accountPlanType'), '| status:', p.get('accountPlanStatus'), '| remaining Free Tier credits:',p.get('accountPlanRemainingCredits'), '| expires:',p.get('accountPlanExpirationDate'))
credits=p.get('accountPlanRemainingCredits',{}).get('amount')
if credits is not None and float(credits)<=0:
    raise SystemExit('No remaining Free Tier credit reported. Stopping before creating resources.')
if p.get('accountPlanStatus')=='EXPIRED':
    raise SystemExit('Free Tier plan expired. Stopping before creating resources.')
PY
else
  echo 'Free Tier API check unavailable. Your confirmed active credit balance must be checked in Billing.'
fi

python3 deploy/aws/build_template.py > "$urban_tmp/template.json"
aws cloudformation validate-template --region "$urban_region" --template-body "file://$urban_tmp/template.json" > /dev/null

if aws cloudformation describe-stacks --region "$urban_region" --stack-name "$urban_stack" --output json > "$urban_tmp/existing.json" 2> "$urban_tmp/stack-error.txt"; then
  urban_status=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["Stacks"][0]["StackStatus"])' "$urban_tmp/existing.json")
  case "$urban_status" in
    CREATE_COMPLETE) echo 'Existing completed stack found; verifying its endpoint without creating another instance.' ;;
    CREATE_IN_PROGRESS) echo 'Existing stack is still being created; resuming the wait.' ;;
    *) echo "Existing stack status is $urban_status. Review its CloudFormation events; this script will not delete or replace it." >&2; exit 1 ;;
  esac
else
  if ! python3 - "$urban_tmp/stack-error.txt" <<'PY'
import sys
s=open(sys.argv[1]).read()
sys.exit(0 if 'ValidationError' in s and 'does not exist' in s else 1)
PY
  then
    cat "$urban_tmp/stack-error.txt" >&2
    exit 1
  fi
  urban_prefix=$(aws ec2 describe-managed-prefix-lists --region "$urban_region" \
    --filters Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing \
    --query 'PrefixLists[0].PrefixListId' --output text)
  [[ "$urban_prefix" == pl-* ]] || { echo 'CloudFront origin-facing prefix list unavailable in this region.' >&2; exit 1; }
  python3 - "$urban_tmp/parameters.json" "$urban_revision" "$urban_prefix" "$urban_instance_type" <<'PY'
import json,secrets,sys
values={'SourceRevision':sys.argv[2], 'CloudFrontPrefixList':sys.argv[3],
        'InstanceType':sys.argv[4], 'OriginSecret':secrets.token_hex(32)}
with open(sys.argv[1],'w') as f:
    json.dump([{'ParameterKey':k,'ParameterValue':v} for k,v in values.items()],f)
PY
  aws cloudformation create-stack --region "$urban_region" --stack-name "$urban_stack" \
    --template-body "file://$urban_tmp/template.json" --parameters "file://$urban_tmp/parameters.json" \
    --capabilities CAPABILITY_IAM --tags Key=Project,Value=UrbanSaarthi > /dev/null
  echo 'Stack creation started. CloudFront and the first container build can take several minutes.'
fi

if ! aws cloudformation wait stack-create-complete --region "$urban_region" --stack-name "$urban_stack"; then
  aws cloudformation describe-stack-events --region "$urban_region" --stack-name "$urban_stack" \
    --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`].[LogicalResourceId,ResourceStatusReason]' --output table
  echo 'Creation failed. Review the stack; check for remaining resources in Billing. No account upgrade or automatic retry was attempted.' >&2
  exit 1
fi
aws cloudformation describe-stacks --region "$urban_region" --stack-name "$urban_stack" --output json > "$urban_tmp/stack.json"
urban_url=$(python3 -c 'import json,sys; print(next(x["OutputValue"] for x in json.load(open(sys.argv[1]))["Stacks"][0]["Outputs"] if x["OutputKey"]=="WebsiteUrl"))' "$urban_tmp/stack.json")
urban_instance=$(python3 -c 'import json,sys; print(next(x["OutputValue"] for x in json.load(open(sys.argv[1]))["Stacks"][0]["Outputs"] if x["OutputKey"]=="InstanceId"))' "$urban_tmp/stack.json")
echo 'Infrastructure created. Waiting for app health, frontend HTML and officer protection…'
urban_ready=false
for urban_attempt in $(seq 1 40); do
  if curl --silent --show-error --fail --connect-timeout 5 --max-time 15 "$urban_url/api/urban/health" > "$urban_tmp/health.json" 2>/dev/null \
    && python3 -c 'import json,sys; h=json.load(open(sys.argv[1])); sys.exit(0 if h.get("status")=="ok" and h.get("officer_auth_required") is True else 1)' "$urban_tmp/health.json" \
    && curl --silent --fail --max-time 15 "$urban_url/" > "$urban_tmp/index.html" \
    && python3 -c 'import sys; sys.exit(0 if "<html" in open(sys.argv[1]).read().lower() else 1)' "$urban_tmp/index.html" \
    && [[ $(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 15 "$urban_url/api/urban/state") == 401 ]]; then
      urban_ready=true
      break
  fi
  printf 'Waiting for application (%s/40)…\n' "$urban_attempt"
  sleep 15
done
if [[ "$urban_ready" != true ]]; then
  printf 'Stack exists, but application readiness did not pass. Inspect bootstrap logs using Session Manager for %s.\n' "$urban_instance" >&2
  exit 1
fi
printf '\nVerified website: %s\nInstance: %s\n' "$urban_url" "$urban_instance"
printf 'Open a maintenance session: aws ssm start-session --region %s --target %s\n' "$urban_region" "$urban_instance"
echo 'In that session, retrieve your private demo officer key: sudo sed -n '\''s/^NAGARSEVA_OFFICER_KEY=//p'\'' /etc/urbansaarthi/runtime.env'
echo 'Enter it in the website’s Officer access panel. Do not paste the key into chat or GitHub.'
echo 'Only synthetic/consented demo files: this deployment has shared-key demo access, not production user identity.'
