"""Offline tests for the Ask-the-analyst agent loop; model calls faked."""

import json

import pytest

from app import analyst
from app.analyst import _execute_tool, ask_analyst
from app.db import connect, init_db, insert_row
from app.models import Claim, Competitor, Finding, Product, Run, Source


@pytest.fixture
def seeded(tmp_path):
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    product_id = insert_row(conn, "products", Product(
        url="https://acme.test", domain="acme.test", name="Acme").to_row())
    run_id = insert_row(conn, "runs", Run(product_id=product_id, status="completed").to_row())
    comp_id = insert_row(conn, "competitors", Competitor(
        run_id=run_id, name="Rival", domain="rival.test", verified=True).to_row())
    source_id = insert_row(conn, "sources", Source(
        run_id=run_id, url="https://rival.test/pricing", source_type="pricing",
        raw_text="Rival Pro costs $12 per user per month.", http_status=200).to_row())
    insert_row(conn, "findings", Finding(
        run_id=run_id, competitor_id=comp_id, dimension="pricing",
        value={"available": True, "tiers": [{"name": "Pro", "price_usd": 12.0}]},
        source_ids=[source_id]).to_row())
    insert_row(conn, "claims", Claim(
        run_id=run_id, section="pricing_comparison",
        text="Rival's Pro tier costs $12 per user per month.",
        claim_type="verified", source_ids=[source_id]).to_row())
    yield conn, run_id, source_id
    conn.close()


class FakeUsage:
    input_tokens, output_tokens = 1000, 200


class FakeBlock:
    def __init__(self, type_, **kw):
        self.type = type_
        self.__dict__.update(kw)


class FakeResponse:
    def __init__(self, blocks, stop_reason):
        self.content = blocks
        self.stop_reason = stop_reason
        self.usage = FakeUsage()


class TestExecuteTool:
    def test_get_findings_and_read_source(self, seeded):
        conn, run_id, source_id = seeded
        findings = json.loads(_execute_tool(conn, run_id, "get_findings", {}))
        assert findings[0]["company"] == "Rival"
        assert findings[0]["value"]["tiers"][0]["price_usd"] == 12.0
        src = json.loads(_execute_tool(conn, run_id, "read_source",
                                       {"source_id": source_id}))
        assert "costs $12" in src["text"]

    def test_read_missing_source_and_unknown_tool(self, seeded):
        conn, run_id, _ = seeded
        assert "error" in json.loads(
            _execute_tool(conn, run_id, "read_source", {"source_id": 999}))
        assert "error" in json.loads(_execute_tool(conn, run_id, "nope", {}))


class TestAgentLoop:
    def test_direct_answer_without_tools(self, seeded, monkeypatch):
        conn, run_id, source_id = seeded
        monkeypatch.setattr(analyst, "_model_call", lambda c, s, m, t: FakeResponse(
            [FakeBlock("text", text=f"Rival's Pro tier is $12 per user [{source_id}].")],
            "end_turn"))
        result = ask_analyst(conn, run_id, "What does Rival cost?")
        assert result.ok and result.turns == 1
        assert result.source_ids == [source_id]  # cited id extracted + validated
        assert result.cost_cents > 0

    def test_tool_round_trip(self, seeded, monkeypatch):
        conn, run_id, source_id = seeded
        calls = []

        def fake_model(client, system, messages, tools):
            calls.append(len(messages))
            if len(calls) == 1:
                return FakeResponse(
                    [FakeBlock("tool_use", id="tu1", name="get_findings", input={})],
                    "tool_use")
            # Second call must include the tool result we produced.
            tool_result = messages[-1]["content"][0]
            assert tool_result["type"] == "tool_result"
            assert "Rival" in tool_result["content"]
            return FakeResponse(
                [FakeBlock("text", text=f"$12 per user per month [{source_id}].")],
                "end_turn")

        monkeypatch.setattr(analyst, "_model_call", fake_model)
        result = ask_analyst(conn, run_id, "What does Rival cost?")
        assert result.ok and result.turns == 2
        assert [t.tool for t in result.trace] == ["get_findings"]

    def test_turn_cap_forces_toolless_final_answer(self, seeded, monkeypatch):
        conn, run_id, _ = seeded
        seen_tools = []

        def fake_model(client, system, messages, tools):
            seen_tools.append(tools is not None)
            if tools is not None:  # keep asking for tools while allowed
                return FakeResponse(
                    [FakeBlock("tool_use", id=f"t{len(seen_tools)}",
                               name="get_findings", input={})], "tool_use")
            return FakeResponse([FakeBlock("text", text="Best effort answer.")],
                                "end_turn")

        monkeypatch.setattr(analyst, "_model_call", fake_model)
        result = ask_analyst(conn, run_id, "loop forever please")
        assert result.ok and result.turns == analyst.MAX_TURNS
        assert seen_tools[-1] is False  # final call had tools disabled
        assert len(result.trace) == analyst.MAX_TURNS - 1

    def test_unknown_run(self, seeded):
        conn, _, _ = seeded
        result = ask_analyst(conn, 999, "hi")
        assert not result.ok and result.error == "unknown run"

    def test_em_dashes_cleaned_from_answer(self, seeded, monkeypatch):
        conn, run_id, _ = seeded
        monkeypatch.setattr(analyst, "_model_call", lambda c, s, m, t: FakeResponse(
            [FakeBlock("text", text="Cheap — and cheerful.")], "end_turn"))
        result = ask_analyst(conn, run_id, "verdict?")
        assert "—" not in result.answer
