output "custom_role_id" {
  description = "The ID of the created custom role, if any."
  value       = length(google_project_iam_custom_role.my_custom_role) > 0 ? google_project_iam_custom_role.my_custom_role[0].id : null
}