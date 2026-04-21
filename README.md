# AIOps: LLM-Driven Remediation via MCP

![AAP 2.5+](https://img.shields.io/badge/AAP-2.5%2B-red)
![CasC](https://img.shields.io/badge/CasC-infra.aap__configuration-blue)
![EDA](https://img.shields.io/badge/EDA-Event--Driven%20Ansible-orange)
![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-green)

## Introduction

This proof of concept demonstrates **AI-driven incident remediation** using
Red Hat Ansible Automation Platform (AAP). When a monitoring alert fires,
Event-Driven Ansible (EDA) triggers a triage job where a Large Language Model
(LLM) analyzes the alert, discovers available remediation templates via the
Model Context Protocol (MCP), and launches the best match -- all without
hardcoded alert-to-template mappings.

The demo supports two LLM backends:

- **Ollama** -- fully on-premise, script-side MCP client, no cloud dependency.
- **Anthropic Claude** -- cloud API with provider-native MCP connector.

**Target audience**: infrastructure teams evaluating AI-augmented operations,
Red Hat partners demonstrating AAP + AI integration, and anyone exploring
MCP as an integration protocol between AI and existing automation tooling.

---

## How to Run the Demo

| Phase | Action | Command / Tool |
|---|---|---|
| 1 | Apply AAP Configuration as Code | `ansible-playbook -e @vault.yml playbooks/aap_config.yml` |
| 2 | Build and push the custom EE | `cd context/ && ./build.sh` |
| 3 | Verify AAP objects | `ansible-playbook -e @vault.yml playbooks/verify.yml` |
| 4 | Enable EDA rulebook activation | EDA Controller UI |
| 5 | Simulate a Prometheus alert | `./files/simulate_alert.sh eda.example.com` |
| 6 | Observe AI Triage + Remediation | AAP Controller UI -- Jobs page |

See [docs/procedures.md](docs/procedures.md) for the full step-by-step walkthrough.

---

## Scenario Overview

### The problem

A RHEL web server running `httpd` goes down. Traditional alert-to-runbook
mappings require maintaining a growing matrix of alert rules and templates.
Adding new services or failure modes means updating EDA rulebooks every time.

### The AIOps approach

Instead of hardcoded mappings, a single EDA rule forwards every firing alert
to an AI triage job. The LLM analyzes the alert payload, discovers available
remediation templates via MCP, and selects the appropriate one. Adding new
remediation capabilities is as simple as creating a new job template with a
descriptive name -- no EDA changes required.

### Demo use case

1. Prometheus detects that `httpd` is down on `webserver1.example.com`.
2. Alertmanager sends a webhook to EDA.
3. EDA triggers the **AI Triage** job template.
4. The LLM discovers two templates: **Restart Web Service** and **Reclaim Disk Space**.
5. The LLM correctly selects **Restart Web Service** (not the decoy disk template).
6. The selected template runs, restarts `httpd`, and verifies recovery.

---

## Architecture

```
Prometheus / simulate_alert.sh
        |
        | Alertmanager webhook (POST)
        v
+-------------------+
| EDA Controller    |  Listens on :5000
| (rulebook)        |  Single generic rule: forward all firing alerts
+-------------------+
        |
        | run_job_template: AI Triage
        v
+-------------------+
| AAP Controller    |
| AI Triage JT      |  Custom EE with LLM + MCP packages
+-------------------+
        |
        | Triage script runs inside custom EE
        |
   +----+----+
   |         |
   v         v
+--------+ +--------+
| Ollama | | Claude |  (choose one backend)
| (local)| | (API)  |
+--------+ +--------+
   |         |
   |         |  Provider-native MCP
   |         |  (Anthropic connects directly)
   |         |
   v         v
+-------------------+
| AAP MCP Server    |  Streamable HTTP on :8448
| (tools: list,     |
|  retrieve, launch)|
+-------------------+
        |
        | job_templates_launch_create
        v
+-------------------+
| AAP Controller    |
| Restart Web       |  Remediation job template
| Service JT        |
+-------------------+
        |
        v
+-------------------+
| RHEL Web Server   |  httpd restarted, health check verified
+-------------------+
```

---

## Prerequisites

| Component | Version | Notes |
|---|---|---|
| Red Hat AAP | 2.5+ | Controller + EDA Controller + MCP server |
| RHEL | 9.x | Managed web server host with `httpd` installed |
| Python | 3.11+ | Inside the custom EE |
| ansible-builder | 3.0+ | To build the custom EE |
| podman | 4.x+ | Container runtime |

### LLM backend

Choose one or both:

| Backend | Type | Internet required | Setup guide |
|---|---|---|---|
| Ollama | Local (on-premise) | No | [docs/ollama-setup.md](docs/ollama-setup.md) |
| Anthropic Claude | Cloud API | Yes (MCP must be internet-reachable) | [docs/claude-setup.md](docs/claude-setup.md) |

### Collections

| Collection | Tier | Purpose |
|---|---|---|
| `infra.aap_configuration` | Validated | CasC for AAP Controller and EDA objects |
| `ansible.controller` | Certified | AAP Controller modules (cleanup, verify) |
| `ansible.eda` | Certified | EDA source plugins and modules |
| `ansible.posix` | Certified | POSIX utilities (firewalld, service management) |

---

## Quick Start

```bash
# 1. Clone and enter the repository
git clone <repo-url>
cd aap-demo-aiops-llm-mcp

# 2. Configure Ansible
cp ansible.cfg.example ansible.cfg

# 3. Install collections
ansible-galaxy collection install -r collections/requirements.yml -p collections

# 4. Configure demo variables
cp group_vars/all/demo_variables.yml.example group_vars/all/demo_variables.yml
# Edit demo_variables.yml with your environment values

# 5. Configure and encrypt secrets
cp vault.yml.example vault.yml
# Edit vault.yml with real credentials
ansible-vault encrypt vault.yml

# 6. Apply AAP Configuration as Code
ansible-playbook -e @vault.yml playbooks/aap_config.yml --ask-vault-pass

# 7. Build and push the custom Execution Environment
cd context/
./build.sh registry.example.com/aiops-triage-ee:latest
podman push registry.example.com/aiops-triage-ee:latest
cd ..

# 8. Verify setup
ansible-playbook -e @vault.yml playbooks/verify.yml --ask-vault-pass

# 9. Simulate an alert (after enabling EDA activation in the UI)
./files/simulate_alert.sh eda.example.com
```

---

## Repository Structure

| Path | Description |
|---|---|
| `ansible.cfg.example` | Ansible configuration template |
| `inventory.yml` | Managed host inventory (web server) |
| `vault.yml.example` | Vault template for secrets |
| `collections/requirements.yml` | Ansible collection dependencies |
| `group_vars/all/` | CasC variables (split by concern) |
| `playbooks/aap_config.yml` | Apply all AAP CasC |
| `playbooks/aap_cleanup.yml` | Tear down demo objects (with confirmation) |
| `playbooks/ai_triage.yml` | AI triage dispatcher (multi-backend) |
| `playbooks/demo/remediate_service.yml` | Restart httpd and verify recovery |
| `playbooks/demo/remediate_disk.yml` | Reclaim disk space (decoy template) |
| `playbooks/demo/simulate_alert.yml` | Send simulated alert to EDA |
| `playbooks/verify.yml` | Smoke test AAP objects |
| `rulebooks/prometheus_alerts.yml` | EDA rulebook (single generic rule) |
| `files/ollama_mcp_triage.py` | Triage script -- Ollama backend |
| `files/claude_mcp_triage.py` | Triage script -- Claude backend |
| `files/simulate_alert.sh` | Alert simulation shell script |
| `files/requirements.txt` | Python dependencies for triage scripts |
| `context/` | Custom EE build files (ansible-builder) |
| `docs/` | Setup, procedures, and verification guides |

---

## Job Templates

| Template | Playbook | EE | Description |
|---|---|---|---|
| AI Triage | `playbooks/ai_triage.yml` | AIOps Triage EE | LLM analyzes alert, selects and launches remediation via MCP |
| Restart Web Service | `playbooks/demo/remediate_service.yml` | Default | Restart httpd, verify port 80 health check |
| Reclaim Disk Space | `playbooks/demo/remediate_disk.yml` | Default | Clean temp files and rotate logs (decoy for reasoning test) |

---

## EDA Rulebook

A single generic rule forwards all firing Prometheus alerts to the AI Triage
job template. The LLM decides what action to take -- no alert-to-template
mapping is needed in the rulebook:

```
rulebooks/prometheus_alerts.yml
  Source: ansible.eda.alertmanager (port 5000)
  Rule:   event.status == "firing" -> run_job_template: AI Triage
```

---

## Documentation

| Document | Contents |
|---|---|
| [docs/setup.md](docs/setup.md) | Environment requirements, collection install, variable configuration |
| [docs/procedures.md](docs/procedures.md) | Step-by-step demo execution |
| [docs/verification.md](docs/verification.md) | Automated and manual verification checks |
| [docs/ollama-setup.md](docs/ollama-setup.md) | Installing and configuring Ollama |
| [docs/claude-setup.md](docs/claude-setup.md) | Anthropic API key and network requirements |
| [docs/mcp-server-setup.md](docs/mcp-server-setup.md) | Enabling the AAP MCP server |
| [docs/custom-ee.md](docs/custom-ee.md) | Building the custom Execution Environment |

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| EDA does not trigger AI Triage | Rulebook activation not enabled or not running | Enable in EDA UI; check activation status |
| AI Triage fails with "module not found" | Custom EE not built or not registered | Build EE and verify `aiops_ee_image` path |
| LLM picks wrong template | Model too small or prompt issue | Try a larger model; check `--verbose` output |
| MCP connection refused | MCP server not running on port 8448 | Enable the MCP service; check firewall |
| Claude cannot reach MCP | MCP server not internet-accessible | Expose via reverse proxy or switch to Ollama |
| Alert simulation returns HTTP error | EDA webhook port not reachable | Check EDA is running and port 5000 is open |

To fully reset the demo environment:

```bash
ansible-playbook -e @vault.yml playbooks/aap_cleanup.yml --ask-vault-pass
```

---

## References

- using-automation-execution.md -- AAP 2.5 automation execution guide
- using-automation-decisions.md -- AAP 2.5 Event-Driven Ansible guide
- configuration-as-code.md -- AAP Configuration as Code guide
- creating-and-using-execution-environments.md -- Custom EE guide
- [infra.aap_configuration collection](https://console.redhat.com/ansible/automation-hub/repo/validated/infra/aap_configuration/)
- [Ollama documentation](https://ollama.com/docs)
- [Anthropic MCP connector](https://docs.anthropic.com/en/docs/agents-and-tools/mcp)
- [Model Context Protocol specification](https://modelcontextprotocol.io/)
