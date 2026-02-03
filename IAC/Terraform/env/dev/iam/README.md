# Project IAM Service Account Module

This module makes it easy to create custom roles and Perform role bindings for IAM Service Accounts.

- Custom roles
- IAM Service Accounts
- Role bindings for IAM Service Accounts

## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.6.1 |
| <a name="requirement_google"></a> [google](#requirement\_google) | ~> 3.0 |

## Providers

| Name | Version |
|------|---------|
| google | ~> 3.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_cloud_dns"></a> [custom_role_gke](#module\_cloud_dns_) | ../../../../../modules/iam/custom-role | n/a |
| <a name="module_cloud_dns"></a> [service_account_gke](#module\_cloud_dns_) | ../../../../../modules/iam/ | n/a |
| <a name="module_cloud_dns"></a> [member_roles_gke](#module\_cloud_dns_) | ../../../../../modules/iam/member-iam | n/a |



## Permissions

In order to execute this module you must have a Service Account with the
following project roles:

- [roles/iam.serviceAccountAdmin](https://cloud.google.com/iam/docs/understanding-roles)

## Enable APIs

In order to operate with the Service Account you must activate the following APIs on the project where the Service Account was created:

- IAM API: iam.googleapis.com


## Usage
Basic usage of this module is as follows:

* Custom roles

```hcl
module "custom_role_gke" {
  source      = "../../../../../modules/iam/custom-role"
  project     = var.service_project_id
  role_id     = var.service_account_gke["role_name"]
  permissions = var.service_account_gke["permissions"]
}
```

* Service Accounts

```hcl
module "service_account_gke" {
  source               = "../../../../../modules/iam/service-account-new"
  project_id           = var.service_project_id
  service_account_name = var.service_account_gke["service_account"]
}
```

* IAM members and role bindings

```hcl
module "member_roles_gke" {
  source                  = "../../../../../modules/iam/member-iam"
  service_account_address = module.service_account_gke.email
  project                 = var.service_project_id
  project_roles           = ["projects/${var.service_project_id}/roles/${var.service_account_gke["role_name"]}", "roles/secretmanager.secretAccessor", ]
}
```

* Provide the variables values to the modules from terraform.tfvars file.

```hcl
project_id = "project_id"
region     = "region name"

service_account_gke = {
  service_account = "service_account name"
  role_name       = "role name"
  permissions = [
  "permission name",
  ]
}
service_account_mgmt_gce = {
  service_account = "service_account name"
  role_name       = "role name"
  permissions = [
    "permission name",
  ]
}
service_account_tf_sa = {
  service_account = "service_account name"
  role_name       = "role name"
  permissions = [
    "permission name",
  ]
}
service_account_data_cloudfunc_sa = {
  service_account = "service_account name"
  role_name       = "role name"
  permissions = [
    "permission name",
  ]
}

```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_project_id"></a> [project\_id](#input\_project\_id) | The GCP project ID | `any` | n/a | yes |
| <a name="input_region"></a> [region](#input\_region) | The GCP region of the deployment. | `any` | n/a | yes |
| <a name="input_service_account_gke"></a> [service\_account\_gke](#input\_service\_account\_gke) | service Account to add the IAM policies/bindings for GKE | `any` | n/a | yes |
| <a name="input_service_account_mgmt_gce"></a> [service\_account\_mgmt\_gce](#input\_service\_account\_mgmt\_gce) | service Account to add the IAM policies/bindings for management VM | `any` | n/a | yes |
| <a name="input_service_account_mgmt_gce"></a> [service_account_tf_sa](#input\_service\_account\_mgmt\_gce) | service Account to add the IAM policies/bindings for deployment via terraform | `any` | n/a | yes |
| <a name="input_service_account_mgmt_gce"></a> [service_account_data_cloudfunc_sa](#input\_service\_account\_mgmt\_gce) | service Account to add the IAM policies/bindings for cloud functions| `any` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_custom_role_gke"></a> [custom\_role\_gke](#output\_custom\_role\_gke) | Custom Role name used for gke  |
| <a name="output_custom_role_mgmt_gce"></a> [custom\_role\_mgmt\_gce](#output\_custom\_role\_mgmt\_gce) | Custom Role name used for management VM |
| <a name="output_service_account_gke_email"></a> [service\_account\_gke\_email](#output\_service\_account\_gke\_email) | Service account emails of gke|
| <a name="output_service_account_mgmt_gce_email"></a> [service\_account\_mgmt\_gce\_email](#output\_service\_account\_mgmt\_gce\_email) | Service account emails of management VM |


* Then perform the following commands in the directory:

   `terraform init` to get the plugins

   `terraform plan` to see the infrastructure plan

   `terraform apply` to apply the infrastructure build

   `terraform destroy` to destroy the built infrastructure