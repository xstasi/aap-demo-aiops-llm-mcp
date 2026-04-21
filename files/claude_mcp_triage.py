#!/usr/bin/env python3
"""AIOps triage script -- Anthropic Claude (provider-native MCP connector).

Uses the Anthropic API with its built-in MCP connector so that Claude
discovers available job templates and launches the best match directly
through the AAP MCP server.  The MCP server must be reachable from
Anthropic's infrastructure (internet-facing).

Exit codes:
    0  Template launched successfully
    1  No matching template (or Claude declined)
    2  Unrecoverable error
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import anthropic

SYSTEM_PROMPT = """\
You are an AIOps triage agent connected to an Ansible Automation Platform
controller via MCP.

Your workflow:
1. Use the MCP tools to list available job templates.
2. Retrieve details for each template to understand what it does.
3. Analyze the alert payload provided by the user.
4. If a template clearly addresses the problem, launch it via MCP.
5. If no template fits, explain why and do NOT launch anything.

Rules:
- NEVER guess. Only launch a template if its description clearly
  addresses the problem described in the alert.
- After launching, report the template name, job ID, and your reasoning.
- If you decide not to launch, explain why no template matches.
"""


def _extract_result(response: Any) -> dict[str, Any]:
    """Parse the Anthropic response to find launch results or reasoning."""
    result: dict[str, Any] = {
        "status": "no_match",
        "selected_template": None,
        "job_id": None,
        "reasoning": "",
        "tool_calls": [],
    }

    text_parts = []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            result["tool_calls"].append(
                {"tool": block.name, "input": block.input}
            )
        elif block.type == "mcp_tool_use":
            result["tool_calls"].append(
                {"tool": block.name, "input": block.input}
            )
        elif block.type == "mcp_tool_result":
            content_text = ""
            if isinstance(block.content, list):
                for item in block.content:
                    if hasattr(item, "text"):
                        content_text += item.text
            elif isinstance(block.content, str):
                content_text = block.content

            if content_text:
                try:
                    data = json.loads(content_text)
                    if "job" in data or "id" in data:
                        result["status"] = "launched"
                        result["job_id"] = data.get("job") or data.get("id")
                except (json.JSONDecodeError, TypeError):
                    pass

    result["reasoning"] = " ".join(text_parts) if text_parts else "No text response"

    if result["status"] == "launched":
        for tc in result["tool_calls"]:
            if "launch" in tc.get("tool", ""):
                template_id = tc["input"].get("id", "")
                result["selected_template"] = f"template_id={template_id}"
                break

    return result


def run_triage(
    alert_json: str,
    mcp_url: str,
    mcp_token: str,
    api_key: str,
    model: str = "claude-sonnet-4-20250514",
    verbose: bool = False,
) -> dict[str, Any]:
    """Send the alert to Claude with MCP server access."""
    client = anthropic.Anthropic(api_key=api_key)

    user_message = (
        "Analyze the following Prometheus/Alertmanager alert and take "
        "the appropriate remediation action using the AAP job templates "
        "available through MCP.\n\n"
        f"## Alert payload\n```json\n{alert_json}\n```"
    )

    if verbose:
        print(f"[DEBUG] User prompt:\n{user_message}", file=sys.stderr)

    response = client.beta.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        mcp_servers=[
            {
                "type": "url",
                "url": mcp_url,
                "name": "aap-controller",
                "authorization_token": mcp_token,
            }
        ],
        betas=["mcp-client-2025-04-04"],
    )

    if verbose:
        print(f"[DEBUG] Full response:\n{response}", file=sys.stderr)

    return _extract_result(response)


def main() -> None:
    parser = argparse.ArgumentParser(description="AIOps triage -- Claude backend")
    parser.add_argument("--alert-json", required=True, help="Alert payload as JSON")
    parser.add_argument("--mcp-url", required=True, help="AAP MCP server URL")
    parser.add_argument("--mcp-token", required=True, help="MCP bearer token")
    parser.add_argument("--api-key", required=True, help="Anthropic API key")
    parser.add_argument(
        "--model", default="claude-sonnet-4-20250514", help="Claude model"
    )
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    result = run_triage(
        alert_json=args.alert_json,
        mcp_url=args.mcp_url,
        mcp_token=args.mcp_token,
        api_key=args.api_key,
        model=args.model,
        verbose=args.verbose,
    )

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "launched" else 1)


if __name__ == "__main__":
    main()
