variable "tenancy_ocid" {
  description = "OCI Tenancy OCID"
  type        = string
}

variable "compartment_ocid" {
  description = "OCI Compartment OCID for ADB deployment"
  type        = string
}

variable "region" {
  description = "OCI Region"
  type        = string
}

variable "config_file_profile" {
  description = "OCI config file profile name"
  type        = string
  default     = "DEFAULT"
}

variable "ecpu_count" {
  description = "Number of ECPUs for ADB"
  type        = number
  default     = 2
}

variable "data_storage_size_in_gb" {
  description = "Data storage size in GB"
  type        = number
  default     = 20
}
