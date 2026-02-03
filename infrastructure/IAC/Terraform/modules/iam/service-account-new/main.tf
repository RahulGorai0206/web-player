
resource "google_service_account" "service_account" {
  account_id   = var.service_account_name
  display_name = var.service_account_name
  project      = var.project_id
}