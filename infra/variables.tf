variable "project_id" {
  type        = string
  description = "Google Cloud Project ID"
}

variable "project_number" {
  type        = string
  description = "Google Cloud Project Number"
}

variable "billing_account" {
  type        = string
  description = "Billing Account ID"
}

variable "region" {
  type        = string
  default     = "us-central1"
}

variable "firestore_location" {
  type        = string
  default     = "nam5"
}

variable "budget_amount_usd" {
  type        = number
  default     = 100
}

variable "pro_model" {
  type        = string
  default     = "gemini-2.5-pro"
}

variable "flash_model" {
  type        = string
  default     = "gemini-2.5-flash"
}

variable "image_model" {
  type        = string
  default     = "imagen-3.0-generate-002"
}

variable "tts_model_en" {
  type        = string
  default     = "en-US-Chirp3-HD-Achernar"
}

variable "tts_model_fa" {
  type        = string
  default     = "fa-IR-Standard-A"
}

variable "stt_model" {
  type        = string
  default     = "chirp_2"
}

variable "enable_veo_clips" {
  type        = bool
  default     = false
}

variable "enable_lyria_music" {
  type        = bool
  default     = false
}
