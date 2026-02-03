resource "google_storage_bucket" "bucket" {
  name                        = var.name
  project                     = var.project_id
  location                    = var.location
  storage_class               = var.storage_class
  uniform_bucket_level_access = var.bucket_policy_only
  public_access_prevention    = var.public_access_prevention
  labels                      = var.labels
  force_destroy               = var.force_destroy

  dynamic "custom_placement_config" {
    for_each = var.custom_placement_config == null ? [] : [var.custom_placement_config]
    content {
      data_locations = var.custom_placement_config.data_locations
    }
  }

  versioning {
    enabled = var.versioning
  }

  dynamic "retention_policy" {
    for_each = var.retention_policy == null ? [] : [var.retention_policy]
    content {
      is_locked        = var.retention_policy.is_locked
      retention_period = var.retention_policy.retention_period
    }
  }

  dynamic "encryption" {
    for_each = var.encryption == null ? [] : [var.encryption]
    content {
      default_kms_key_name = var.encryption.default_kms_key_name
    }
  }

  dynamic "cors" {
    for_each = var.cors == null ? [] : var.cors
    content {
      origin          = lookup(cors.value, "origin", null)
      method          = lookup(cors.value, "method", null)
      response_header = lookup(cors.value, "response_header", null)
      max_age_seconds = lookup(cors.value, "max_age_seconds", null)
    }
  }

  dynamic "soft_delete_policy" {
    for_each = var.soft_delete_policy == null ? [] : [var.soft_delete_policy]
    content {
      retention_duration_seconds = lookup(soft_delete_policy.value, "retention_duration_seconds", null)
    }
  }

  dynamic "lifecycle_rule" {
    for_each = var.lifecycle_rules
    content {
      action {
        type          = lifecycle_rule.value.action.type
        storage_class = lookup(lifecycle_rule.value.action, "storage_class", null)
      }
      condition {
        age                        = lookup(lifecycle_rule.value.condition, "age", null)
        send_age_if_zero           = lookup(lifecycle_rule.value.condition, "send_age_if_zero", null)
        created_before             = lookup(lifecycle_rule.value.condition, "created_before", null)
        with_state                 = lookup(lifecycle_rule.value.condition, "with_state", lookup(lifecycle_rule.value.condition, "is_live", false) ? "LIVE" : null)
        matches_storage_class      = lookup(lifecycle_rule.value.condition, "matches_storage_class", null)
        matches_prefix             = lookup(lifecycle_rule.value.condition, "matches_prefix", null)
        matches_suffix             = lookup(lifecycle_rule.value.condition, "matches_suffix", null)
        num_newer_versions         = lookup(lifecycle_rule.value.condition, "num_newer_versions", null)
        custom_time_before         = lookup(lifecycle_rule.value.condition, "custom_time_before", null)
        days_since_custom_time     = lookup(lifecycle_rule.value.condition, "days_since_custom_time", null)
        days_since_noncurrent_time = lookup(lifecycle_rule.value.condition, "days_since_noncurrent_time", null)
        noncurrent_time_before     = lookup(lifecycle_rule.value.condition, "noncurrent_time_before", null)
      }
    }
  }

  dynamic "logging" {
    for_each = var.log_bucket == null ? [] : [var.log_bucket]
    content {
      log_bucket        = var.log_bucket
      log_object_prefix = var.log_object_prefix
    }
  }

  dynamic "website" {
    for_each = var.website == null ? [] : [var.website]
    content {
      main_page_suffix = website.value.main_page_suffix
      not_found_page   = website.value.not_found_page
    }
  }
}

resource "google_storage_bucket_iam_member" "members" {
  for_each = {
    for m in var.iam_members : "${m.role} ${m.member}" => m
  }
  bucket     = google_storage_bucket.bucket.name
  role       = each.value.role
  member     = each.value.member
  depends_on = [google_tags_location_tag_binding.bucket_tag_bindings]
}

resource "google_compute_global_network_endpoint" "default-endpoint" {

  count                         = var.enable_neg ? 1 : 0
  project                       = var.project_id
  global_network_endpoint_group = google_compute_global_network_endpoint_group.neg[0].name
  fqdn                          = "${google_storage_bucket.bucket.name}.storage.googleapis.com"
  port                          = var.port
}

resource "google_compute_global_network_endpoint_group" "neg" {
  count                 = var.enable_neg ? 1 : 0
  project               = var.project_id
  name                  = "${google_storage_bucket.bucket.name}-backend-bucket"
  default_port          = var.neg_default_port
  network_endpoint_type = "INTERNET_FQDN_PORT"
}

resource "google_tags_location_tag_binding" "bucket_tag_bindings" {
  for_each = toset(var.tag_bindings)

  parent    = "//storage.googleapis.com/projects/_/buckets/${google_storage_bucket.bucket.name}"
  tag_value = each.value
  location  = var.location
}
