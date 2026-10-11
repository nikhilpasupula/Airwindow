#!/usr/bin/env bash
# One-time setup + deploy. Needs: AWS CLI configured, AWS SAM CLI installed.
set -euo pipefail
REGION="${AWS_REGION:-ap-south-1}"

read -r -s -p "Paste your TinyFish API key: " TF_KEY; echo
aws ssm put-parameter --region "$REGION" --name /airwindow/tinyfish-api-key \
  --type SecureString --value "$TF_KEY" --overwrite >/dev/null
echo "Stored TinyFish key in SSM Parameter Store."

python3 -m pytest -q
sam build
sam deploy --region "$REGION"
echo "Done. Open the AppUrl shown above."
