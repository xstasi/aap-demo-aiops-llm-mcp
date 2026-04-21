# Ollama Setup

This document covers how to install and configure Ollama as the local LLM
backend for the AIOps triage demo. Ollama runs entirely on-premise with no
cloud dependencies.

## Architecture

With the Ollama backend, the triage script acts as the MCP client:

```
Triage script (in custom EE)
  |-- connects to AAP MCP server (pre-fetches templates)
  |-- calls Ollama API (OpenAI-compatible) for a JSON decision
  |-- validates the decision
  \-- launches the selected template via MCP
```

All traffic stays on the local network.

## Install Ollama

On the host that will serve the LLM (can be the AAP host or a separate GPU
server):

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Verify the installation:

```bash
ollama --version
```

## Pull a model

Choose a model that fits your hardware. Recommended options:

| Model | Size | VRAM needed | Notes |
|---|---|---|---|
| `qwen3:8b` | ~5 GB | ~6 GB | Good balance of speed and reasoning |
| `qwen3:4b` | ~2.5 GB | ~4 GB | Faster, slightly less accurate |
| `llama3.1:8b` | ~4.7 GB | ~6 GB | Strong general reasoning |
| `mistral:7b` | ~4.1 GB | ~6 GB | Fast, good at structured output |

```bash
ollama pull qwen3:8b
```

## Configure Ollama for network access

By default, Ollama listens on `127.0.0.1:11434`. To allow access from the
AAP Execution Environment, set the bind address:

```bash
# Edit the systemd service
sudo systemctl edit ollama

# Add these lines:
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

Then restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

## Verify the OpenAI-compatible endpoint

Ollama exposes an OpenAI-compatible API at `/v1/`:

```bash
# List available models
curl -s http://<ollama-host>:11434/v1/models | python3 -m json.tool

# Test a simple completion
curl -s http://<ollama-host>:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:8b",
    "messages": [{"role": "user", "content": "Say hello in JSON: {\"greeting\": \"...\"}"}],
    "temperature": 0.1
  }' | python3 -m json.tool
```

## Configure the demo variables

In `group_vars/all/demo_variables.yml`:

```yaml
triage_backend: ollama
llm_api_url: "http://<ollama-host>:11434/v1"
llm_model: qwen3:8b
```

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Connection refused | Ollama not running or bound to localhost | Set `OLLAMA_HOST=0.0.0.0:11434` and restart |
| Model not found | Model not pulled | Run `ollama pull <model>` |
| Slow responses | Insufficient GPU memory, model running on CPU | Use a smaller model or add GPU memory |
| `<think>` tags in output | Some models (Qwen, DeepSeek) emit reasoning blocks | The triage script strips these automatically |
| Garbled JSON | Model too small for structured output | Try a larger model (`8b` or above) |
