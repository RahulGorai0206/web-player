output "workload_identity_provider" {
  description = "The full name of the Workload Identity Provider. Needed for GitHub Actions workflow."
  value       = google_iam_workload_identity_pool_provider.github_provider.name
}

output "service_account_email" {
  description = "The email of the service account configured for impersonation."
  value       = var.service_account_email
}
