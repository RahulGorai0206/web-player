# ==============================================================================
# Input Variables
# ==============================================================================

variable "project_id" {
  description = "The GCP project ID to deploy the resources in."
  type        = string
}

variable "pool_id" {
  description = "A unique ID for the Workload Identity Pool."
  type        = string
  default     = "github-pool"
}

variable "provider_id" {
  description = "A unique ID for the Workload Identity Pool Provider."
  type        = string
  default     = "github-provider"
}

variable "pool_display_name" {
  description = "A unique ID for the Workload Identity Pool."
  type        = string
  default     = ""
}

variable "service_account_email" {
  description = "The email of the EXISTING GCP service account that GitHub Actions will impersonate."
  type        = string
}

variable "github_owner" {
  description = "The GitHub organization or user that owns the repository."
  type        = string
}

# variable "github_repo" {
#   description = "The name of the GitHub repository that will use this identity."
#   type        = string
# }
