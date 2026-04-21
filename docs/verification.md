# Verification

This document describes how to validate the demo setup and confirm that
the end-to-end remediation flow works correctly.

## Automated verification

Run the verify playbook to check that all AAP objects exist:

```bash
ansible-playbook -e @vault.yml playbooks/verify.yml --ask-vault-pass
```

### Expected output

All tasks should report `ok` (green). A passing run looks like:

```
TASK [Verify organization exists] ******************
ok: [localhost]

TASK [Verify project exists] ***********************
ok: [localhost]

TASK [Verify inventory exists] *********************
ok: [localhost]

TASK [Verify job templates exist] ******************
ok: [localhost] => (item=AI Triage)
ok: [localhost] => (item=Restart Web Service)
ok: [localhost] => (item=Reclaim Disk Space)

TASK [Verify machine credential exists] ************
ok: [localhost]

TASK [Verify controller token credential exists] ***
ok: [localhost]

TASK [Verify execution environment exists] *********
ok: [localhost]

TASK [All AAP objects verified] ********************
ok: [localhost] => {
    "msg": "All AIOps demo objects are present..."
}

PLAY RECAP *****************************************
localhost : ok=8  changed=0  unreachable=0  failed=0
```

## Manual checks

### AAP Controller UI

1. **Organizations**: confirm `AIOps Demo` exists.
2. **Projects**: confirm `AIOps LLM MCP Project` exists, SCM URL is correct,
   and last sync succeeded.
3. **Inventories**: confirm `AIOps Demo Inventory` exists and contains
   `webserver1.example.com` in the `web_servers` group.
4. **Credentials**: confirm `AIOps Machine Credential` and
   `AIOps Controller Token` exist.
5. **Execution Environments**: confirm `AIOps Triage EE` exists and the
   image path matches `aiops_ee_image`.
6. **Templates**: confirm all three job templates exist:

| Template | Playbook | EE |
|---|---|---|
| AI Triage | `playbooks/ai_triage.yml` | AIOps Triage EE |
| Restart Web Service | `playbooks/demo/remediate_service.yml` | Default |
| Reclaim Disk Space | `playbooks/demo/remediate_disk.yml` | Default |

### EDA Controller UI

1. **Projects**: confirm `AIOps EDA Project` exists and the SCM URL matches.
2. **Rulebook Activations**: confirm `Prometheus Alert Monitor` exists,
   is **Enabled**, and shows status **Running**.

### MCP server connectivity

From the AAP host or a host with network access to the MCP server:

```bash
curl -sk -H "Authorization: Bearer $MCP_TOKEN" \
  https://aap-host:8448/mcp
```

A successful response (even an error about missing method) confirms the
MCP server is reachable.

### LLM endpoint connectivity

**Ollama:**

```bash
curl -s http://192.168.1.250:11434/v1/models | python3 -m json.tool
```

Confirm the model listed in `llm_model` appears in the response.

**Claude:**

The Anthropic API is cloud-hosted; connectivity is verified implicitly
when the triage script runs. Ensure the `ANTHROPIC_API_KEY` is valid.

## References

- [AAP 2.5 -- Using automation execution](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.5/html/using-automation-execution/)
- [AAP 2.5 -- Using automation decisions (EDA)](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.5/html/using-automation-decisions/)
- [infra.aap_configuration collection](https://console.redhat.com/ansible/automation-hub/repo/validated/infra/aap_configuration/)
- [Ollama documentation](https://ollama.com/docs)
- [Anthropic API -- MCP connector](https://docs.anthropic.com/en/docs/agents-and-tools/mcp)
