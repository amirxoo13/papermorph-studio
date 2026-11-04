resource "google_bigquery_dataset" "analytics" {
  dataset_id                 = "papermorph_analytics"
  friendly_name              = "Papermorph Studio Cost & Stage Analytics"
  location                   = var.region
  project                    = var.project_id
  delete_contents_on_destroy = true
}
