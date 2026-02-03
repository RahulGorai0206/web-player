/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

data "google_compute_default_service_account" "default" {
  count   = local.create_service_account == false && var.service_account == null ? 1 : 0
  project = var.project_id
}

locals {
  # Central map for environment-specific settings, keyed by project_id.
  # environment_settings = {
  #   "rahul-playground-v1" = {
  #     datadog_enabled        = true
  #     datadog_secret_name    = "projects/828407182283/secrets/staging_datadog_base"
  #     datadog_secret_version = "latest"
  #     env_secrets_config_dir = "/etc/env-secrets.d"
  #   }
  #   "rahul-production-eu" = {
  #     datadog_enabled        = true
  #     datadog_secret_name    = "projects/37685959056/secrets/prod_datadog_base"
  #     datadog_secret_version = "latest"
  #     env_secrets_config_dir = "/etc/env-secrets.d"
  #   }
  #   "rahul-production-us" = {
  #     datadog_enabled        = true
  #     datadog_secret_name    = "projects/205542412214/secrets/prod_datadog_base"
  #     datadog_secret_version = "latest"
  #     env_secrets_config_dir = "/etc/env-secrets.d"
  #   }
  # }

  # Look up the settings for the current project.
  # current_env_settings = lookup(local.environment_settings, var.project_id, {})

  # # Determine final configuration values, allowing for per-application overrides.
  # # Precedence: App Variable > Environment Setting > Module Default.
  # final_datadog_enabled        = coalesce(var.datadog_enabled, lookup(local.current_env_settings, "datadog_enabled", null), true)
  # final_datadog_secret_name    = coalesce(var.datadog_secret_name, lookup(local.current_env_settings, "datadog_secret_name", null), null)
  # final_datadog_secret_version = coalesce(var.datadog_secret_version, lookup(local.current_env_settings, "datadog_secret_version", null), "latest")
  # final_env_secrets_config_dir = coalesce(var.env_secrets_config_dir, lookup(local.current_env_settings, "env_secrets_config_dir", null), "/etc/env-secrets.d")

  # Create a map of all environment variables from all containers for easy lookup.
  env_vars_map = merge([for c in var.containers : c.env_vars]...)

  # Determine the secrets mount path, prioritizing a user-defined environment variable.
  # secrets_mount_path = lookup(local.env_vars_map, "ENV_SECRETS_CONFIG_DIR", local.final_env_secrets_config_dir)

  # Conditionally construct the Datadog volume.
  # datadog_volume = local.final_datadog_enabled && local.final_datadog_secret_name != null ? [
  #   {
  #     name = "datadog-secret"
  #     secret = {
  #       secret = local.final_datadog_secret_name
  #       items = {
  #         path    = "00_datadog.json"
  #         version = local.final_datadog_secret_version
  #         mode    = null # Mode is not applicable here, but schema requires the key.
  #       }
  #     }
  #     # Set other volume types to null to match the object type in var.volumes.
  #     cloud_sql_instance = {}
  #     empty_dir          = null
  #     gcs                = {}
  #     nfs                = null
  #   }
  # ] : []
  # all_volumes = concat(var.volumes, local.datadog_volume)

  # Conditionally construct the Datadog volume mount.
  # datadog_volume_mount = local.final_datadog_enabled && local.final_datadog_secret_name != null ? [
  #   {
  #     name       = "datadog-secret"
  #     mount_path = "${local.secrets_mount_path}/00_datadog"
  #   }
  # ] : []

  # Create a new list of containers that includes the automatic Datadog volume mount.
  # containers_with_datadog = [
  #   for c in var.containers : {
  #     # Copy all original container attributes
  #     container_name       = c.container_name
  #     container_image      = c.container_image
  #     working_dir          = c.working_dir
  #     depends_on_container = c.depends_on_container
  #     container_args       = c.container_args
  #     container_command    = c.container_command
  #     env_vars = merge(
  #       {
  #         "ENVIRONMENT_PROVIDER" = "GCP",
  #         "GCP_PROJECT_ID"       = var.project_id
  #       },
  #       local.final_datadog_enabled ? { "DD_SERVICE" = coalesce(c.datadog_service_name, c.container_name, var.datadog_service_name, var.service_name) } : {},
  #       c.env_vars
  #     )
  #     env_secret_vars = c.env_secret_vars
  #     ports           = c.ports
  #     resources       = c.resources
  #     startup_probe   = c.startup_probe
  #     liveness_probe  = c.liveness_probe
  #     # Append the datadog mount to the existing mounts
  #     volume_mounts = concat(try(c.volume_mounts, []), local.datadog_volume_mount)
  #   }
  # ]

  # --- Original locals from the module ---
  service_account = (
    var.service_account != null
    ? var.service_account
    : (
      var.create_service_account
      ? google_service_account.sa[0].email
      : null
    )
  )
  create_service_account = var.create_service_account ? var.service_account == null : false

  service_account_prefix = substr("${var.service_name}-${var.location}", 0, 27)

  service_account_output = local.create_service_account ? {
    id     = google_service_account.sa[0].account_id,
    email  = google_service_account.sa[0].email,
    member = google_service_account.sa[0].member
    } : var.service_account == null ? {
    id     = data.google_compute_default_service_account.default[0].name,
    email  = data.google_compute_default_service_account.default[0].email,
    member = data.google_compute_default_service_account.default[0].member
    } : {
    id     = split("@", var.service_account)[0],
    email  = var.service_account,
    member = "serviceAccount:${var.service_account}"
  }

  service_account_project_roles = local.create_service_account ? distinct(concat(
    var.service_account_project_roles,
    var.enable_prometheus_sidecar ? ["roles/monitoring.metricWriter"] : []
  )) : []

  ingress_container = try(
    [for container in var.containers : container if length(try(container.ports, {})) > 0][0],
    null
  )
  prometheus_sidecar_container = [{
    container_name       = "collector"
    container_image      = "us-docker.pkg.dev/cloud-ops-agents-artifacts/cloud-run-gmp-sidecar/cloud-run-gmp-sidecar:1.1.1"
    ports                = {}
    working_dir          = null
    depends_on_container = try(local.ingress_container != null ? [local.ingress_container.container_name] : [], [])
    container_args       = null
    container_command    = null
    env_vars             = {}
    env_secret_vars      = {}
    volume_mounts        = []
    resources = {
      cpu_idle          = true
      startup_cpu_boost = false
      limits            = {}
    }
    startup_probe  = null
    liveness_probe = null
  }]
}

