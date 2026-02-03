# Cloud Storage Module

This module makes it easy to create a GCS bucket, and assign basic permissions on it to arbitrary users.

The resources/services/activations/deletions that this module will create are:

- One GCS bucket

## Compatibility
This module is meant for use with Terraform 0.13+ and tested using Terraform 1.0+. If you find incompatibilities using Terraform >=0.13, please open an issue.
 If you haven't
[upgraded](https://www.terraform.io/upgrade-guides/0-13.html)

## Usage

Basic usage of this module is as follows:

```
module "gcs" {
  source           = "../../../../modules/cloud-storage"
  project_id       = var.service_project_id
  location         = var.region
  count            = length(var.gcs_buckets)
  name             = var.gcs_buckets[count.index].name
  retention_policy = var.gcs_buckets[count.index].retention_policy
  encryption       = var.gcs_buckets[count.index].encryption
  lifecycle_rule   = var.gcs_buckets[count.index].lifecycle_rule
  versioning       = var.gcs_buckets[count.index].versioning
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| gcs\_buckets | The details of the Cloud Storage Buckets. | <pre>list(object({<br>    name = string,<br>    retention_policy = object({<br>      is_locked        = bool<br>      retention_period = number<br>    })<br>    encryption = object({<br>      default_kms_key_name = string<br>    })<br>    lifecycle_rule = object({<br>      action = object({<br>        type          = string<br>        storage_class = string<br>      })<br>      condition = object({<br>        age                        = number<br>        created_before             = string<br>        with_state                 = string<br>        matches_storage_class      = list(string)<br>        num_newer_versions         = number<br>        custom_time_before         = string<br>        days_since_custom_time     = number<br>        days_since_noncurrent_time = number<br>        noncurrent_time_before     = string<br>      })<br>    })<br>    versioning = bool<br>  }))</pre> | <pre>[{<br>    encryption       = null<br>    name             = ""<br>    retention_policy = null<br>    lifecycle_rule   = null<br>    versioning       = true<br>  }]</pre> | yes |

## Outputs

| Name | Description |
|------|-------------|
| gcs_buckets | The created storage buckets. | 

## Permissions

In order to execute this module you must have a Service Account with the following permissions and roles:

- `roles/storage.admin`

## APIs

In order to operate this module, you must activate the following APIs on
the project:

- Cloud Storage API - `storage.googleapis.com`

## Terraform plugins

- [Terraform](https://www.terraform.io/downloads.html) >= 0.13
- [terraform-provider-google](https://github.com/terraform-providers/terraform-provider-google) plugin >= 3.53, < 5.0

### The Terraform resources will consists of following structure
```
├── README.md                 // Description of the module and what it should be used for.
├── main.tf                   // The primary entrypoint for terraform resources.
├── variables.tf              // It contains the declarations for variables.
├── outputs.tf                // It contains the declarations for outputs.
├── providers.tf              // To specify infrastructure vendors.
├── versions.tf               // To specify terraform versions.
├── backend.tf                // To create terraform backend state configuration.
├── terraform.tfvars   // The file to pass the terraform variables values.
```
