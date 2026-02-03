/******************************************
  service_account variables
 *****************************************/

variable "project_id" {
  type        = string
  description = "The GCP project ID"
}

variable "service_account_configs" {
  description = "A map of configurations for service accounts, their custom roles, and IAM bindings."
  type = map(object({
    service_account_name = string
    project_level_roles  = list(string)

    # If custom_role_id is null or omitted, no custom role will be created.
    custom_role_id          = optional(string, null)
    custom_role_permissions = optional(list(string), [])
  }))
  default = {}
}
