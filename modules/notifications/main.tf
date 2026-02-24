resource "google_pubsub_topic" "drift_alerts" {
  name = "model-drift-alerts"
}

resource "google_pubsub_topic" "commentary_ready" {
  name = "commentary-ready"
  # Fired when new commentary is generated for a city
  # Cloudflare Workers subscribe to trigger ISR rebuild
}

resource "google_pubsub_topic" "subscriber_notifications" {
  name = "subscriber-notifications"
  # Fired when drift exceeds threshold
  # Triggers email/push notification pipeline
}
