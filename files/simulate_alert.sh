#!/usr/bin/env bash
# Simulate a Prometheus / Alertmanager webhook to the EDA Controller.
# This replaces a real Prometheus + Alertmanager stack for demo purposes.
#
# Usage:
#   ./simulate_alert.sh <eda-host> [port] [service] [target-host] [severity]
#
# Examples:
#   ./simulate_alert.sh eda.example.com
#   ./simulate_alert.sh eda.example.com 5000 httpd webserver1.example.com critical
#   ./simulate_alert.sh eda.example.com 5000 nginx web2.example.com warning

set -euo pipefail

EDA_HOST="${1:?Usage: $0 <eda-host> [port] [service] [target-host] [severity]}"
EDA_PORT="${2:-5000}"
SERVICE="${3:-httpd}"
TARGET_HOST="${4:-webserver1.example.com}"
SEVERITY="${5:-critical}"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

PAYLOAD=$(cat <<EOF
{
  "status": "firing",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "ServiceDown",
        "instance": "${TARGET_HOST}:9090",
        "job": "node",
        "service": "${SERVICE}",
        "severity": "${SEVERITY}"
      },
      "annotations": {
        "summary": "${SERVICE} service is down on ${TARGET_HOST}",
        "description": "The ${SERVICE} service has been down for more than 2 minutes."
      },
      "startsAt": "${TIMESTAMP}",
      "generatorURL": "http://prometheus:9090/graph"
    }
  ]
}
EOF
)

echo "Sending ServiceDown alert to EDA at http://${EDA_HOST}:${EDA_PORT}..."
echo "  Service:  ${SERVICE}"
echo "  Target:   ${TARGET_HOST}"
echo "  Severity: ${SEVERITY}"
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
