# Terraform — player/IAC/Terraform

Small, focused Terraform repo for the project. Contains environment-level configs under env/ and reusable modules under modules/.

Quick overview
- env/ — per-environment Terraform workspaces (dev examples: artifact-registry, cloud-run, gcs, iam, service-api, workload-identity-federation).
- modules/ — reusable modules (artifact-registry, cloud_storage, cloud-run, iam helpers, service-api).

Quick usage
1. cd into target env, e.g.:
   cd Terraform/env/dev/cloud-run
2. Init, plan, apply:
   terraform init
   terraform plan -var-file=terraform.tfvars
   terraform apply -var-file=terraform.tfvars

Notes / best practices
- Keep secrets out of VCS (terraform.tfvars should be gitignored).
- Prefer remote state (check backend.tf in each env).
- Use modules/ to centralize logic; change with care and test in a dev workspace.
- Remove any committed .terraform/ or local terraform.tfstate files.

For details, inspect the env folder and module README files as needed.