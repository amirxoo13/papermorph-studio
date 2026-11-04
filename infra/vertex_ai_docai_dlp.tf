resource "google_data_loss_prevention_inspect_template" "pii_scan" {
  parent       = "projects/${var.project_id}/locations/global"
  display_name = "Papermorph PII Inspect Template"
  description  = "Scans uploaded manuscripts for PII before indexing"

  inspect_config {
    info_types {
      name = "EMAIL_ADDRESS"
    }
    info_types {
      name = "PHONE_NUMBER"
    }
    info_types {
      name = "US_SOCIAL_SECURITY_NUMBER"
    }
    info_types {
      name = "CREDIT_CARD_NUMBER"
    }
    min_likelihood = "POSSIBLE"
  }
}
