# CI/CD Workflows — GitHub Actions (Terraform + Build/Deploy)

This document describes the repository's GitHub Actions workflows under `.github/workflows/`. It focuses only on the CI/CD workflows present in this repository and explains triggers, inputs, secrets, and usage patterns.

## Workflows overview
- build-deploy.yaml — Build & push Docker image to Google Artifact Registry and deploy to Cloud Run (reusable via `workflow_call`).
- deploy-manual.yaml — Manual dispatch wrapper that calls `build-deploy.yaml`.
- reusable-terraform-plan.yaml — Reusable workflow that runs `terraform plan` for a matrix of Terraform stacks.
- reusable-terraform-apply.yaml — Reusable workflow that runs `terraform apply` for a matrix of Terraform stacks.
- terraform-plan.yaml — CI workflow that detects changed Terraform stacks, generates a matrix, and calls the reusable plan for `dev`.
- terraform-apply.yaml — Push/dispatch workflow that detects changed stacks and calls the reusable apply for `dev`.

---

## Common concepts

- Reusable workflows
  - `workflow_call` is used to make `build-deploy`, `reusable-terraform-plan`, and `reusable-terraform-apply` callable from other workflows.
  - Inputs: `matrix` (JSON-encoded array of stack entries) and `environment` are common inputs.

- Matrix
  - The terraform workflows expect a JSON matrix of stack entries produced by `scripts/tf_dep_map.py`.
  - Each matrix entry typically contains at least: `dir` (stack dir) and `env` (environment like `dev`).
  - Example matrix JSON:
    [
      {"dir":"IAC/Terraform/network","env":"dev"},
      {"dir":"IAC/Terraform/app","env":"dev"}
    ]

- Google Cloud auth
  - Dev workflows use `google-github-actions/auth@v2` with a Workload Identity Provider and a GCP service account (inputs or envs).
  - `id-token: write` permission is required by these workflows.

- Terraform helper tools
  - `terraform-config-inspect` and a Python script `scripts/tf_dep_map.py` are used to generate dependency matrices.
  - `astral-sh/setup-uv@v1` and Node are used in plan workflow for utilities (UV).

---

## Detailed workflow notes

### build-deploy.yaml
- Purpose: Build image with Docker Buildx, push to Google Artifact Registry (GAR), then deploy to Cloud Run.
- Trigger: `workflow_call` (inputs: `gcp-project-id`, `cloudrun_name`, `cloudrun_location`).
- Important envs:
  - `APP_ARTIFACT_REGISTRY_URL`, `APP_IMAGE_NAME`, `GCP_INFRA_IDP`, `GCP_INFRA_GHA_SERVICE_ACCOUNT` (set in file).
- Key steps:
  - Checkout
  - Docker login to GAR using a custom action with Workload Identity
  - Generate revision tag from branch + short SHA
  - Build & push image (buildx)
  - Deploy to Cloud Run via a custom action
- Required secrets/permissions:
  - Repository-level Workload Identity setup for GCP service account; no plain GCP secrets in the repo.

### deploy-manual.yaml
- Purpose: Manual dispatcher for `build-deploy.yaml`.
- Trigger: `workflow_dispatch` with inputs for GCP project, Cloud Run name & location.
- Implementation: Calls `build-deploy.yaml` via `uses: ./.github/workflows/build-deploy.yaml`.

### reusable-terraform-plan.yaml
- Purpose: Run `terraform init` and `terraform plan` for each matrix entry.
- Trigger: `workflow_call` inputs: `matrix`, `environment`, `GCP_PROJECT_DEV`, `GCP_INFRA_IDP`, `GCP_INFRA_GHA_SERVICE_ACCOUNT`.
- Key behavior:
  - Checks out `master`
  - Sets up Terraform
  - Optionally authenticates to GCP when environment == `dev` using Workload Identity
  - Runs `terraform init` and `terraform plan` (writes `plan_output.txt`)
  - If plan fails, checks `plan_output.txt` for a `prevent_destroy` violation and fails with a helpful message if detected.
- Permissions: `pull-requests: write` to post plan results or comments (configured).

