"""Tests for the Income OS tools: opportunities, investment research, projects,
and the money briefing aggregator. Guardrail checks (no advice framing, no
brokerage/trading hooks) are asserted explicitly.
"""

from __future__ import annotations


def test_income_opportunities_add_status_list_today(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    from jarvis.tools.income_tools import IncomeOpportunitiesTool

    tool = IncomeOpportunitiesTool()
    added = tool.run(action="add", title="Automate invoices for a small biz", type="gig", url="https://example.com")
    assert "Added opportunity" in added
    opp_id = added.split("`")[1]

    listing = tool.run(action="list")
    assert "Automate invoices" in listing
    assert "saved: 1" in listing or "saved" in listing

    today_before_status_change = tool.run(action="today")
    assert "Today's plan" in today_before_status_change
    assert opp_id in today_before_status_change

    status = tool.run(action="status", id=opp_id, set_status="applied")
    assert "applied" in status

    today = tool.run(action="today")
    assert "Today's plan" in today

    bad_status = tool.run(action="status", id=opp_id, set_status="not-a-status")
    assert "Unknown status" in bad_status


def test_income_opportunities_find_uses_mock_search_and_saves(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    from jarvis.tools.income_tools import IncomeOpportunitiesTool

    tool = IncomeOpportunitiesTool()
    result = tool.run(action="find", query="remote python automation gigs")
    assert "Income Opportunities" in result
    assert "does not auto-apply" in result

    listing = tool.run(action="list")
    assert "discovered: 1" in listing


def test_investment_research_watchlist_and_portfolio_not_live_synced(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    from jarvis.tools.income_tools import InvestmentResearchTool

    tool = InvestmentResearchTool()

    added = tool.run(action="watchlist_add", symbol="aapl", note="watching for a dip")
    assert "AAPL" in added
    assert "not financial advice" in added.lower()

    watchlist = tool.run(action="watchlist")
    assert "AAPL" in watchlist

    removed = tool.run(action="watchlist_remove", symbol="AAPL")
    assert "Removed" in removed

    tool.run(action="portfolio_set", symbol="MSFT", quantity=10, cost_basis=300, current_price=320)
    portfolio = tool.run(action="portfolio")
    assert "MSFT" in portfolio
    assert "not live-synced" in portfolio
    assert "P/L" in portfolio

    research = tool.run(action="research", symbol="MSFT")
    assert "Research summary" in research
    assert "not financial advice" in research.lower()

    notes = tool.run(action="notes")
    assert "MSFT" in notes


def test_investment_research_every_response_has_disclaimer(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    from jarvis.tools.income_tools import InvestmentResearchTool

    tool = InvestmentResearchTool()
    for action, kwargs in [
        ("watchlist", {}),
        ("watchlist_add", {"symbol": "TSLA"}),
        ("portfolio", {}),
        ("portfolio_set", {"symbol": "TSLA", "quantity": 1, "cost_basis": 200}),
        ("research", {"symbol": "TSLA"}),
        ("notes", {}),
    ]:
        result = tool.run(action=action, **kwargs)
        assert "not financial advice" in result.lower(), f"missing disclaimer for action={action}"


def test_income_projects_add_log_report_today(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    from jarvis.tools.income_tools import IncomeProjectsTool

    tool = IncomeProjectsTool()
    added = tool.run(action="add", name="Freelance automation")
    proj_id = added.split("`")[1]

    log1 = tool.run(action="log", id=proj_id, hours=2, revenue=150)
    assert "Logged entry" in log1

    report = tool.run(action="report")
    assert "Freelance automation" in report
    assert "75.00/hour" in report or "/hour" in report

    today = tool.run(action="today")
    assert "Today's plan" in today
    assert proj_id in today


def test_money_briefing_aggregates_and_has_disclaimer(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    from jarvis.tools.income_tools import IncomeOpportunitiesTool, IncomeProjectsTool, MoneyBriefingTool

    IncomeOpportunitiesTool().run(action="add", title="Grant for small biz automation")
    proj = IncomeProjectsTool().run(action="add", name="Consulting")
    assert proj

    briefing = MoneyBriefingTool().run(action="today")
    assert "Money Briefing" in briefing
    assert "Career" in briefing
    assert "Income opportunities" in briefing
    assert "Income projects" in briefing
    assert "Watchlist" in briefing
    assert "not financial advice" in briefing.lower()


def test_income_tools_registered_in_registry(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    from jarvis.tools.registry import get_tool, list_tools

    names = list_tools()
    for expected in ("income_opportunities", "investment_research", "income_projects", "money_briefing"):
        assert expected in names
        assert get_tool(expected) is not None


def test_income_state_is_local_json_files_only(monkeypatch, tmp_path):
    """Guardrail: state must live under JARVIS_HOME/income as plain JSON, no DB."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    from jarvis.tools.income_tools import IncomeOpportunitiesTool, income_dir

    IncomeOpportunitiesTool().run(action="add", title="Test gig")
    d = income_dir()
    assert d == tmp_path / "income"
    files = list(d.glob("*.json"))
    assert len(files) == 1
    assert files[0].name == "opportunities.json"
