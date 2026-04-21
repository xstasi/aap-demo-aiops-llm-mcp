# Custom Execution Environment

The AI Triage job template requires Python packages (LLM client SDKs,
MCP SDK, httpx) that are not available in the default AAP Execution
Environments. This document covers building, pushing, and registering
the custom EE.

## What goes into the custom EE

| Layer | Contents |
|---|---|
| Base image | `registry.redhat.io/ansible-automation-platform-25/ee-minimal-rhel9:latest` |
| Python packages | `openai`, `anthropic`, `mcp`, `httpx` |
| Ansible collections | `ansible.controller`, `ansible.posix` |
| Triage scripts | `files/ollama_mcp_triage.py`, `files/claude_mcp_triage.py` (copied to `/opt/aiops/files/`) |

## Prerequisites

- `ansible-builder` >= 3.0 installed on your build host.
- `podman` (or `docker`) available.
- Access to `registry.redhat.io` (Red Hat container registry) for the base image.
  Log in first:

```bash
podman login registry.redhat.io
```

## Build the EE

The `context/` directory contains the ansible-builder definition and a
convenience script:

```bash
cd context/
./build.sh aiops-triage-ee:latest
```

This script:
1. Copies `files/` (triage scripts) into the build context.
2. Runs `ansible-builder build` to create the image.
3. Cleans up the copied scripts.

### Manual build (alternative)

```bash
cd context/
cp -r ../files/ files/
ansible-builder build \
  --file execution-environment.yml \
  --tag aiops-triage-ee:latest \
  --container-runtime podman
rm -rf files/
```

## Push to a registry

Tag and push the image to a registry accessible by your AAP Controller:

```bash
podman tag aiops-triage-ee:latest registry.example.com/aiops-triage-ee:latest
podman push registry.example.com/aiops-triage-ee:latest
```

## Register in AAP

The CasC playbook (`playbooks/aap_config.yml`) registers the EE
automatically using the `aiops_ee_image` variable from
`group_vars/all/demo_variables.yml`. Make sure this variable matches the
registry path you pushed to:

```yaml
aiops_ee_image: "registry.example.com/aiops-triage-ee:latest"
```

If the registry requires authentication, create a credential in AAP
Controller of type **Container Registry** and associate it with the EE.

## Verify the EE

After applying CasC, confirm in the AAP Controller UI:

1. Navigate to **Execution Environments**.
2. Confirm **AIOps Triage EE** exists with the correct image path.
3. The **AI Triage** job template should reference this EE.

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Build fails on base image pull | Not logged in to registry.redhat.io | Run `podman login registry.redhat.io` |
| pip install fails | Network restrictions | Configure pip proxy or mirror in `context/` |
| EE image not found by AAP | Image not pushed or wrong path | Verify `aiops_ee_image` matches the pushed path |
| Triage script not found at runtime | Scripts not copied during build | Rebuild with `./build.sh`; verify `files/` exists in context |
