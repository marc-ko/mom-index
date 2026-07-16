import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DASHBOARD_PATH = ROOT / "data" / "dashboard_data.json"
DEFAULT_OUTPUT_PATH = ROOT / ".github" / "ISSUE_TEMPLATE.md"
DEFAULT_DASHBOARD_URL = "https://marc-ko.github.io/mom-index/dashboard.html"

SECTOR_NAMES = {
    "nasdaq": "Nasdaq",
    "gold": "Gold",
    "cpo": "CPO / Communications",
    "semiconductor": "Semiconductor",
}


def _format_number(value):
    if value is None:
        return "n/a"
    if isinstance(value, (int, float)):
        return f"{value:.1f}"
    return str(value)


def _escape_table_cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def _load_latest_dashboard(dashboard_path):
    data = json.loads(Path(dashboard_path).read_text(encoding="utf-8"))
    latest = data.get("latest")
    if not latest:
        raise ValueError(f"Missing latest dashboard record in {dashboard_path}")
    if not latest.get("date"):
        raise ValueError(f"Missing latest dashboard date in {dashboard_path}")
    if not latest.get("sectors"):
        raise ValueError(f"Missing latest sectors in {dashboard_path}")
    return latest


def build_issue_template(latest, dashboard_url=DEFAULT_DASHBOARD_URL):
    date = latest["date"]
    lines = [
        "---",
        f"title: Mom Index Daily Report - {date}",
        "labels: documentation",
        "---",
        "",
        "# Mom Index Daily Report",
        "",
        f"Date: {date}",
        "",
        f"Dashboard: {dashboard_url}",
        "",
        "| Sector | Mom Index | Mom Buy | Mom Sell | Posts | Newbie Posts | Interpretation |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for sector_key, sector in latest["sectors"].items():
        details = sector.get("details") or {}
        sector_name = SECTOR_NAMES.get(sector_key, sector_key)
        row = [
            sector_name,
            _format_number(sector.get("index")),
            _format_number(details.get("mom_buy_index")),
            _format_number(details.get("mom_sell_index")),
            str(details.get("total_posts", "n/a")),
            str(details.get("newbie_posts", "n/a")),
            _escape_table_cell(sector.get("interpretation", "n/a")),
        ]
        lines.append("| " + " | ".join(row) + " |")

    lines.extend(
        [
            "",
            "Raw Rednote/Xiaohongshu post text is not published in this issue. "
            "Use the dashboard for the public snapshot and keep local scrape caches private.",
            "",
        ]
    )
    return "\n".join(lines)


def generate_issue_template(
    dashboard_path=DEFAULT_DASHBOARD_PATH,
    output_path=DEFAULT_OUTPUT_PATH,
    dashboard_url=DEFAULT_DASHBOARD_URL,
):
    latest = _load_latest_dashboard(dashboard_path)
    content = build_issue_template(latest, dashboard_url=dashboard_url)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate the daily Mom Index issue template.")
    parser.add_argument("--dashboard", type=Path, default=DEFAULT_DASHBOARD_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--dashboard-url", default=DEFAULT_DASHBOARD_URL)
    args = parser.parse_args()

    output = generate_issue_template(
        dashboard_path=args.dashboard,
        output_path=args.output,
        dashboard_url=args.dashboard_url,
    )
    print(f"Issue template written: {output}")


if __name__ == "__main__":
    main()
