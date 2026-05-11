#!/usr/bin/env bash
# Simulate a Prometheus / Alertmanager webhook to the EDA Controller.
# This replaces a real Prometheus + Alertmanager stack for demo purposes.
#
# Usage:
#   ./simulate_alert.sh <eda-host> [port] [type] [target-host] [severity] [detail]
#
# Arguments:
#   eda-host    Hostname or IP of the EDA Controller
#   port        Webhook listener port (default: 5000)
#   type        Alert type: service_down | disk_full | custom  (default: service_down)
#   target-host Host label in the alert (default: webserver1.example.com)
#   severity    Alert severity label (default: critical)
#   detail      Type-specific extra value:
#                 service_down  -> service name        (default: httpd)
#                 disk_full     -> mount point         (default: /)
#                 custom        -> free-text summary   (default: "Custom alert fired")
#
# Custom alert name:
#   For the 'custom' type a seventh argument sets the alertname label
#   (default: CustomAlert).
#
# Examples:
#   ./simulate_alert.sh eda.example.com
#   ./simulate_alert.sh eda.example.com 5000 service_down webserver1.example.com critical nginx
#   ./simulate_alert.sh eda.example.com 5000 disk_full   dbserver.example.com    critical /var
#   ./simulate_alert.sh eda.example.com 5000 custom      app1.example.com        warning  "Swap usage above 90%" HighSwap

set -euo pipefail

EDA_HOST="${1:?Usage: $0 <eda-host> [port] [type] [target-host] [severity] [detail] [alert-name]}"
EDA_PORT="${2:-5000}"
TYPE="${3:-service_down}"
TARGET_HOST="${4:-webserver1.example.com}"
SEVERITY="${5:-critical}"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ---------------------------------------------------------------------------
# Build alert payload based on type
# ---------------------------------------------------------------------------
case "${TYPE}" in

  service_down)
    SERVICE="${6:-httpd}"
    ALERT_NAME="ServiceDown"
    SUMMARY="${SERVICE} service is down on ${TARGET_HOST}"
    DESCRIPTION="The ${SERVICE} service has been down for more than 2 minutes."
    EXTRA_LABEL="\"service\": \"${SERVICE}\","
    ;;

  disk_full)
    MOUNT="${6:-/}"
    ALERT_NAME="DiskFull"
    SUMMARY="Disk space critically low on ${TARGET_HOST} (${MOUNT})"
    DESCRIPTION="Filesystem ${MOUNT} on ${TARGET_HOST} is above the usage threshold."
    EXTRA_LABEL="\"mountpoint\": \"${MOUNT}\","
    ;;

  custom)
    CUSTOM_SUMMARY="${6:-Custom alert fired}"
    ALERT_NAME="${7:-CustomAlert}"
    SUMMARY="${CUSTOM_SUMMARY}"
    DESCRIPTION="${CUSTOM_SUMMARY} — triggered manually via simulate_alert.sh."
    EXTRA_LABEL=""
    ;;

  *)
    echo "ERROR: Unknown alert type '${TYPE}'. Valid values: service_down, disk_full, custom." >&2
    exit 1
    ;;
esac

PAYLOAD=$(cat <<EOF
{
  "status": "firing",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "${ALERT_NAME}",
        "instance": "${TARGET_HOST}:9090",
        "job": "node",
        ${EXTRA_LABEL}
        "severity": "${SEVERITY}"
      },
      "annotations": {
        "summary": "${SUMMARY}",
        "description": "${DESCRIPTION}"
      },
      "startsAt": "${TIMESTAMP}",
      "generatorURL": "http://prometheus:9090/graph"
    }
  ]
}
EOF
)

echo "Sending ${ALERT_NAME} alert to EDA at http://${EDA_HOST}:${EDA_PORT}..."
echo "  Type:     ${TYPE}"
echo "  Target:   ${TARGET_HOST}"
echo "  Severity: ${SEVERITY}"
echo "  Summary:  ${SUMMARY}"
echo ""

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}" \
  "http://${EDA_HOST}:${EDA_PORT}/alerts")

if [[ "${HTTP_CODE}" =~ ^2[0-9]{2}$ ]]; then
  echo "Alert sent successfully (HTTP ${HTTP_CODE})."
  echo "Check AAP Controller for the AI Triage job."
else
  echo "ERROR: EDA responded with HTTP ${HTTP_CODE}." >&2
  exit 1
fi