### reusable-terraform-apply.yaml
- Purpose: Run `terraform init` and `terraform apply -auto-approve` across matrix entries.
- Trigger: `workflow_call` inputs: same as plan.
- Key behavior:
  - Optionally authenticates to GCP when environment == `dev`
  - Runs `terraform init` and `terraform apply -auto-approve`
- Note: This action should be gated (manual approval / environments protected) before applying to prod.

### terraform-plan.yaml
- Purpose: Repo-level Terraform CI for PRs or manual dispatch.
- Triggers:
  - `pull_request`
  - `workflow_dispatch` (inputs: `stacks`, `environment`)
- Key steps:
  - `terraform-fmt` sanity check
  - `detect-changes`: uses `tj-actions/changed-files` for PRs or `scripts/tf_dep_map.py` on manual runs to generate a matrix of stacks
  - Calls reusable plan for `dev` using `uses: ./.github/workflows/reusable-terraform-plan.yaml`
- Concurrency: cancels in-progress runs for the same ref to avoid duplicate work.

### terraform-apply.yaml
- Purpose: Auto-apply/dispatch Terraform changes on pushes to `master` or manual runs.
- Triggers:
  - `push` to `master` for changes in `IAC/Terraform/**`
  - `workflow_dispatch`
- Key steps:
  - Detect changed Terraform dirs (similar to plan workflow)
  - Calls reusable apply for `dev` for matching matrix entries
- Important: This workflow does an unconditional `terraform apply -auto-approve` in the reusable apply. Protect `master` branch and restrict who can trigger apply workflows.

---

## Required secrets & repository configuration

- Workload Identity / GCP:
  - Configure a Workload Identity Provider and a dedicated GitHub service account mapping.
  - Set `GCP_INFRA_IDP` and `GCP_INFRA_GHA_SERVICE_ACCOUNT` (used as inputs/envs). These are set inside workflows or passed in.
- Artifact Registry & Cloud Run:
  - No raw credentials stored — the build steps rely on workload identity and custom actions; ensure IAM roles are set up.
- Recommended GitHub repo settings:
  - Protect `master` branch
  - Require approvals for workflows that run `terraform-apply`
  - Add environment protection rules for `dev` / production deploys
- Optional secrets (if you modify workflows to use service account JSON):
  - `GCP_SA_KEY` (not used by current workflows — prefer Workload Identity)

---

## How to run / common usage

- Manual image build & deploy:
  1. GitHub UI → Actions → Choose `Deploy Docker image to Cloud Run Job` (deploy-manual).
  2. Provide project id, cloud run name & location, then dispatch.

- Manual Terraform plan for explicit stacks:
  1. GitHub UI → Actions → `Terraform CI` → Run workflow dispatch
  2. Provide `stacks` input (space-separated relative paths or `all`) and optional environment `dev`.

- Example manual matrix invocation (advanced):
  - Create a JSON matrix and call reusable workflow via another workflow or from CLI by constructing the `matrix` input. Each matrix item must be JSON-encoded string passed to `inputs.matrix`.

---

## Troubleshooting & tips

- Terraform plan failure:
  - If plan fails, check `plan_output.txt` for a `prevent_destroy` violation. The plan workflow will surface a clear error if it finds this condition.
- No stacks detected:
  - Ensure `scripts/tf_dep_map.py` is present and executable. For PRs, changed files must be under `IAC/Terraform/**`.
- GCP auth errors:
  - Verify Workload Identity provider ARN and service account email are correct.
  - Validate the GitHub action service account has appropriate IAM roles for Artifact Registry, Cloud Run, and Terraform state access.
- Reusable workflow debugging:
  - Re-run with `workflow_dispatch` on the parent workflow and add `echo` / extra logging if required.

---

## Security & best practices (summary)

- Use Workload Identity instead of embedding service account keys.
- Protect branches and require reviews before terraform apply.
- Use Terraform remote state with locking for team workflows.
- Store sensitive values in GitHub Secrets or use cloud-native secret managers.
- Prefer manual approval for `apply` workflows targeting production.

---
