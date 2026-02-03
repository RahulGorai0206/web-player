variable "region_name" {
  description = "Name of the Region for deployment"
  type        = string
}

variable "repo_id" {
  description = "Name of the Repository for deployment"
  type        = string
}

variable "format_type" {
  description = "Name of the Format for deployment"
  type        = string
}

variable "project_id" {
  description = "Name of the Project ID"
  type        = string
}

variable "labels" {
  description = "A set of key/value label pairs to assign to the artifact registry"
  type        = map(string)
  default     = null
}

variable "description" {
  description = "A set of key/value label pairs to assign to the artifact registry"
  type        = string
  default     = "For Docker Images"
}

variable "immutable_tags" {
  description = "he repository which enabled this flag prevents all tags from being modified, moved or deleted. This does not prevent tags from being created."
  type        = bool
  default     = true
}

variable "cleanup_policies" {
  type = map(object({
    action = optional(string)
    condition = optional(object({
      tag_state             = optional(string)
      tag_prefixes          = optional(list(string))
      version_name_prefixes = optional(list(string))
      package_name_prefixes = optional(list(string))
      older_than            = optional(string)
      newer_than            = optional(string)
    }), null)
    most_recent_versions = optional(object({
      package_name_prefixes = optional(list(string))
      keep_count            = optional(number)
    }), null)
  }))
  description = "Cleanup policies for this repository. Cleanup policies indicate when certain package versions can be automatically deleted. Map keys are policy IDs supplied by users during policy creation. They must unique within a repository and be under 128 characters in length."
  default     = {}
}
