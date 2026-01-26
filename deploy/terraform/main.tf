terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 5.0.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0.0"
    }
  }
}

provider "oci" {
  tenancy_ocid        = var.tenancy_ocid
  region              = var.region
  config_file_profile = var.config_file_profile
}

resource "random_string" "deploy_id" {
  length  = 4
  special = false
  upper   = false
}

resource "random_password" "admin_password" {
  length           = 16
  special          = true
  override_special = "#_"
  min_upper        = 2
  min_lower        = 2
  min_numeric      = 2
  min_special      = 1
}
