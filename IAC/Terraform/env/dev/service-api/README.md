# Network Project

This module allows creation of resources for Network Project.

## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.6.1 |
| <a name="requirement_google"></a> [google](#requirement\_google) |  >= 6.37.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_google"></a> [google](#provider\_google) | 4.84.0 |
| <a name="provider_google.impersonator"></a> [google.impersonator](#provider\_google.impersonator) | 4.84.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_artifact_registry"></a> [artifact\_registry](#module\_artifact\_registry) | ../modules/artifact-registry/ | n/a |
| <a name="module_custom_role_terraform_seed"></a> [custom\_role\_terraform\_seed](#module\_custom\_role\_terraform\_seed) | ../modules/terraform-google-iam/custom-role | n/a |
| <a name="module_firewall_rules"></a> [firewall\_rules](#module\_firewall\_rules) | ../modules/firewall-rules | n/a |
| <a name="module_iam-binding"></a> [iam-binding](#module\_iam-binding) | ../modules/terraform-google-iam/projects-iam | n/a |
| <a name="module_member_roles_terraform_seed"></a> [member\_roles\_terraform\_seed](#module\_member\_roles\_terraform\_seed) | ../modules/terraform-google-iam/member-iam | n/a |
| <a name="module_project_services_api"></a> [project\_services\_api](#module\_project\_services\_api) | ../modules/service-api | n/a |
| <a name="module_serverless_vpc_access"></a> [serverless\_vpc\_access](#module\_serverless\_vpc\_access) | ../modules/serverless-vpc-access | n/a |
| <a name="module_svc_project_networking"></a> [svc\_project\_networking](#module\_svc\_project\_networking) | ../modules/shared-vpc | n/a |

## Resources

| Name | Type |
|------|------|
| [google_compute_shared_vpc_host_project.host](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_shared_vpc_host_project) | resource |
| [google_compute_shared_vpc_service_project.service_project](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_shared_vpc_service_project) | resource |
| [google_service_account_access_token.impersonated](https://registry.terraform.io/providers/hashicorp/google/latest/docs/data-sources/service_account_access_token) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_ar_labels"></a> [ar\_labels](#input\_ar\_labels) | A set of key/value label pairs to assign to the artifact registry | `map(string)` | `null` | no |
| <a name="input_project_id"></a> [base\_project\_id](#input\_base\_project\_id) | Existing Base project | `string` | n/a | yes |
| <a name="input_description"></a> [description](#input\_description) | A set of key/value label pairs to assign to the artifact registry | `string` | `"For Docker Images"` | no |
| <a name="input_firewall_rules"></a> [firewall\_rules](#input\_firewall\_rules) | n/a | <pre>map(<br>    object(<br>      {<br>        network_name = string<br>        rules = list(<br>          object(<br>            {<br>              name                    = string<br>              description             = string<br>              direction               = string<br>              priority                = number<br>              ranges                  = list(string)<br>              source_tags             = list(string)<br>              source_service_accounts = list(string)<br>              target_tags             = list(string)<br>              target_service_accounts = list(string)<br>              allow = list(object({<br>                protocol = string<br>                ports    = list(string)<br>              }))<br>              deny = list(object({<br>                protocol = string<br>                # ports    = list(string)<br>              }))<br>              log_config = object({<br>                metadata = string<br>              })<br>            }<br>          )<br>        )<br>      }<br>    )<br>  )</pre> | `{}` | no |
| <a name="input_format"></a> [format](#input\_format) | Name of the Format for deployment | `string` | n/a | yes |
| <a name="input_host_project_id"></a> [host\_project\_id](#input\_host\_project\_id) | Host Project ID. | `string` | n/a | yes |
| <a name="input_iam_bindings_config"></a> [iam\_bindings\_config](#input\_iam\_bindings\_config) | n/a | `map` | `{}` | no |
| <a name="input_project_services_api"></a> [project\_services\_api](#input\_project\_services\_api) | n/a | <pre>map(<br>    object(<br>      {<br>        project_id                 = string<br>        activate_apis              = list(string)<br>        disable_dependent_services = bool<br>      }<br>    )<br>  )</pre> | `{}` | no |
| <a name="input_region"></a> [region](#input\_region) | The region to create the project in. | `string` | n/a | yes |
| <a name="input_repo"></a> [repo](#input\_repo) | Name of the Repository for deployment | `string` | n/a | yes |
| <a name="input_serverless_vpc_access_config"></a> [serverless\_vpc\_access\_config](#input\_serverless\_vpc\_access\_config) | n/a | `map` | `{}` | no |
| <a name="input_service_account_terraform_seed"></a> [service\_account\_terraform\_seed](#input\_service\_account\_terraform\_seed) | Seed Terraform Resource Deployment Service Account to add the IAM policies/bindings | `any` | n/a | yes |
| <a name="input_service_project_ids"></a> [service\_project\_ids](#input\_service\_project\_ids) | List of Service Project IDs | `list(string)` | n/a | yes |
| <a name="input_svc_project_networking"></a> [svc\_project\_networking](#input\_svc\_project\_networking) | The GKE cluster name, node pool  and metadata list for the Service project's GKE. | <pre>map(object({<br>    network_name                     = string<br>    routing_mode                     = string<br>    pvt_svc_access_name              = string<br>    pvt_svc_access_address_range     = string<br>    pvt_svc_access_prefix_length     = string<br>    min_ports_per_vm                 = string<br>    icmp_idle_timeout_sec            = string<br>    tcp_established_idle_timeout_sec = string<br>    tcp_transitory_idle_timeout_sec  = string<br>    udp_idle_timeout_sec             = string<br>    subnets                          = list(map(string))<br>    secondary_ranges                 = map(list(object({ range_name = string, ip_cidr_range = string })))<br>  }))</pre> | n/a | yes |
| <a name="input_terraform_owner_email"></a> [terraform\_owner\_email](#input\_terraform\_owner\_email) | Email of the service account that will be used to create the project. | `string` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_artifact_registry_details"></a> [artifact\_registry\_details](#output\_artifact\_registry\_details) | The details of the Artifactory Registry |
| <a name="output_custom_role_terraform_seed"></a> [custom\_role\_terraform\_seed](#output\_custom\_role\_terraform\_seed) | The details of the Custom Role attached with Terraform Seed Service Account |
| <a name="output_firewall_rules_details"></a> [firewall\_rules\_details](#output\_firewall\_rules\_details) | The details of the Firewall Rules of Service Project |
| <a name="output_google_compute_shared_vpc_host_project_details"></a> [google\_compute\_shared\_vpc\_host\_project\_details](#output\_google\_compute\_shared\_vpc\_host\_project\_details) | The details of the host project provides network resources to associated service projects |
| <a name="output_google_compute_shared_vpc_service_projec_details"></a> [google\_compute\_shared\_vpc\_service\_projec\_details](#output\_google\_compute\_shared\_vpc\_service\_projec\_details) | The details of theservice project gains access to network resources provided by its associated host project |
| <a name="output_iam-binding_details"></a> [iam-binding\_details](#output\_iam-binding\_details) | The details of the IAM Binding for Network User role to Service Projects SA |
| <a name="output_member_roles_terraform_seed"></a> [member\_roles\_terraform\_seed](#output\_member\_roles\_terraform\_seed) | The details of the Terraform Seed Service Account with which the Customer Role has been bound |
| <a name="output_project_services_api_details"></a> [project\_services\_api\_details](#output\_project\_services\_api\_details) | The details of the APIs enabled in Project |
| <a name="output_serverless_vpc_access_details"></a> [serverless\_vpc\_access\_details](#output\_serverless\_vpc\_access\_details) | The details of the Serverless VPC Access of Service Project |
| <a name="output_svc_project_networking_details"></a> [svc\_project\_networking\_details](#output\_svc\_project\_networking\_details) | The details of the VPC, Subnets, PrivateServiceAccess and Cloud NAT of Service Project |

Then perform the following commands on the root folder:

- `terraform init` to get the plugins
- `terraform plan` to see the infrastructure plan
- `terraform apply` to apply the infrastructure build
- `terraform destroy` to destroy the built infrastructure

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