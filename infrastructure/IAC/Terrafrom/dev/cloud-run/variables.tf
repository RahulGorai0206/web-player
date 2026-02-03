variable "service_project_id" {
  type = string
}

variable "cloud_run" {
  description = "The details of the Cloud Run"
  type = map(object({
    service_name                  = string,
    datadog_service_name          = optional(string),
    location                      = string,
    create_service_account        = bool,
    service_account               = string,
    cloud_run_deletion_protection = optional(bool),
    ingress                       = string,
    service_labels                = map(string),
    vpc_access = optional(object({
      connector = optional(string)
      egress    = optional(string)
      network_interfaces = optional(object({
        network    = optional(string)
        subnetwork = optional(string)
        tags       = optional(list(string))
      }))
    })),
    volumes = optional(list(object({
      name = string
      secret = optional(object({
        secret       = string
        default_mode = optional(string)
        items = optional(object({
          path    = string
          version = optional(string)
          mode    = optional(string)
        }))
      }))
      cloud_sql_instance = optional(object({
        instances = optional(list(string))
      }))
      empty_dir = optional(object({
        medium     = optional(string)
        size_limit = optional(string)
      }))
      gcs = optional(object({
        bucket    = string
        read_only = optional(string)
      }))
      nfs = optional(object({
        server    = string
        path      = string
        read_only = optional(string)
      }))
    })), [])
    containers = list(object({
      container_name       = optional(string, null)
      container_image      = string
      working_dir          = optional(string, null)
      depends_on_container = optional(list(string), null)
      container_args       = optional(list(string), null)
      container_command    = optional(list(string), null)
      env_vars             = optional(map(string), {})
      env_secret_vars = optional(map(object({
        secret  = string
        version = string
      })), {})
      volume_mounts = optional(list(object({
        name       = string
        mount_path = string
      })), [])
      ports = optional(object({
        name           = optional(string)
        container_port = optional(number)
      }), {})
      resources = optional(object({
        limits = optional(object({
          cpu    = optional(string)
          memory = optional(string)
        }))
        cpu_idle          = optional(bool, true)
        startup_cpu_boost = optional(bool, false)
      }), {})
      startup_probe = optional(object({
        failure_threshold     = optional(number, null)
        initial_delay_seconds = optional(number, null)
        timeout_seconds       = optional(number, null)
        period_seconds        = optional(number, null)
        http_get = optional(object({
          path = optional(string)
          port = optional(string)
          http_headers = optional(list(object({
            name  = string
            value = string
          })), [])
        }), null)
        tcp_socket = optional(object({
          port = optional(number)
        }), null)
        grpc = optional(object({
          port    = optional(number)
          service = optional(string)
        }), null)
      }), null)
      liveness_probe = optional(object({
        failure_threshold     = optional(number, null)
        initial_delay_seconds = optional(number, null)
        timeout_seconds       = optional(number, null)
        period_seconds        = optional(number, null)
        http_get = optional(object({
          path = optional(string)
          port = optional(string)
          http_headers = optional(list(object({
            name  = string
            value = string
          })), null)
        }), null)
        tcp_socket = optional(object({
          port = optional(number)
        }), null)
        grpc = optional(object({
          port    = optional(number)
          service = optional(string)
        }), null)
      }), null)
    }))
    max_instance_request_concurrency = optional(string, "80"),
    template_annotations             = optional(map(string), null),
    scaling = object({
      min_instance_count = optional(number, 1)
      max_instance_count = optional(number, 5)
    })
  }))
}
