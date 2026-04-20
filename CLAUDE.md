# ChatGPT Data Export Analysis Project

## Project Overview
Analytics pipeline and interactive dashboard for ChatGPT conversation data export.

## Architecture

```
<project-root>/
├── <export-dir>/               # Raw ChatGPT export (conversations-000.json … conversations-NNN.json)
├── analyze.py                  # Base analysis → analysis_results.json
├── analyze_dashboard.py        # Extended analysis → dashboard_data.json
├── dashboard.py                # Dash app (6 tabs, dark theme, Plotly)
├── dashboard_data.json         # Pre-computed dashboard data
├── analysis_results.json       # Full analysis output
├── Dockerfile                  # Python 3.13-slim container
├── docker-compose.yml          # dashboard + analyze services
└── requirements.txt            # dash, plotly[express], dbc, numpy
```

## Data Pipeline

1. **Raw export** → unzip ChatGPT export into a subfolder; scripts auto-discover it
2. `analyze.py` → `analysis_results.json` (overview stats, topic/language/model distributions, NLP metrics)
3. `analyze_dashboard.py` → `dashboard_data.json` (cross-dimensional: topic×month, hour×day heatmap, model×month, sophistication×topic)
4. `dashboard.py` → Interactive Dash app at `http://localhost:8050`

## Commands

```bash
# Regenerate base analysis (auto-discovers export subfolder)
py -X utf8 analyze.py

# Regenerate dashboard data
py -X utf8 analyze_dashboard.py

# Run dashboard locally
py dashboard.py

# Docker
docker compose up dashboard -d          # start
docker compose down                     # stop
docker compose build dashboard          # rebuild after code changes
docker compose run --rm analyze         # regenerate data in container
```

## Key Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `CHATGPT_EXPORT` | auto-discovered subfolder | Path to raw export directory |
| `DASHBOARD_DATA` | `dashboard_data.json` | Path to dashboard data file |
| `ANALYSIS_RESULTS` | `analysis_results.json` | Path to full analysis output |

**Auto-discovery**: If `CHATGPT_EXPORT` is not set, analysis scripts scan the current directory for the first subfolder containing `conversations-000.json`.

## Conventions

- Python via `py` command (Windows launcher) or `python`/`python3` on Linux/Mac
- Use `py -X utf8` when printing Unicode to console (Windows cp1252 encoding issue)
- All analysis scripts use stdlib only (json, re, collections, datetime) — no pandas/numpy in analysis
- Dashboard uses: dash 4.0, plotly 6.6, dash-bootstrap-components 2.0, numpy
- Dark theme: `plotly_dark` template, bg `#0f1117`, card bg `#1a1d27`, accent `#636efa`
- All charts interactive with hover tooltips

## Dashboard Tabs

| Tab | Charts |
|-----|--------|
| Activity & Temporal | Monthly area (dual-axis), Hour×Day heatmap, Hourly bar, Day-of-week bar |
| Topics & Domains | Topic treemap, Topic evolution stacked area, Programming langs bar, Natural langs donut |
| Prompt Intelligence | Sophistication donut, Communication radar, Prompt length histogram, Sophistication×topic stacked bar |
| Models & Tools | Model donut, Model evolution area, Custom GPTs bar, Voice pie |
| Conversation Depth | Depth histogram, Top 25 longest conversations table |
| Word Patterns | Title keywords bar, Bigrams bar, Trigrams bar |

## Adding New Visualizations

1. Add computed data to `analyze_dashboard.py` output dict
2. Regenerate: `py -X utf8 analyze_dashboard.py`
3. Add chart in `dashboard.py` under the appropriate tab
4. Rebuild Docker if needed: `docker compose build dashboard`

## Data Schema: dashboard_data.json

```
overview          → {total_conversations, total_prompts, date_range_from/to, months_active, avg_per_month, voice_conversations, attachment_prompts}
months            → ["2022-12", "2023-01", ...] (sorted)
topic_distribution → {topic_name: count}
topic_month_matrix → {topic_name: [count_per_month]}
hour_day_heatmap  → [[count]] (24 rows × 7 cols, hour × weekday)
hourly            → [count] (24 entries)
daily             → {day_name: count}
monthly_activity  → {YYYY-MM: count}
monthly_active_days → {YYYY-MM: unique_days}
prompt_length_buckets → {bucket_label: count}
conversation_depth_buckets → {bucket_label: count}
longest_conversations → [{title, turns, model}]
model_usage       → {model_name: count}
model_month_matrix → {model_name: [count_per_month]} (top 6)
programming_languages → {lang: count}
natural_languages → {lang: count}
sophistication    → {basic/intermediate/advanced: count}
sophistication_by_topic → {topic: {basic, intermediate, advanced}}
communication_style → {sentence_types, polite_pct, informal_pct, context_pct, code_pct, short_pct}
code_by_topic     → {topic: {with_code, without_code}}
custom_gpts       → {gpt_id: count} (top 10)
voice_types       → {voice_name: count}
title_keywords    → {word: count} (top 40)
top_bigrams       → {phrase: count} (top 25)
top_trigrams      → {phrase: count} (top 15)
```

## Conversation JSON Structure (raw export)

Each `conversations-NNN.json` is an array of conversation objects:
```
{
  title, create_time (unix), update_time, default_model_slug,
  gizmo_id (custom GPT), voice, is_archived, is_starred,
  mapping: {
    node_id: {
      message: {
        author: {role: "user"|"assistant"|"system"},
        content: {content_type, parts: [string | attachment_object]},
        create_time
      }
    }
  }
}
```
