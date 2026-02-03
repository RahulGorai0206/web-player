/**
 * Copyright 2023 Google LLC
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
resource "google_artifact_registry_repository" "my_repo" {
  location      = var.region_name
  project       = var.project_id
  repository_id = var.repo_id
  description   = var.description
  format        = var.format_type
  labels        = var.labels

  dynamic "docker_config" {
    for_each = var.immutable_tags == true ? [1] : []
    content {
      immutable_tags = var.immutable_tags
    }
  }
  dynamic "cleanup_policies" {
    for_each = var.cleanup_policies
    content {
      id     = cleanup_policies.key
      action = cleanup_policies.value.action

      dynamic "condition" {
        for_each = cleanup_policies.value.condition[*]
        content {
          tag_state             = condition.value.tag_state
          tag_prefixes          = condition.value.tag_prefixes
          older_than            = condition.value.older_than
          newer_than            = condition.value.newer_than
          version_name_prefixes = condition.value.version_name_prefixes
          package_name_prefixes = condition.value.package_name_prefixes
        }
      }

      dynamic "most_recent_versions" {
        for_each = cleanup_policies.value.most_recent_versions[*]
        content {
          keep_count            = most_recent_versions.value.keep_count
          package_name_prefixes = most_recent_versions.value.package_name_prefixes
        }
      }
    }
  }
}