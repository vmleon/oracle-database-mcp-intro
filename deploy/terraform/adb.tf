resource "oci_database_autonomous_database" "hr_adb" {
  compartment_id              = var.compartment_ocid
  db_name                     = "HRMCP${upper(random_string.deploy_id.result)}"
  display_name                = "hr-mcp-${random_string.deploy_id.result}"
  admin_password              = random_password.admin_password.result
  compute_model               = "ECPU"
  compute_count               = var.ecpu_count
  data_storage_size_in_gb     = var.data_storage_size_in_gb
  db_workload                 = "OLTP"
  is_free_tier                = false
  license_model               = "LICENSE_INCLUDED"
  db_version                  = "23ai"
  is_auto_scaling_enabled     = false
  is_mtls_connection_required = true

  lifecycle {
    ignore_changes = [admin_password]
  }
}
