resource "google_secret_manager_secret" "internal_hmac" {
  secret_id = "papermorph-internal-hmac"
  project   = var.project_id

  replication {
    auto {}
  }
}
