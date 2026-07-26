# AWS deployment

Merges to `master` trigger `.github/workflows/deploy.yml`. The workflow tests
the app, packages the Lambda, uploads the package to S3, and deploys the
`bin-day` CloudFormation stack.

## One-time AWS setup

Deploy `bootstrap.yaml` once from an administrator session in AWS account
`016696950356`:

```sh
aws cloudformation deploy \
  --region eu-west-2 \
  --stack-name bin-day-bootstrap \
  --template-file bootstrap.yaml \
  --capabilities CAPABILITY_NAMED_IAM
```

This creates:

1. The private, encrypted, versioned artifact bucket
   `bin-day-deployments-016696950356-eu-west-2`.
2. The `bin-day-github-deploy` IAM role.
3. A GitHub Actions OIDC provider, with trust restricted to the
   `morgan-murray/bin-day` repository's `production` environment.

If the AWS account already has the GitHub Actions OIDC provider, deploy with:

```sh
aws cloudformation deploy \
  --region eu-west-2 \
  --stack-name bin-day-bootstrap \
  --template-file bootstrap.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    CreateGitHubOidcProvider=false \
    ExistingGitHubOidcProviderArn=arn:aws:iam::016696950356:oidc-provider/token.actions.githubusercontent.com
```

The workflow deliberately uses OIDC instead of long-lived AWS access keys.

## GitHub production environment

Create a GitHub environment named `production`. The account, region, artifact
bucket, deployment role ARN, and Alexa skill ID are configured in the workflow;
no AWS secrets or access keys are required. Environment protection rules can
optionally require approval before production deployment.

## Alexa developer console

After the first successful deployment, copy the `FunctionArn` shown by the
workflow (or the CloudFormation stack output) into the skill's default endpoint
in the Alexa developer console. Build and save the interaction model there
using `interaction_model.json`.
