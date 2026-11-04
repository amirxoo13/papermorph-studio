resource "google_storage_bucket" "raw_uploads" {
  name                        = "${var.project_id}-pm-raw-uploads"
  location                    = var.region
  project                     = var.project_id
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 14
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket" "work" {
  name                        = "${var.project_id}-pm-work"
  location                    = var.region
  project                     = var.project_id
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true

  versioning {
    enabled = true
  }

  autoclass {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket" "published" {
  name                        = "${var.project_id}-pm-published"
  location                    = var.region
  project                     = var.project_id
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true

  versioning {
    enabled = true
  }

  autoclass {
    enabled = true
  }
}
