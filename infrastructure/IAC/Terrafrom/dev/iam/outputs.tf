/******************************************
  Outputs of service_account emails
 *****************************************/
output "service_account_emails" {
  description = "A list of the created Service Account Emails"
  value       = [for sa in module.service_accounts : sa.email]
}

output "custom_roles" {
  description = "A list of the created Custom role IDs"
  value       = [for role in module.custom_roles : role.custom_role_id]
}
