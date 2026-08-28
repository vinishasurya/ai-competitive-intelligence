"""'Ask the analyst' agent: follow-up Q&A over a report's evidence base.

A bounded tool-use loop (post-V1 extension): Claude chooses which tools to
call (report claims, structured findings, stored source text, fresh web
search, page crawling) and iterates until it can answer, capped at MAX_TURNS
model calls. Answers cite source ids so the UI can link them like report
claims. The loop is manual and explicit; nothing here can run away.
"""

import json
import re
import sqlite3

import anthropic
from pydantic import BaseModel, Field

from app import config
from app.report import _clean_text
from app.tools.crawl import crawl_page
from app.tools.search import search_web

MAX_TURNS = 6
MAX_TOOL_RESULT_CHARS = 12_000

SYSTEM = """You are the research analyst behind a competitive intelligence \
report about {product}. A reader is asking a follow-up question.

Ground rules:
- Prefer the report's stored evidence (claims, findings, sources). Use \
search_web or crawl_page only when the stored evidence cannot answer.
- Cite sources inline by writing their numeric id in brackets, e.g. [12]. \
Only cite ids that appear in tool results.
- If something is not in the evidence and cannot be verified, say so plainly \
instead of guessing. Distinguish facts from your own analysis.
- Answer in 2-6 sentences of plain prose. No em dashes. If the question asks \
for a calculation (e.g. team cost), show the arithmetic."""