resource "google_service_account" "sa" {
  count        = local.create_service_account ? 1 : 0
  project      = var.project_id
  account_id   = "${local.service_account_prefix}-sa"
  display_name = "Service account for ${var.service_name} in ${var.location}"
}

resource "google_project_iam_member" "roles" {
  for_each = toset(local.service_account_project_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${local.service_account}"
}

resource "google_cloud_run_v2_service" "main" {
  provider = google-beta

  project              = var.project_id
  name                 = var.service_name
  location             = var.location
  description          = var.description
  labels               = var.service_labels
  invoker_iam_disabled = var.invoker_iam_disabled

  deletion_protection = var.cloud_run_deletion_protection
  lifecycle {
    ignore_changes = [
      conditions[0].message,
      template[0].containers[0].image,
      client,
    ]
  }

  template {
    revision        = var.revision
    labels          = var.template_labels
    annotations     = var.template_annotations
    timeout         = var.timeout
    service_account = local.service_account

    execution_environment            = var.execution_environment
    encryption_key                   = var.encryption_key
    max_instance_request_concurrency = var.max_instance_request_concurrency
    session_affinity                 = var.session_affinity

    dynamic "scaling" {
      for_each = var.template_scaling[*]
      content {
        min_instance_count = scaling.value.min_instance_count
        max_instance_count = scaling.value.max_instance_count
      }
    }

    dynamic "vpc_access" {
      for_each = var.vpc_access[*]
      content {
        connector = vpc_access.value.connector
        egress    = vpc_access.value.egress
        dynamic "network_interfaces" {
          for_each = vpc_access.value.network_interfaces[*]
          content {
            network    = network_interfaces.value.network
            subnetwork = network_interfaces.value.subnetwork
            tags       = network_interfaces.value.tags
          }
        }
      }
    }

    dynamic "containers" {
      for_each = var.enable_prometheus_sidecar ? local.prometheus_sidecar_container : []
      content {
        name        = containers.value.container_name
        image       = containers.value.container_image
        command     = containers.value.container_command
        args        = containers.value.container_args
        working_dir = containers.value.working_dir
        depends_on  = containers.value.depends_on_container
        # dynamic "ports" {
        #   for_each = lookup(containers.value, "ports", {}) != {} ? [containers.value.ports] : []
        #   content {
        #     name           = ports.value["name"]
        #     container_port = ports.value["container_port"]
        #   }
        # }

        dynamic "ports" {
          for_each = try(containers.value.ports.container_port, null) != null ? [1] : []

          content {
            name           = containers.value.ports.name
            container_port = containers.value.ports.container_port
          }
        }

        resources {
          limits            = containers.value.resources.limits
          cpu_idle          = containers.value.resources.cpu_idle
          startup_cpu_boost = containers.value.resources.startup_cpu_boost
        }

        dynamic "startup_probe" {
          for_each = containers.value.startup_probe == null ? [] : [containers.value.startup_probe]
          content {
            failure_threshold     = startup_probe.value.failure_threshold
            initial_delay_seconds = startup_probe.value.initial_delay_seconds
            timeout_seconds       = startup_probe.value.timeout_seconds
            period_seconds        = startup_probe.value.period_seconds

            dynamic "http_get" {
              for_each = startup_probe.value.http_get == null ? [] : [startup_probe.value.http_get]
              content {
                path = http_get.value.path
                port = http_get.value.port

                dynamic "http_headers" {
                  for_each = http_get.value.http_headers[*]
                  content {
                    name  = http_headers.value["name"]
                    value = http_headers.value["value"]
                  }
                }
              }
            }

            dynamic "tcp_socket" {
              for_each = startup_probe.value.tcp_socket == null ? [] : [startup_probe.value.tcp_socket]
              content {
                port = tcp_socket.value.port
              }
            }

            dynamic "grpc" {
              for_each = startup_probe.value.grpc == null ? [] : [startup_probe.value.grpc]
              content {
                port    = grpc.value.port
                service = grpc.value.service
              }
            }
          }
        }

        dynamic "liveness_probe" {
          for_each = containers.value.liveness_probe == null ? [] : [containers.value.liveness_probe]
          content {
            failure_threshold     = liveness_probe.value.failure_threshold
            initial_delay_seconds = liveness_probe.value.initial_delay_seconds
            timeout_seconds       = liveness_probe.value.timeout_seconds
            period_seconds        = liveness_probe.value.period_seconds

            dynamic "http_get" {
              for_each = liveness_probe.value.http_get == null ? [] : [liveness_probe.value.http_get]
              content {
                path = http_get.value.path
                port = http_get.value.port

                dynamic "http_headers" {
                  for_each = http_get.value.http_headers[*]
                  content {
                    name  = http_headers.value["name"]
                    value = http_headers.value["value"]
                  }
                }
              }
            }

            dynamic "tcp_socket" {
              for_each = liveness_probe.value.tcp_socket == null ? [] : [liveness_probe.value.tcp_socket]
              content {
                port = tcp_socket.value.port
              }
            }

            dynamic "grpc" {
              for_each = liveness_probe.value.grpc == null ? [] : [liveness_probe.value.grpc]
              content {
                port    = grpc.value.port
                service = grpc.value.service
              }
            }
          }
        }

        dynamic "env" {
          for_each = containers.value.env_vars
          content {
            name  = env.key
            value = env.value
          }
        }

        dynamic "env" {
          for_each = containers.value.env_secret_vars
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value.secret
                version = env.value.version
              }
            }
          }
        }

        dynamic "volume_mounts" {
          for_each = containers.value.volume_mounts
          content {
            name       = volume_mounts.value.name
            mount_path = volume_mounts.value.mount_path
          }
        }
      }
    } // containers

    dynamic "volumes" {
      for_each = var.volumes
      content {
        name = volumes.value.name

        dynamic "secret" {
          for_each = volumes.value.secret != null ? [volumes.value.secret] : []
          content {
            secret = secret.value.secret
            items {
              path    = secret.value.items.path
              version = secret.value.items.version
              # Safely access the optional 'mode' attribute.
              mode = try(secret.value.items.mode, null)
            }
          }
        }

        dynamic "cloud_sql_instance" {
          for_each = try(volumes.value.cloud_sql_instance.instances, null) != null ? [volumes.value.cloud_sql_instance] : []
          content {
            instances = cloud_sql_instance.value["instances"]
          }
        }
        dynamic "empty_dir" {
          for_each = volumes.value.empty_dir != null ? [volumes.value.empty_dir] : []
          content {
            medium     = empty_dir.value["medium"]
            size_limit = empty_dir.value["size_limit"]
          }
        }
        dynamic "gcs" {
          for_each = try(volumes.value.gcs.bucket, null) != null ? [volumes.value.gcs] : []
          content {
            bucket    = gcs.value["bucket"]
            read_only = gcs.value["read_only"]
          }
        }
        dynamic "nfs" {
          for_each = try(volumes.value.nfs.server, null) != null ? [volumes.value.nfs] : []
          content {
            server    = nfs.value["server"]
            path      = nfs.value["path"]
            read_only = nfs.value["read_only"]
          }
        }
      }
    }
  } // template

  annotations      = var.service_annotations
  client           = var.client.name
  client_version   = var.client.version
  ingress          = var.ingress
  launch_stage     = var.launch_stage
  custom_audiences = var.custom_audiences

  dynamic "binary_authorization" {
    for_each = var.binary_authorization[*]
    content {
      breakglass_justification = binary_authorization.value.breakglass_justification
      use_default              = binary_authorization.value.use_default
    }
  }

  dynamic "scaling" {
    for_each = var.service_scaling[*]
    content {
      min_instance_count    = scaling.value.min_instance_count
      max_instance_count    = scaling.value.max_instance_count
      scaling_mode          = scaling.value.scaling_mode
      manual_instance_count = scaling.value.manual_instance_count
    }
  }

  dynamic "traffic" {
    for_each = var.traffic
    content {
      percent  = traffic.value.percent
      type     = traffic.value.type
      revision = traffic.value.revision
      tag      = traffic.value.tag
    }
  }
  depends_on = [google_project_iam_member.roles]
}

resource "google_cloud_run_v2_service_iam_member" "authorize" {
  for_each = toset(var.members)
  location = google_cloud_run_v2_service.main.location
  project  = google_cloud_run_v2_service.main.project
  name     = google_cloud_run_v2_service.main.name
  role     = "roles/run.invoker"
  member   = each.value
}
