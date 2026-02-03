module "artifact_registry" {
  source           = "../../modules/artifact-registry"
  for_each         = var.repo
  region_name      = each.value.region
  project_id       = var.project_id
  repo_id          = each.value.repo_name
  format_type      = each.value.format
  labels           = each.value.labels
  description      = each.value.description
  immutable_tags   = each.value.immutable_tags
  cleanup_policies = each.value.cleanup_policies
}
