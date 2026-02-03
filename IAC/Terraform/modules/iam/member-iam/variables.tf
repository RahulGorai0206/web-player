variable "service_account_address" {
  description = "Service account address. Mutually exclusive with principal_set_address."
  type        = string
  default     = null
}
variable "principal_set_address" {
  description = "Principal set address (e.g., allUsers, allAuthenticatedUsers). Mutually exclusive with service_account_address."
  type        = string
  default     = null
}
variable "project" {
  description = "Project id"
  type        = string
  default     = null
}
variable "project_roles" {
  description = "List of IAM roles"
  type        = list(string)
  default     = []
}
