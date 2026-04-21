# AAP MCP Server Setup

This document covers how to enable and configure the AAP Model Context
Protocol (MCP) server, which is the bridge between the LLM and AAP
Controller.

## What is the AAP MCP server?

The MCP server exposes AAP Controller operations (listing job templates,
launching jobs, etc.) as MCP tools over a Streamable HTTP transport. The
LLM or the triage script uses these tools to discover and launch
remediation templates.

## Transport and endpoint

| Setting | Value |
|---|---|
| Protocol | HTTPS (Streamable HTTP) |
| Default port | 8448 |
| Endpoint | `https://<aap-host>:8448/mcp` |
| Authentication | Bearer token |

## Enable the MCP server

The MCP server is a component of AAP 2.5+. Enablement depends on your
deployment method:

### RPM-based deployment

Check if the MCP service is available:

```bash
systemctl status automation-gateway-mcp
```

If not running, enable and start it:

```bash
sudo systemctl enable --now automation-gateway-mcp
```

### Operator-based deployment (OpenShift)

The MCP server may be exposed as a route. Check with your cluster
administrator for the correct URL and port.

## Obtain a bearer token

The MCP server uses the same authentication as the AAP Controller API.
You can generate a personal access token from the Controller UI:

1. Log in to AAP Controller.
2. Navigate to your user profile (top-right menu).
3. Go to **Tokens**.
4. Click **Add** to create a new token.
5. Set **Scope** to **Write** (required for launching jobs).
6. Copy the token value.

Add it to `vault.yml`:

```yaml
vault_mcp_auth_token: <your-token>
```

## Verify connectivity

From a host that can reach the MCP server:

```bash
# Basic connectivity check
curl -sk \
  -H "Authorization: Bearer $MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' \
  https://aap-host:8448/mcp
```

A successful response returns a JSON-RPC result with the list of
available MCP tools (job_templates_list, job_templates_retrieve,
job_templates_launch_create, etc.).

## Firewall considerations

Ensure port 8448 is open on the AAP host:

```bash
sudo firewall-cmd --add-port=8448/tcp --permanent
sudo firewall-cmd --reload
```

### For Claude backend only

If using the Claude (Anthropic) backend, the MCP server must be reachable
from the internet. See [claude-setup.md](claude-setup.md) for network
requirements.

The Ollama backend does not require internet exposure -- all MCP traffic
stays on the local network.

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Connection refused on 8448 | MCP service not running | Enable and start the service |
| 401 Unauthorized | Invalid or expired token | Generate a new token from Controller UI |
| 403 Forbidden | Token lacks write scope | Recreate with Write scope |
| TLS errors | Self-signed certificate | Use `verify=False` in scripts (already configured) |
| No tools listed | MCP server misconfigured | Check AAP logs and service status |
