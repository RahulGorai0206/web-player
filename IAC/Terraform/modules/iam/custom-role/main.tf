resource "google_project_iam_custom_role" "my_custom_role" {
  count       = var.role_id == null ? 0 : 1
  project     = var.project
  role_id     = var.role_id
  title       = var.role_id
  stage       = "GA"
  permissions = var.permissions
}