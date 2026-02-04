project_id = "rahul-playground-v1"

service_account_configs = {
  dev-github-oauth-sa = {
    service_account_name = "dev-github-oauth-sa"
    project_level_roles  = ["roles/artifactregistry.admin", "roles/iam.serviceAccountAdmin", "roles/storage.admin", "roles/iam.serviceAccountTokenCreator", "roles/iam.serviceAccountUser", "roles/run.admin", "roles/viewer", "roles/container.admin", "roles/resourcemanager.projectIamAdmin"]
  },
  dev-cloud-run-sa = {
    service_account_name = "dev-cloud-run-sa"
    project_level_roles  = ["roles/run.invoker", "roles/run.viewer", "roles/iam.serviceAccountUser"]
  }
}