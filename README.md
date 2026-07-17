# Mom Index

> English fork of the original project by [mihang123/mom-index](https://github.com/mihang123/mom-index). This fork keeps the core idea and dashboard, adds Rednote/Xiaohongshu Playwright collection work, fixes the sub-index formula, and documents the workflow in English.

Mom Index tracks retail-investor, beginner, and "mom investor" discussion heat across Chinese social platforms. The higher the index, the more extreme retail sentiment appears to be, making it a contrarian behavioral-finance signal inspired by the shoeshine-boy theory.

Live dashboard: [https://marc-ko.github.io/mom-index/](https://marc-ko.github.io/mom-index/)

The dashboard may contain both English and Chinese. The data sources, search terms, and classification signals are Chinese-language by nature, while this README explains the fork and workflow in English.

## Core Idea

```text
When market tips reach everyday non-professional investors, the crowd may already be late.
```

Each covered sector is scored independently with three visible metrics:

| Metric | Meaning |
| --- | --- |
| **Mom Index** | Overall retail sentiment heat, from 0 to 100 |
| **Mom Buy** | FOMO / chase-buying pressure, from 0 to 100 |
| **Mom Sell** | Panic-selling pressure, from 0 to 100 |

## Reading The Index

| Range | Signal | Interpretation |
| --- | --- | --- |
| 0-20 | Very cold | Beginners are quiet; could indicate low retail participation |
| 20-40 | Normal | Retail activity is present but not extreme |
| 40-60 | Warming up | Retail attention is rising; watch closely |
| 60-75 | High alert | Retail crowding is elevated |
| 75-100 | Extreme heat | Shoeshine-boy moment; strong contrarian warning |

## Covered Sectors

| Sector | Eastmoney Guba Code | ETF |
| --- | --- | --- |
| Nasdaq | `of159941` | `513100` |
| Gold | `of518880` | `518880` |
| CPO / Communications | `of515880` | `515880` |
| Semiconductor | `of512480` | `512480` |

## Current Data Flow

1. Scrape Eastmoney Guba board titles for the tracked ETF sectors.
2. Scrape Rednote/Xiaohongshu search results through Playwright using a local logged-in browser profile.
3. Classify posts with keyword-based beginner, sentiment, and buy/sell intent signals.
4. Calculate sector indices and buy/sell sub-indices.
5. Write JSON data into `data/` and sync it into `frontend/data/` for the static dashboard.

## Rednote / Xiaohongshu Login

Use a persistent Playwright profile so you can log in once and reuse the saved session. Cookies stay inside the local browser profile and are not printed, exported, or committed.

```bash
# First-time setup: install the Chromium runtime used by Playwright
python -m playwright install chromium

# Open Rednote with a persistent local profile and log in manually
python xhs_profile.py

# Run the complete collection and index pipeline after login
python pipeline.py
```

The profile is stored at `.browser_profiles/xhs/` by default. It is ignored by Git and should remain local.

Useful environment variables:

| Variable | Purpose |
| --- | --- |
| `MOM_INDEX_XHS_PROFILE` | Override the Playwright profile directory |
| `MOM_INDEX_REDNOTE_BASE_URL` | Override the Rednote base URL, default `https://www.rednote.com` |
| `MOM_INDEX_XHS_HEADLESS` | Set to `1` for headless collection after login is stable |
| `MOM_INDEX_PROXY` | Optional proxy for Eastmoney requests, for example `http://127.0.0.1:7890` |

## Quick Start

```bash
# Install Python dependencies
pip install -r requirements.txt
python -m playwright install chromium

# Optional but recommended before Rednote scraping
python xhs_profile.py

# Run data collection, analysis, and index generation
python pipeline.py

# Serve the local dashboard
cd frontend
python -m http.server 8765
```

Open [http://localhost:8765/dashboard.html](http://localhost:8765/dashboard.html).

## Daily Local Schedule

This project should run on the local Windows machine when Rednote/Xiaohongshu
collection is enabled, because Playwright depends on the local logged-in browser
profile in `.browser_profiles/xhs/`.

Install an 8:00 AM daily Windows scheduled task:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install_daily_task.ps1 -Time 08:00 -PublishPages
```

The scheduled runner executes `python pipeline.py`. With `-PublishPages`, it
publishes the generated dashboard and history JSON to `gh-pages`, including the
top 5 beginner-signal posts per sector. Raw scraped caches are not published.

To also create a daily GitHub issue report, install the task with `-PushReport`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install_daily_task.ps1 -Time 08:00 -PublishPages -PushReport
```

After a successful local run, `-PushReport` generates `.github/ISSUE_TEMPLATE.md`
from `data/dashboard_data.json`, commits only the safe public report files, and
pushes them to the `marcko` remote. The GitHub Actions workflow then opens a
dated issue from that template. In the GitHub repository settings, make sure
Actions are allowed to create issues with the repository `GITHUB_TOKEN`.

You can generate the issue template without running the full pipeline:

```bash
python scripts/generate_issue_template.py
```

## Project Structure

```text
mom-index/
├── pipeline.py                  # Main flow: collect -> analyze -> index -> store
├── scripts/
│   ├── install_daily_task.ps1    # Register Windows Task Scheduler job
│   └── run_daily.ps1             # Daily pipeline runner and Pages publish
├── sync_data.py                 # Data sync helper: data/ -> frontend/data/
├── xhs_profile.py               # Rednote login/profile helper, no cookie export
├── collectors/
│   ├── anti_detection.py        # User-agent rotation, stealth scripts, delays
│   ├── guba_collector.py        # Eastmoney Guba scraper
│   ├── xhs_collector.py         # Legacy rnote.dev API path
│   └── xhs_playwright.py        # Rednote/Xiaohongshu Playwright scraper
├── analyzer/
│   ├── llm_analyzer.py          # Keyword-based classification engine
│   └── index_calculator.py      # Mom Index and buy/sell sub-index formulas
├── frontend/
│   ├── dashboard.html           # Static dashboard using Chart.js
│   └── data/                    # Dashboard JSON data
├── data/
│   ├── dashboard_data.json      # Main dashboard data source
│   ├── history.json             # Historical records
│   └── xhs_posts.json           # Rednote/XHS collection cache
├── requirements.txt
├── .gitignore
└── README.md
```

## Data Sources

| Source | Status | Notes |
| --- | --- | --- |
| Eastmoney Guba | Working | Public ETF board pages, no login required |
| Rednote / Xiaohongshu via Playwright | Experimental | Requires a local logged-in browser profile |
| rnote.dev API | Legacy / optional | Requires external service quota |
| x-mcp path | Legacy / unstable | Login/search flow may be blocked by platform risk controls |

## Classification Method

The current classifier is rule-based. It scores title text using Chinese-language beginner-investor signals such as:

| Signal Dimension | Weight Direction | Examples |
| --- | --- | --- |
| Self-identified beginner | Positive | 小白, 新手, 宝妈 |
| Knowledge-seeking | Positive | 怎么买, 在哪看, 请教 |
| Decision dependence | Positive | 该不该, 要不要, 还能买吗 |
| Panic emotion | Positive | 亏麻了, 好慌, 心态崩了 |
| Herd behavior | Positive | 听博主说, 朋友推荐 |
| Excessive optimism | Positive | 梭哈, 满仓干, 稳赚 |
| Professional terminology | Negative | PE, PB, 估值, 溢价率 |

Buy/sell intent is detected with Chinese trigger phrases such as:

- Buy/FOMO: 上车, 冲, 加仓, 买了, 还能买吗, 想买, 心动
- Sell/panic: 割肉, 止损, 清仓, 亏了, 要不要走, 跌麻了

### Semantic Classification Mode

The default classifier remains deterministic and can run offline. For more
accurate classification, set:

```powershell
$env:MOM_INDEX_CLASSIFIER="semantic"
```

Semantic mode separates `author_is_beginner` from `targets_beginners`, so a
post like `新手买美股？看这篇就够了` is treated as beginner-facing education,
not automatically as a beginner-authored post.

Optional OpenRouter-backed semantic classification uses the free models router:

```powershell
$env:MOM_INDEX_CLASSIFIER="semantic"
$env:MOM_INDEX_SEMANTIC_PROVIDER="openrouter"
$env:MOM_INDEX_SEMANTIC_MODEL="openrouter/free"
$env:OPENROUTER_API_KEY="..."
```

Without `OPENROUTER_API_KEY`, semantic mode uses the deterministic local
fallback. The key should only be supplied through the shell environment and
must not be committed.

## Index Formula

```text
Mom Index = beginner_ratio * 0.40
          + beginner_intensity * 0.25
          + sentiment_extremity * 0.20
          + signal_purity * 0.15

Mom Buy  = beginner_buy_ratio * 50
         + beginner_heat * 30
         + buy_intensity * 20

Mom Sell = beginner_sell_ratio * 50
         + beginner_heat * 30
         + sell_intensity * 20
```

This fork intentionally does not include raw collection volume as an `activity_signal` in the formula, because page sample size can make the index look more confident than the underlying data deserves.

## Dashboard

The static dashboard includes:

- Sector index cards with buy/sell sub-indices
- Historical index lines powered by Chart.js
- Recent high-signal beginner posts with classification reasoning
- Dark responsive layout
- Chinese labels where they are closer to the source data semantics

## Known Limitations

- Guba has a lower beginner-signal density than Rednote/Xiaohongshu.
- Rednote/Xiaohongshu scraping depends on an authenticated local Playwright profile and can be affected by platform risk controls.
- The classifier is keyword-based, not a full semantic LLM pipeline.
- There is no market backtest yet, so this should be treated as an exploratory sentiment indicator.
- This project is for research and learning only. It is not investment advice.

## Roadmap

- [ ] More stable Rednote/Xiaohongshu collection
- [ ] Replace or augment keyword rules with semantic classification
- [ ] Add Weibo/Douyin-style social sources
- [ ] Scheduled daily collection
- [ ] Daily push notification through Telegram/WeChat/etc.
- [ ] Historical backtest against sector price data

## Tech Stack

- Python + `requests` + `playwright`
- Chart.js 4.x
- Static HTML/CSS dashboard
- Eastmoney Guba HTML parsing
- Rednote/Xiaohongshu Playwright scraping

## Attribution

This repository is an English fork of [mihang123/mom-index](https://github.com/mihang123/mom-index). Credit for the original concept and project foundation belongs to the original owner. Changes in this fork focus on English documentation, Rednote/Xiaohongshu Playwright handling, formula cleanup, and GitHub Pages publishing.

## License

MIT. Research/education only; not financial advice.
