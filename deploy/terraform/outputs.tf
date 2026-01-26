output "adb_ocid" {
  value       = oci_database_autonomous_database.hr_adb.id
  description = "OCID of the Autonomous Database"
}

output "db_name" {
  value       = oci_database_autonomous_database.hr_adb.db_name
  description = "Database name"
}

output "connection_strings" {
  value       = oci_database_autonomous_database.hr_adb.connection_strings[0].profiles
  description = "Connection profiles"
  sensitive   = true
}

output "admin_password" {
  value       = random_password.admin_password.result
  description = "Admin password for the database"
  sensitive   = true
}

output "wallet_password" {
  value       = random_password.wallet_password.result
  description = "Wallet password"
  sensitive   = true
}

output "tns_alias_low" {
  value       = "${lower(oci_database_autonomous_database.hr_adb.db_name)}_low"
  description = "TNS alias for low priority connections"
}
