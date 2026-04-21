# Claude Setup (Anthropic API)

This document covers how to configure the Anthropic Claude backend for the
AIOps triage demo. Claude uses a provider-native MCP connector, meaning
Anthropic's servers connect directly to the AAP MCP server.

## Architecture

With the Claude backend, Anthropic's API handles MCP tool calling directly:

```
Triage script (in custom EE)
  |-- calls Anthropic API with MCP server config
  |
  Anthropic API
  |-- connects to AAP MCP server (discovers tools)
  |-- Claude analyzes alert + available templates
  |-- Claude calls MCP launch tool directly
  |
  \-- returns result to triage script
```

## Network requirements

The AAP MCP server must be reachable from Anthropic's infrastructure.
This means the MCP server endpoint (`https://<aap-host>:8448/mcp`) must
be **internet-accessible**. Options:

- Expose the MCP port through a reverse proxy with TLS.
- Use a VPN tunnel or SSH tunnel with a public endpoint.
- Temporarily open the port for the demo, then close it.

If internet exposure is not acceptable, use the Ollama backend instead
(see [ollama-setup.md](ollama-setup.md)).

## Obtain an Anthropic API key

1. Create an account at [console.anthropic.com](https://console.anthropic.com/).
2. Navigate to **API Keys** in the dashboard.
3. Create a new key and copy it.
4. Add it to `vault.yml`:

```yaml
vault_anthropic_api_key: sk-ant-api03-...
```

5. Encrypt the vault:

```bash
ansible-vault encrypt vault.yml
```

## Configure the demo variables

In `group_vars/all/demo_variables.yml`:

```yaml
triage_backend: claude
anthropic_api_key: "{{ vault_anthropic_api_key }}"
```

The `mcp_server_url` and `mcp_auth_token` variables are still required,
as the script passes them to the Anthropic API for the MCP connection.

## Model selection

The default model is `claude-sonnet-4-20250514`. Claude models that support
the MCP connector beta:

| Model | Speed | Reasoning | Cost |
|---|---|---|---|
| `claude-sonnet-4-20250514` | Fast | Strong | Medium |
| `claude-opus-4-20250514` | Slower | Strongest | Higher |

To change the model, pass `--model` to the triage script or modify the
`claude_mcp_triage.py` default.

## Verify the setup

Test the Anthropic API key:

```bash
curl -s https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "Say hello"}]
  }' | python3 -m json.tool
```

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| 401 Unauthorized | Invalid API key | Regenerate the key at console.anthropic.com |
| MCP server unreachable | AAP MCP not internet-accessible | Expose via reverse proxy or use Ollama instead |
| Rate limited | Too many requests | Wait and retry; check your API tier limits |
| MCP tool errors | MCP server auth failure | Verify `mcp_auth_token` is correct and not expired |
