output "raw_uploads_bucket" {
  value = google_storage_bucket.raw_uploads.name
}

output "work_bucket" {
  value = google_storage_bucket.work.name
}

output "published_bucket" {
  value = google_storage_bucket.published.name
}

output "bigquery_dataset" {
  value = google_bigquery_dataset.analytics.dataset_id
}
