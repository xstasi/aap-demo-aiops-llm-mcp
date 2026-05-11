# Step-by-Step Procedures

This document walks through the full demo lifecycle: setup, execution,
and observation of the AI-driven remediation flow.

## 1. Apply AAP Configuration as Code

This creates all Controller and EDA objects (organization, credentials,
project, inventory, job templates, execution environment, EDA project,
and rulebook activation):

```bash
ansible-playbook -e @vault.yml playbooks/aap_config.yml --ask-vault-pass
```

## 2. Build and push the custom Execution Environment

The AI Triage job template requires a custom EE with Python packages for
LLM clients and MCP. See [custom-ee.md](custom-ee.md) for the full build
procedure.

```bash
cd context/
./build.sh registry.example.com/aiops-triage-ee:latest
podman push registry.example.com/aiops-triage-ee:latest
cd ..
```

## 3. Verify AAP objects

Confirm that all objects were created correctly:

```bash
ansible-playbook -e @vault.yml playbooks/verify.yml --ask-vault-pass
```

See [verification.md](verification.md) for expected output and manual checks.

## 4. Enable the EDA rulebook activation

In the EDA Controller UI:

1. Navigate to **Rulebook Activations**.
2. Locate **Prometheus Alert Monitor**.
3. Ensure it is **Enabled** (CasC should have enabled it, but verify).
4. Confirm the status shows **Running**.

## 5. Simulate a Prometheus alert

From any host that can reach the EDA Controller's webhook port (5000):

```bash
# Minimal invocation: ServiceDown for httpd on webserver1.example.com
./files/simulate_alert.sh eda.example.com

# Or using the Ansible playbook wrapper
ansible-playbook playbooks/demo/simulate_alert.yml \
  -e eda_webhook_host=eda.example.com
```

The script accepts three alert types via the third positional argument
(`service_down` is the default):

| Type | Description | Example |
|---|---|---|
| `service_down` | Service outage (`ServiceDown` alertname) | `./files/simulate_alert.sh eda.example.com 5000 service_down webserver1.example.com critical nginx` |
| `disk_full` | Filesystem exhaustion (`DiskFull` alertname) | `./files/simulate_alert.sh eda.example.com 5000 disk_full dbserver.example.com critical /var` |
| `custom` | Arbitrary alert with a free-text summary | `./files/simulate_alert.sh eda.example.com 5000 custom app1.example.com warning "Swap above 90%" HighSwap` |

Full argument reference:

```
./files/simulate_alert.sh <eda-host> [port] [type] [target-host] [severity] [detail] [alert-name]
```

For the `custom` type, the optional seventh argument overrides the
`alertname` label (default: `CustomAlert`).

## 6. Observe the remediation chain

After the alert fires, the following chain executes automatically:

1. **EDA** receives the webhook and triggers the **AI Triage** job template.
2. **AI Triage** runs the triage script inside the custom EE.
3. The triage script connects to the **AAP MCP server** to discover templates.
4. The **LLM** (Ollama or Claude) analyzes the alert and selects
   **Restart Web Service**.
5. The triage script (or Claude via MCP) **launches** the selected template.
6. **Restart Web Service** runs on the target host, restarts `httpd`, and
   verifies the health check.

### What to check in the AAP Controller UI

- **Jobs** page: you should see two jobs in sequence:
  1. `AI Triage` -- the LLM analysis and MCP dispatch
  2. `Restart Web Service` -- the actual remediation

- Open the **AI Triage** job output to see the triage decision:
  - `selected_template`: should be `Restart Web Service`
  - `reasoning`: explanation of why this template was chosen
  - `job_id`: the ID of the launched remediation job

- Open the **Restart Web Service** job output to confirm:
  - `httpd` was restarted
  - Port 80 health check passed

## 7. Test the decoy template

To prove the LLM reasons about the alert rather than picking arbitrarily,
trigger a `DiskFull` alert. The **Reclaim Disk Space** template should be
selected instead of **Restart Web Service**:

```bash
./files/simulate_alert.sh eda.example.com 5000 disk_full webserver1.example.com warning /var
```

This sends a proper `DiskFull` alertname with a `mountpoint` label. Observe
the **AI Triage** job output and confirm:

- `selected_template` is now `Reclaim Disk Space` (not `Restart Web Service`)
- `reasoning` references the filesystem / disk usage context from the alert

For the inverse check, re-run the default `ServiceDown` alert and confirm
the LLM switches back to **Restart Web Service**:

```bash
./files/simulate_alert.sh eda.example.com
```

## 8. Cleanup (optional)

To remove all demo objects from AAP:

```bash
ansible-playbook -e @vault.yml playbooks/aap_cleanup.yml --ask-vault-pass
```

You will be prompted to type `yes` to confirm the destructive operation.
