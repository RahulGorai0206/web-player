variable "project_id" {
  type = string
}

variable "repo" {
  description = "The details of the Artifact Registries"
  type = map(object({
    repo_name      = string,
    region         = string,
    format         = string,
    description    = string,
    labels         = map(string),
    immutable_tags = bool,
    cleanup_policies = optional(map(object({
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
    })))
  }))
}
