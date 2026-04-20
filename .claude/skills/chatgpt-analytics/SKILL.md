---
name: chatgpt-analytics
description: Set up, run, or extend the ChatGPT export analytics dashboard. Use when the user asks to analyze a ChatGPT export, regenerate dashboard data, add a new chart, or run the dashboard.
argument-hint: [task]
---

# ChatGPT Export Analytics

## Pipeline

```
<export-dir>/          # unzipped ChatGPT export (conversations-000.json …)
   ↓ analyze_dashboard.py
dashboard_data.json
   ↓ dashboard.py
http://localhost:8050
```

## Run locally

```bash
# Auto-discovers export subfolder, writes dashboard_data.json
py -X utf8 analyze_dashboard.py

# Launch dashboard
py dashboard.py
```

## Run with Docker

```bash
unzip chatgpt-export.zip -d export/
docker compose run --rm --profile tools analyze   # generates dashboard_data.json
docker compose up dashboard -d                    # serves on :8050
```

## Path configuration (env vars override defaults)

| Variable | Default |
|---|---|
| `CHATGPT_EXPORT` | first subfolder containing `conversations-000.json` |
| `DASHBOARD_DATA` | `dashboard_data.json` |
| `ANALYSIS_RESULTS` | `analysis_results.json` |

## Reuse for a new export

1. Unzip new export into any subfolder (or point `CHATGPT_EXPORT` at it)
2. `py -X utf8 analyze_dashboard.py`
3. `py dashboard.py` (or `docker compose restart dashboard`)

## Add a new chart

1. Add computed data to the output dict in `analyze_dashboard.py`
2. `py -X utf8 analyze_dashboard.py`
3. Add the chart in `dashboard.py` under the relevant tab
4. `docker compose build dashboard` if running in Docker

## Dashboard tabs

| Tab | Content |
|-----|---------|
| Activity & Temporal | Monthly trends, hour×day heatmap, peak hours, busiest weekday |
| Topics & Domains | Topic treemap, topic evolution, programming & natural languages |
| Prompt Intelligence | Sophistication, communication style radar, prompt length |
| Models & Tools | Model usage, custom GPTs, voice conversations |
| Conversation Depth | Depth histogram, top 25 longest threads |
| Word Patterns | Title keywords, bigrams, trigrams |
