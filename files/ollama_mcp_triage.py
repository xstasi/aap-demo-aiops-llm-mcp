#!/usr/bin/env python3
"""AIOps triage script -- Ollama (script-side MCP client).

Connects to the AAP MCP server to discover available job templates,
sends the alert payload and template catalog to a local LLM via an
OpenAI-compatible API, parses a structured JSON decision, validates
the template ID, and launches the selected template via MCP.

Exit codes:
    0  Template launched successfully
    1  No matching template (or LLM declined)
    2  Unrecoverable error
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from openai import OpenAI

SYSTEM_PROMPT = """\
You are an AIOps triage agent.

You receive two inputs:
1. A Prometheus / Alertmanager alert payload (JSON).
2. A catalog of available AAP job templates (ID, name, description).

Respond with ONLY a JSON object -- no markdown fences, no extra text:

If a template clearly matches the problem described in the alert:
{"action": "launch", "template_id": <int>, "reasoning": "<why>"}

If no template matches:
{"action": "no_match", "reasoning": "<why none fit>"}

Rules:
- NEVER guess. Only choose "launch" if the template description clearly
  addresses the problem described in the alert.
- Respond with the JSON object only. Nothing else.
"""


def _strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks emitted by some models."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _extract_json(text: str) -> dict[str, Any]:
    """Extract the first JSON object from text, ignoring markdown fences."""
    text = _strip_think_tags(text)
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = text.replace("```", "")
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response: {text[:200]}")
    return json.loads(match.group())


async def _fetch_templates(session: ClientSession) -> list[dict[str, Any]]:
    """Pre-fetch all job template details from the AAP MCP server."""
    list_result = await session.call_tool("job_templates_list", {})

    raw = list_result.content[0].text if list_result.content else "[]"
    candidates = json.loads(raw) if isinstance(raw, str) else raw

    if isinstance(candidates, dict):
        candidates = candidates.get("results", [])

    templates: list[dict[str, Any]] = []
    for t in candidates:
        tid = t.get("id")
        if tid is None:
            continue
        detail_result = await session.call_tool(
            "job_templates_retrieve", {"id": str(tid)}
        )
        detail_raw = detail_result.content[0].text if detail_result.content else "{}"
        detail = json.loads(detail_raw) if isinstance(detail_raw, str) else detail_raw
        templates.append(
            {
                "id": detail.get("id", tid),
                "name": detail.get("name", t.get("name", "")),
                "description": detail.get("description", t.get("description", "")),
            }
        )
    return templates


def _call_llm(
    alert_json: str,
    templates: list[dict[str, Any]],
    llm_url: str,
    llm_model: str,
    api_key: str = "",
    verbose: bool = False,
) -> dict[str, Any]:
    """Call the LLM for a structured JSON triage decision."""
    catalog = json.dumps(templates, indent=2)
    user_message = (
        f"## Alert\n```json\n{alert_json}\n```\n\n"
        f"## Available templates\n```json\n{catalog}\n```"
    )

    if verbose:
        print(f"[DEBUG] User prompt:\n{user_message}", file=sys.stderr)

    client = OpenAI(base_url=llm_url, api_key=api_key or "not-needed")
    response = client.chat.completions.create(
        model=llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,
    )

    llm_text = response.choices[0].message.content or ""
    if verbose:
        print(f"[DEBUG] LLM response:\n{llm_text}", file=sys.stderr)

    return _extract_json(llm_text)


async def run_triage(
    alert_json: str,
    mcp_url: str,
    mcp_token: str,
    llm_url: str,
    llm_model: str,
    llm_api_key: str = "",
    verbose: bool = False,
) -> dict[str, Any]:
    """Full triage pipeline: MCP discovery -> LLM decision -> MCP launch."""
    result: dict[str, Any] = {
        "status": "no_match",
        "selected_template": None,
        "job_id": None,
        "reasoning": "",
    }

    http_headers = {"Authorization": f"Bearer {mcp_token}"}
    http_client = httpx.AsyncClient(headers=http_headers, verify=False)

    try:
        async with streamable_http_client(
            mcp_url, http_client=http_client
        ) as (read_stream, write_stream, *_):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                templates = await _fetch_templates(session)
                if verbose:
                    print(
                        f"[DEBUG] Discovered {len(templates)} templates",
                        file=sys.stderr,
                    )

                if not templates:
                    result["reasoning"] = "No job templates found on the controller."
                    return result

                decision = _call_llm(
                    alert_json, templates, llm_url, llm_model, llm_api_key, verbose
                )

                if decision.get("action") != "launch":
                    result["reasoning"] = decision.get(
                        "reasoning", "LLM declined to launch."
                    )
                    return result

                chosen_id = decision.get("template_id")
                matched = [t for t in templates if t["id"] == chosen_id]
                if not matched:
                    result["reasoning"] = (
                        f"LLM selected template ID {chosen_id} which does not exist."
                    )
                    return result

                launch_result = await session.call_tool(
                    "job_templates_launch_create",
                    {"id": str(chosen_id)},
                )
                launch_raw = (
                    launch_result.content[0].text if launch_result.content else "{}"
                )
                launch_data = (
                    json.loads(launch_raw) if isinstance(launch_raw, str) else launch_raw
                )

                result["status"] = "launched"
                result["selected_template"] = matched[0]["name"]
                result["job_id"] = launch_data.get("id") or launch_data.get("job")
                result["reasoning"] = decision.get("reasoning", "")
    finally:
        await http_client.aclose()

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="AIOps triage -- Ollama backend")
    parser.add_argument("--alert-json", required=True, help="Alert payload as JSON")
    parser.add_argument("--mcp-url", required=True, help="AAP MCP server URL")
    parser.add_argument("--mcp-token", required=True, help="MCP bearer token")
    parser.add_argument("--llm-url", required=True, help="OpenAI-compatible API URL")
    parser.add_argument("--llm-model", required=True, help="Model name")
    parser.add_argument("--llm-api-key", default="", help="API key (if required)")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    result = asyncio.run(
        run_triage(
            alert_json=args.alert_json,
            mcp_url=args.mcp_url,
            mcp_token=args.mcp_token,
            llm_url=args.llm_url,
            llm_model=args.llm_model,
            llm_api_key=args.llm_api_key,
            verbose=args.verbose,
        )
    )

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "launched" else 1)


if __name__ == "__main__":
    main()
