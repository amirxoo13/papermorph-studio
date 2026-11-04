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

resource "google_firestore_index" "jobs_owner_created" {
  project    = var.project_id
  database   = google_firestore_database.default.name
  collection = "jobs"

  fields {
    field_path = "ownerUid"
    order      = "ASCENDING"
  }
  fields {
    field_path = "createdAt"
    order      = "DESCENDING"
  }
}

resource "google_firestore_index" "jobs_state_heartbeat" {
  project    = var.project_id
  database   = google_firestore_database.default.name
  collection = "jobs"

  fields {
    field_path = "state"
    order      = "ASCENDING"
  }
  fields {
    field_path = "updatedAt"
    order      = "ASCENDING"
  }
}

resource "google_firestore_index" "books_owner_published" {
  project    = var.project_id
  database   = google_firestore_database.default.name
  collection = "books"

  fields {
    field_path = "ownerUid"
    order      = "ASCENDING"
  }
  fields {
    field_path = "publishedAt"
    order      = "DESCENDING"
  }
}