TOOLS = [
    {
        "name": "list_claims",
        "description": "List the report's claims (text, trust label, cited source ids), optionally for one section.",
        "input_schema": {
            "type": "object",
            "properties": {"section": {
                "type": "string",
                "enum": ["executive_summary", "competitive_landscape",
                         "feature_comparison", "pricing_comparison", "all"],
            }},
        },
    },
    {
        "name": "get_findings",
        "description": "Structured findings (positioning, features, pricing tiers with prices) for every company in the report, with the source ids they came from. Best tool for pricing questions.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "read_source",
        "description": "Read the stored text of a cited source page by its numeric id (as crawled at report time, with URL and retrieval date).",
        "input_schema": {
            "type": "object",
            "properties": {"source_id": {"type": "integer"}},
            "required": ["source_id"],
        },
    },
    {
        "name": "search_web",
        "description": "Fresh web search for information beyond the stored evidence. Results are current, not from report time.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "crawl_page",
        "description": "Fetch a public web page's current text (e.g. to check whether a cited page changed).",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
]


class ToolStep(BaseModel):
    tool: str
    input: dict


class AnalystAnswer(BaseModel):
    ok: bool
    answer: str = ""
    source_ids: list[int] = Field(default_factory=list)
    trace: list[ToolStep] = Field(default_factory=list)
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_cents: float = 0.0
    error: str | None = None


def _execute_tool(conn: sqlite3.Connection, run_id: int, name: str, args: dict) -> str:
    """Run one tool against this run's evidence; always returns a JSON string."""
    try:
        if name == "list_claims":
            section = args.get("section", "all")
            cond, params = "", [run_id]
            if section and section != "all":
                cond, params = "AND section = ?", [run_id, section]
            rows = conn.execute(
                f"SELECT id, section, text, claim_type, source_ids_json FROM claims "
                f"WHERE run_id = ? {cond}", params,
            ).fetchall()
            return json.dumps([
                {"section": r["section"], "text": r["text"],
                 "claim_type": r["claim_type"],
                 "source_ids": json.loads(r["source_ids_json"])}
                for r in rows
            ])
        if name == "get_findings":
            comp_names = {r["id"]: r["name"] for r in conn.execute(
                "SELECT id, name FROM competitors WHERE run_id = ?", (run_id,)
            ).fetchall()}
            product = conn.execute(
                "SELECT p.name FROM products p JOIN runs r ON r.product_id = p.id "
                "WHERE r.id = ?", (run_id,),
            ).fetchone()["name"]
            rows = conn.execute(
                "SELECT competitor_id, dimension, value_json, source_ids_json "
                "FROM findings WHERE run_id = ?", (run_id,),
            ).fetchall()
            return json.dumps([
                {"company": comp_names.get(r["competitor_id"], product),
                 "dimension": r["dimension"],
                 "value": json.loads(r["value_json"]),
                 "source_ids": json.loads(r["source_ids_json"])}
                for r in rows
            ])
        if name == "read_source":
            row = conn.execute(
                "SELECT id, url, source_type, fetched_at, raw_text FROM sources "
                "WHERE run_id = ? AND id = ?", (run_id, args["source_id"]),
            ).fetchone()
            if row is None:
                return json.dumps({"error": "no such source in this report"})
            return json.dumps({
                "source_id": row["id"], "url": row["url"],
                "type": row["source_type"], "retrieved_at": row["fetched_at"],
                "text": (row["raw_text"] or "")[:MAX_TOOL_RESULT_CHARS],
            })
        if name == "search_web":
            return json.dumps(search_web(args["query"], max_results=6).model_dump())
        if name == "crawl_page":
            result = crawl_page(args["url"])
            payload = result.model_dump()
            if payload.get("raw_text"):
                payload["raw_text"] = payload["raw_text"][:MAX_TOOL_RESULT_CHARS]
            return json.dumps(payload)
        return json.dumps({"error": f"unknown tool {name}"})
    except Exception as exc:
        return json.dumps({"error": f"{type(exc).__name__}: {exc}"})


def _model_call(client, system: str, messages: list, tools: list | None):
    kwargs = {"tools": tools} if tools else {}
    return client.messages.create(
        model=config.MODEL_PROFILER,
        max_tokens=4000,
        thinking={"type": "adaptive"},
        system=system,
        messages=messages,
        **kwargs,
    )


def ask_analyst(conn: sqlite3.Connection, run_id: int, question: str) -> AnalystAnswer:
    product = conn.execute(
        "SELECT p.name FROM products p JOIN runs r ON r.product_id = p.id "
        "WHERE r.id = ?", (run_id,),
    ).fetchone()
    if product is None:
        return AnalystAnswer(ok=False, error="unknown run")

    valid_source_ids = {r["id"] for r in conn.execute(
        "SELECT id FROM sources WHERE run_id = ?", (run_id,)
    ).fetchall()}

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    system = SYSTEM.format(product=product["name"])
    messages = [{"role": "user", "content": question}]
    answer = AnalystAnswer(ok=False)

    try:
        for turn in range(MAX_TURNS):
            # Last turn: no tools, forcing a final answer with what we have.
            tools = TOOLS if turn < MAX_TURNS - 1 else None
            response = _model_call(client, system, messages, tools)
            answer.turns = turn + 1
            answer.input_tokens += response.usage.input_tokens
            answer.output_tokens += response.usage.output_tokens

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if response.stop_reason != "tool_use" or not tool_uses:
                text = next(
                    (b.text for b in response.content if b.type == "text"), ""
                )
                answer.answer = _clean_text(text.strip())
                answer.ok = bool(answer.answer)
                if not answer.ok:
                    answer.error = "the analyst returned no answer"
                break

            messages.append({"role": "assistant", "content": response.content})
            results = []
            for block in tool_uses:
                answer.trace.append(ToolStep(tool=block.name, input=dict(block.input)))
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": _execute_tool(conn, run_id, block.name, block.input),
                })
            messages.append({"role": "user", "content": results})
        else:
            answer.error = "turn limit reached without an answer"
    except Exception as exc:
        answer.error = f"{type(exc).__name__}: {exc}"

    answer.cost_cents = config.estimate_cost_cents(
        config.MODEL_PROFILER, answer.input_tokens, answer.output_tokens
    )
    answer.source_ids = sorted({
        int(m) for m in re.findall(r"\[(\d+)\]", answer.answer)
        if int(m) in valid_source_ids
    })
    return answer
