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
# Using the shell script
./files/simulate_alert.sh eda.example.com

# Or using the Ansible playbook
ansible-playbook playbooks/demo/simulate_alert.yml \
  -e eda_webhook_host=eda.example.com
```

Both methods send an Alertmanager-compatible `ServiceDown` alert for
`httpd` on `webserver1.example.com`.

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
you can modify the alert to a different scenario. The **Reclaim Disk Space**
template should NOT be selected for a `ServiceDown` alert.

If you want to test disk alerts, modify `simulate_alert.sh` or the playbook:

```bash
./files/simulate_alert.sh eda.example.com 5000 disk webserver1.example.com warning
```

Note: this will still send a `ServiceDown` alert with the service name set
to `disk`. For a true disk alert, you would need to modify the alert payload
to use a `DiskSpaceLow` alertname.

## 8. Cleanup (optional)

To remove all demo objects from AAP:

```bash
ansible-playbook -e @vault.yml playbooks/aap_cleanup.yml --ask-vault-pass
```

You will be prompted to type `yes` to confirm the destructive operation.
