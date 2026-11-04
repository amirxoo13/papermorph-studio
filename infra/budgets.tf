resource "google_pubsub_topic" "budget_alerts" {
  name    = "papermorph-budget-alerts"
  project = var.project_id
}

resource "google_billing_budget" "studio_budget" {
  billing_account = var.billing_account
  display_name    = "papermorph-studio-budget-${var.project_id}"

  budget_filter {
    projects               = ["projects/${var.project_number}"]
    credit_types_treatment = "INCLUDE_ALL_CREDITS"
    calendar_period        = "MONTH"
  }

  amount {
    specified_amount {
      currency_code = "EUR"
      units         = tostring(var.budget_amount_usd)
    }
  }

  threshold_rules {
    threshold_percent = 0.25
    spend_basis       = "CURRENT_SPEND"
  }
  threshold_rules {
    threshold_percent = 0.50
    spend_basis       = "CURRENT_SPEND"
  }
  threshold_rules {
    threshold_percent = 0.75
    spend_basis       = "CURRENT_SPEND"
  }
  threshold_rules {
    threshold_percent = 0.90
    spend_basis       = "CURRENT_SPEND"
  }

  all_updates_rule {
    pubsub_topic   = google_pubsub_topic.budget_alerts.id
    schema_version = "1.0"
  }
}
