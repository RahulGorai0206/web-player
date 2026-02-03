output "artifact_registry_repo_names" {
  description = "A map of all Artifact Registry repository names created by the module."
  value       = { for key, repo in module.artifact_registry : key => repo.repo_name }
}
