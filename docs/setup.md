# Environment Setup

This document covers the prerequisites and initial configuration for the
AIOps LLM-driven remediation demo.

## Prerequisites

| Component | Minimum version | Notes |
|---|---|---|
| Red Hat AAP | 2.5+ | Controller, EDA Controller, MCP server enabled |
| RHEL | 9.x | Managed web server host |
| Python | 3.11+ | For triage scripts inside the custom EE |
| ansible-builder | 3.0+ | To build the custom Execution Environment |
| podman | 4.x+ | Container runtime for EE build |

### LLM backend (choose one or both)

- **Ollama** -- local, on-premise. See [ollama-setup.md](ollama-setup.md).
- **Anthropic Claude** -- cloud API. See [claude-setup.md](claude-setup.md).

### AAP MCP server

The AAP MCP server must be enabled and accessible. See
[mcp-server-setup.md](mcp-server-setup.md).

## Install Ansible collections

```bash
cp ansible.cfg.example ansible.cfg
ansible-galaxy collection install -r collections/requirements.yml -p collections
```

## Configure variables

1. Copy the example files:

```bash
cp group_vars/all/demo_variables.yml.example group_vars/all/demo_variables.yml
cp vault.yml.example vault.yml
```

2. Edit `group_vars/all/demo_variables.yml`:
   - Set `aap_hostname` to your AAP Controller FQDN or IP.
   - Set `eda_hostname` to your EDA Controller FQDN or IP.
   - Set `demo_project_scm_url` to the Git URL of this repository.
   - Set `mcp_server_url` to `https://<aap-host>:8448/mcp`.
   - Choose `triage_backend`: `ollama` or `claude`.
   - Configure `llm_api_url` and `llm_model` for Ollama, or leave defaults for Claude.
   - Set `aiops_ee_image` to the registry path where you will push the custom EE.

3. Edit `vault.yml` with real credentials, then encrypt:

```bash
ansible-vault encrypt vault.yml
```

The vault file contains:
- `vault_controller_username` / `vault_controller_password` -- AAP Controller credentials
- `vault_mcp_auth_token` -- bearer token for the AAP MCP server
- `vault_anthropic_api_key` -- Anthropic API key (Claude backend only)
- `vault_machine_ssh_user` / `vault_machine_ssh_key` -- SSH credentials for managed hosts
- `vault_eda_controller_username` / `vault_eda_controller_password` -- EDA Controller credentials

## Configure inventory

Edit `inventory.yml` to set the actual IP or FQDN of your web server host
under `web_servers`:

```yaml
web_servers:
  hosts:
    webserver1.example.com:
      ansible_host: 192.168.1.100   # <-- your real host IP
```

Ensure the web server has `httpd` installed and that the machine
credential can SSH to it with `become` privileges.

## Next steps

- Build the custom Execution Environment: [custom-ee.md](custom-ee.md)
- Configure the LLM backend: [ollama-setup.md](ollama-setup.md) or [claude-setup.md](claude-setup.md)
- Run the demo: [procedures.md](procedures.md)
