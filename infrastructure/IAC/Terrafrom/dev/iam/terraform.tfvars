project_id = "rahul-playground-v1"

service_account_configs = {
  dev-github-oauth-sa = {
    service_account_name = "dev-github-oauth-sa"
    project_level_roles  = ["roles/artifactregistry.admin", "roles/iam.serviceAccountAdmin", "roles/storage.objectAdmin"]
  },
  dev-cloud-run-sa = {
    service_account_name = "dev-cloud-run-sa"
    project_level_roles  = ["roles/run.invoker", "roles/run.viewer"]
}
}