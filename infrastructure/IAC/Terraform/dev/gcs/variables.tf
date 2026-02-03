variable "project_id" {
  description = "GCP Project ID in which the resource will be provisioned."
  type        = string
  default     = ""
}

variable "gcs_bucket" {
  description = "The details of the Cloud Storage Buckets."
  type = map(object({
    app_name           = string,
    location           = string,
    versioning         = bool,
    storage_class      = string,
    bucket_policy_only = bool,
    force_destroy      = bool,
    enable_neg         = bool,
    neg_default_port   = optional(string),
    port               = optional(string),
    labels             = map(string),
    data_locations     = list(string),
    retention_policy = object({
      is_locked        = bool
      retention_period = number
    })
    iam_members = optional(list(object({
      role   = string
      member = string
    })), [])
    cors = optional(list(object({
      origin          = list(string)
      method          = list(string)
      response_header = optional(list(string))
      max_age_seconds = optional(number)
    })))
    lifecycle_rules = optional(list(object({
      action = object({
        type          = string
        storage_class = optional(string)
      })
      condition = object({
        age                        = optional(number)
        send_age_if_zero           = optional(bool)
        created_before             = optional(string)
        with_state                 = optional(string)
        matches_storage_class      = optional(list(string))
        matches_prefix             = optional(list(string))
        matches_suffix             = optional(list(string))
        num_newer_versions         = optional(number)
        custom_time_before         = optional(string)
        days_since_custom_time     = optional(number)
        days_since_noncurrent_time = optional(number)
        noncurrent_time_before     = optional(string)
      })
    })), []),
    tag_bindings = optional(list(string), [])
    soft_delete_policy = optional(object({
      retention_duration_seconds = optional(number)
    }))
    website = optional(object({
      main_page_suffix = optional(string)
      not_found_page   = optional(string)
    }))
  }))
}

variable "gcs_managed_folder_iam_bindings" {
  description = "A map of role and member bindings to apply to the gcs managed folder."
  type = map(object({
    bucket_name   = string
    bucket_folder = string
    member        = string
    role          = string
  }))
  default = {}
}
