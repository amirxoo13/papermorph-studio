resource "google_firestore_database" "default" {
  project                     = var.project_id
  name                        = "(default)"
  location_id                 = var.firestore_location
  type                        = "FIRESTORE_NATIVE"
  delete_protection_state     = "DELETE_PROTECTION_DISABLED"
  deletion_policy             = "ABANDON"
}

resource "google_firestore_field" "events_ttl" {
  project    = var.project_id
  database   = google_firestore_database.default.name
  collection = "events"
  field      = "expireAt"

  ttl_config {}
}
