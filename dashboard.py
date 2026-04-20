"""
ChatGPT Usage Analytics Dashboard
Interactive Dash application with 6 tabs.
Run: py dashboard.py → http://localhost:8050
"""
import json
import dash
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px

# ─── Load data ────────────────────────────────────────────────────
import os
DATA_PATH = os.environ.get("DASHBOARD_DATA", "dashboard_data.json")
with open(DATA_PATH, "r", encoding="utf-8") as f:
    D = json.load(f)

OV = D["overview"]
MONTHS = D["months"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# ─── Color palette ────────────────────────────────────────────────
COLORS = px.colors.qualitative.Set3
BG = "#0f1117"
CARD_BG = "#1a1d27"
TEXT = "#e0e0e0"
ACCENT = "#636efa"
TEMPLATE = "plotly_dark"

def card_style():
    return {
        "backgroundColor": CARD_BG,
        "borderRadius": "12px",
        "padding": "20px",
        "marginBottom": "20px",
        "border": "1px solid #2a2d3a",
    }

# ─── Metric cards ─────────────────────────────────────────────────
def metric_card(label, value, sub=""):
    return dbc.Col(html.Div([
        html.H2(str(value), style={"color": ACCENT, "margin": "0", "fontSize": "2rem", "fontWeight": "700"}),
        html.P(label, style={"color": TEXT, "margin": "4px 0 0 0", "fontSize": "0.85rem"}),
        html.Small(sub, style={"color": "#888"}) if sub else None,
    ], style={**card_style(), "textAlign": "center", "padding": "16px"}), md=2)

header = dbc.Row([
    metric_card("Conversations", f"{OV['total_conversations']:,}"),
    metric_card("User Prompts", f"{OV['total_prompts']:,}"),
    metric_card("Months Active", OV["months_active"]),
    metric_card("Avg/Month", OV["avg_per_month"]),
    metric_card("Voice Convos", OV["voice_conversations"]),
    metric_card("Attachments", OV["attachment_prompts"]),
], className="mb-3 g-2")

# ═══════════════════════════════════════════════════════════════════
# TAB 1: Activity & Temporal
# ═══════════════════════════════════════════════════════════════════

# Monthly activity area chart
monthly_vals = [D["monthly_activity"].get(m, 0) for m in MONTHS]
monthly_days = [D["monthly_active_days"].get(m, 0) for m in MONTHS]
fig_monthly = go.Figure()
fig_monthly.add_trace(go.Scatter(
    x=MONTHS, y=monthly_vals, mode="lines+markers", name="Prompts",
    fill="tozeroy", line=dict(color=ACCENT, width=2), marker=dict(size=4),
))
fig_monthly.add_trace(go.Bar(
    x=MONTHS, y=monthly_days, name="Active Days", marker_color="rgba(255,165,0,0.4)",
    yaxis="y2",
))
fig_monthly.update_layout(
    template=TEMPLATE, title="Monthly Activity", height=350,
    margin=dict(l=40, r=40, t=50, b=40),
    yaxis=dict(title="Prompts"),
    yaxis2=dict(title="Active Days", overlaying="y", side="right", range=[0, 31]),
    legend=dict(orientation="h", y=1.12),
    paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
)

# Hour × Day heatmap
heatmap_data = D["hour_day_heatmap"]
fig_heatmap = go.Figure(go.Heatmap(
    z=heatmap_data,
    x=DAY_NAMES,
    y=[f"{h:02d}:00" for h in range(24)],
    colorscale="Inferno",
    hovertemplate="Day: %{x}<br>Hour: %{y}<br>Prompts: %{z}<extra></extra>",
))
fig_heatmap.update_layout(
    template=TEMPLATE, title="Activity Heatmap (Hour x Day)", height=500,
    margin=dict(l=60, r=20, t=50, b=40),
    paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
)

# Hourly bar
fig_hourly = go.Figure(go.Bar(
    x=[f"{h:02d}:00" for h in range(24)],
    y=D["hourly"],
    marker_color=[ACCENT if h == D["hourly"].index(max(D["hourly"])) else "rgba(99,110,250,0.5)" for h in range(24)],
))
fig_hourly.update_layout(
    template=TEMPLATE, title="Hourly Distribution", height=300,
    margin=dict(l=40, r=20, t=50, b=40),
    paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
)

# Day of week bar
daily_vals = [D["daily"].get(d, 0) for d in DAY_NAMES]
fig_daily = go.Figure(go.Bar(
    x=DAY_NAMES, y=daily_vals,
    marker_color=["#ff6b6b" if d in ["Saturday", "Sunday"] else ACCENT for d in DAY_NAMES],
))
fig_daily.update_layout(
    template=TEMPLATE, title="Day of Week", height=300,
    margin=dict(l=40, r=20, t=50, b=40),
    paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
)

tab1 = html.Div([
    html.Div(dcc.Graph(figure=fig_monthly), style=card_style()),
    html.Div(dcc.Graph(figure=fig_heatmap), style=card_style()),
    dbc.Row([
        dbc.Col(html.Div(dcc.Graph(figure=fig_hourly), style=card_style()), md=6),
        dbc.Col(html.Div(dcc.Graph(figure=fig_daily), style=card_style()), md=6),
    ]),
])

# ═══════════════════════════════════════════════════════════════════
# TAB 2: Topics & Domains
# ═══════════════════════════════════════════════════════════════════

# Topic treemap
topic_dist = D["topic_distribution"]
fig_treemap = go.Figure(go.Treemap(
    labels=list(topic_dist.keys()),
    parents=[""] * len(topic_dist),
    values=list(topic_dist.values()),
    textinfo="label+value+percent root",
    marker=dict(colors=COLORS[:len(topic_dist)]),
    hovertemplate="<b>%{label}</b><br>Prompts: %{value}<br>Share: %{percentRoot:.1%}<extra></extra>",
))
fig_treemap.update_layout(
    template=TEMPLATE, title="Topic Distribution (Treemap)", height=450,
    margin=dict(l=10, r=10, t=50, b=10),
    paper_bgcolor=CARD_BG,
)

# Topic evolution stacked area
topic_matrix = D["topic_month_matrix"]
top_topics = list(topic_dist.keys())[:8]  # top 8 for readability
fig_topic_evo = go.Figure()
for i, topic in enumerate(top_topics):
    if topic in topic_matrix:
        fig_topic_evo.add_trace(go.Scatter(
            x=MONTHS, y=topic_matrix[topic], name=topic,
            stackgroup="one", mode="lines",
            line=dict(width=0.5), fillcolor=COLORS[i % len(COLORS)],
        ))
fig_topic_evo.update_layout(
    template=TEMPLATE, title="Topic Evolution Over Time", height=400,
    margin=dict(l=40, r=20, t=50, b=40),
    legend=dict(orientation="h", y=-0.15, font=dict(size=10)),
    paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
)

# Programming languages horizontal bar
prog = D["programming_languages"]
prog_sorted = dict(sorted(prog.items(), key=lambda x: x[1]))
fig_prog = go.Figure(go.Bar(
    x=list(prog_sorted.values()),
    y=list(prog_sorted.keys()),
    orientation="h",
    marker_color=ACCENT,
))
fig_prog.update_layout(
    template=TEMPLATE, title="Programming Languages", height=350,
    margin=dict(l=110, r=20, t=50, b=40),
    paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
)

# Natural languages donut
nat = D["natural_languages"]
fig_nat = go.Figure(go.Pie(
    labels=list(nat.keys()),
    values=list(nat.values()),
    hole=0.5,
    marker=dict(colors=COLORS),
))
fig_nat.update_layout(
    template=TEMPLATE, title="Natural Languages", height=350,
    margin=dict(l=20, r=20, t=50, b=40),
    paper_bgcolor=CARD_BG,
)

tab2 = html.Div([
    html.Div(dcc.Graph(figure=fig_treemap), style=card_style()),
    html.Div(dcc.Graph(figure=fig_topic_evo), style=card_style()),
    dbc.Row([
        dbc.Col(html.Div(dcc.Graph(figure=fig_prog), style=card_style()), md=6),
        dbc.Col(html.Div(dcc.Graph(figure=fig_nat), style=card_style()), md=6),
    ]),
])

# ═══════════════════════════════════════════════════════════════════
# TAB 3: Prompt Intelligence
# ═══════════════════════════════════════════════════════════════════

# Sophistication donut
soph = D["sophistication"]
fig_soph = go.Figure(go.Pie(
    labels=["Basic (<30 words)", "Intermediate", "Advanced (detailed)"],
    values=[soph.get("basic", 0), soph.get("intermediate", 0), soph.get("advanced", 0)],
    hole=0.5,
    marker=dict(colors=["#ff6b6b", "#ffd93d", "#6bcb77"]),
))
fig_soph.update_layout(
    template=TEMPLATE, title="Prompt Sophistication", height=350,
    margin=dict(l=20, r=20, t=50, b=20),
    paper_bgcolor=CARD_BG,
)

# Communication style radar
style = D["communication_style"]
st = style["sentence_types"]
total_p = OV["total_prompts"]
categories = ["Imperative", "Interrogative", "Declarative", "Polite", "Informal", "With Context", "With Code", "Short (<10w)"]
values = [
    st.get("imperative", 0) / total_p * 100,
    st.get("interrogative", 0) / total_p * 100,
    st.get("declarative", 0) / total_p * 100,
    style["polite_pct"],
    style["informal_pct"],
    style["context_pct"],
    style["code_pct"],
    style["short_pct"],
]
fig_radar = go.Figure(go.Scatterpolar(
    r=values + [values[0]],
    theta=categories + [categories[0]],
    fill="toself",
    fillcolor="rgba(99,110,250,0.3)",
    line=dict(color=ACCENT),
))
fig_radar.update_layout(
    template=TEMPLATE, title="Communication Style Radar", height=380,
    polar=dict(
        radialaxis=dict(visible=True, range=[0, max(values) * 1.1]),
        bgcolor=CARD_BG,
    ),
    margin=dict(l=60, r=60, t=50, b=40),
    paper_bgcolor=CARD_BG,
)

# Prompt length distribution
lb = D["prompt_length_buckets"]
fig_length = go.Figure(go.Bar(
    x=list(lb.keys()), y=list(lb.values()),
    marker_color=ACCENT,
    text=list(lb.values()), textposition="outside",
))
fig_length.update_layout(
    template=TEMPLATE, title="Prompt Length Distribution (words)", height=320,
    margin=dict(l=40, r=20, t=50, b=40),
    xaxis_title="Word count range",
    paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
)

# Sophistication by topic grouped bar
soph_by_topic = D["sophistication_by_topic"]
top_soph_topics = list(topic_dist.keys())[:10]
soph_basic = [soph_by_topic.get(t, {}).get("basic", 0) for t in top_soph_topics]
soph_inter = [soph_by_topic.get(t, {}).get("intermediate", 0) for t in top_soph_topics]
soph_adv = [soph_by_topic.get(t, {}).get("advanced", 0) for t in top_soph_topics]
fig_soph_topic = go.Figure()
fig_soph_topic.add_trace(go.Bar(name="Basic", x=top_soph_topics, y=soph_basic, marker_color="#ff6b6b"))
fig_soph_topic.add_trace(go.Bar(name="Intermediate", x=top_soph_topics, y=soph_inter, marker_color="#ffd93d"))
fig_soph_topic.add_trace(go.Bar(name="Advanced", x=top_soph_topics, y=soph_adv, marker_color="#6bcb77"))
fig_soph_topic.update_layout(
    template=TEMPLATE, title="Sophistication by Topic", height=400,
    barmode="stack",
    margin=dict(l=40, r=20, t=50, b=100),
    xaxis_tickangle=-35,
    legend=dict(orientation="h", y=1.1),
    paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
)

tab3 = html.Div([
    dbc.Row([
        dbc.Col(html.Div(dcc.Graph(figure=fig_soph), style=card_style()), md=5),
        dbc.Col(html.Div(dcc.Graph(figure=fig_radar), style=card_style()), md=7),
    ]),
    html.Div(dcc.Graph(figure=fig_length), style=card_style()),
    html.Div(dcc.Graph(figure=fig_soph_topic), style=card_style()),
])

# ═══════════════════════════════════════════════════════════════════
# TAB 4: Models & Tools
# ═══════════════════════════════════════════════════════════════════

# Model donut
model_data = D["model_usage"]
fig_model = go.Figure(go.Pie(
    labels=list(model_data.keys()),
    values=list(model_data.values()),
    hole=0.45,
    marker=dict(colors=px.colors.qualitative.Plotly),
))
fig_model.update_layout(
    template=TEMPLATE, title="Model Usage Distribution", height=400,
    margin=dict(l=20, r=20, t=50, b=20),
    paper_bgcolor=CARD_BG,
)

# Model evolution over time
model_matrix = D["model_month_matrix"]
fig_model_evo = go.Figure()
model_colors = px.colors.qualitative.Plotly
for i, (model, values) in enumerate(model_matrix.items()):
    fig_model_evo.add_trace(go.Scatter(
        x=MONTHS, y=values, name=model,
        stackgroup="one", mode="lines",
        line=dict(width=0.5),
    ))
fig_model_evo.update_layout(
    template=TEMPLATE, title="Model Usage Over Time (Top 6)", height=380,
    margin=dict(l=40, r=20, t=50, b=40),
    legend=dict(orientation="h", y=-0.15, font=dict(size=10)),
    paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
)

# Custom GPTs bar
gpts = D["custom_gpts"]
fig_gpts = go.Figure(go.Bar(
    x=list(gpts.values()),
    y=[g[:20] for g in gpts.keys()],
    orientation="h",
    marker_color="#ff6b6b",
    text=list(gpts.values()), textposition="outside",
))
fig_gpts.update_layout(
    template=TEMPLATE, title="Top Custom GPTs (by usage)", height=350,
    margin=dict(l=160, r=40, t=50, b=40),
    paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
)

# Voice pie
voice = D["voice_types"]
fig_voice = go.Figure(go.Pie(
    labels=list(voice.keys()),
    values=list(voice.values()),
    hole=0.4,
    marker=dict(colors=["#6bcb77", "#ffd93d", "#ff6b6b", "#4ecdc4"]),
))
fig_voice.update_layout(
    template=TEMPLATE, title="Voice Usage", height=350,
    margin=dict(l=20, r=20, t=50, b=20),
    paper_bgcolor=CARD_BG,
)

tab4 = html.Div([
    dbc.Row([
        dbc.Col(html.Div(dcc.Graph(figure=fig_model), style=card_style()), md=6),
        dbc.Col(html.Div(dcc.Graph(figure=fig_model_evo), style=card_style()), md=6),
    ]),
    dbc.Row([
        dbc.Col(html.Div(dcc.Graph(figure=fig_gpts), style=card_style()), md=6),
        dbc.Col(html.Div(dcc.Graph(figure=fig_voice), style=card_style()), md=6),
    ]),
])

# ═══════════════════════════════════════════════════════════════════
# TAB 5: Conversation Depth
# ═══════════════════════════════════════════════════════════════════

# Depth distribution
db = D["conversation_depth_buckets"]
fig_depth = go.Figure(go.Bar(
    x=list(db.keys()), y=list(db.values()),
    marker_color=ACCENT,
    text=list(db.values()), textposition="outside",
))
fig_depth.update_layout(
    template=TEMPLATE, title="Conversation Depth Distribution (turns)", height=350,
    margin=dict(l=40, r=20, t=50, b=40),
    xaxis_title="Number of turns",
    paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
)

# Top 25 longest conversations table
longest = D["longest_conversations"]
table_data = [{"#": i+1, "Title": c["title"][:60], "Turns": c["turns"], "Model": c["model"]} for i, c in enumerate(longest)]
fig_table = dash_table.DataTable(
    data=table_data,
    columns=[{"name": col, "id": col} for col in ["#", "Title", "Turns", "Model"]],
    style_header={"backgroundColor": "#2a2d3a", "color": TEXT, "fontWeight": "bold", "border": "1px solid #3a3d4a"},
    style_cell={"backgroundColor": CARD_BG, "color": TEXT, "border": "1px solid #2a2d3a", "padding": "8px", "textAlign": "left", "fontSize": "13px"},
    style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#1e2130"}],
    page_size=25,
    sort_action="native",
)

tab5 = html.Div([
    html.Div(dcc.Graph(figure=fig_depth), style=card_style()),
    html.Div([
        html.H5("Top 25 Longest Conversations", style={"color": TEXT, "marginBottom": "12px"}),
        fig_table,
    ], style=card_style()),
])

# ═══════════════════════════════════════════════════════════════════
# TAB 6: Word Patterns
# ═══════════════════════════════════════════════════════════════════

# Title keywords
tk = D["title_keywords"]
tk_sorted = dict(sorted(tk.items(), key=lambda x: x[1]))
tk_items = list(tk_sorted.items())[-30:]
fig_title_kw = go.Figure(go.Bar(
    x=[v for _, v in tk_items],
    y=[k for k, _ in tk_items],
    orientation="h",
    marker_color=ACCENT,
))
fig_title_kw.update_layout(
    template=TEMPLATE, title="Top 30 Conversation Title Keywords", height=600,
    margin=dict(l=120, r=20, t=50, b=40),
    paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
)

# Bigrams
bg = D["top_bigrams"]
bg_sorted = dict(sorted(bg.items(), key=lambda x: x[1]))
bg_items = list(bg_sorted.items())[-20:]
fig_bigrams = go.Figure(go.Bar(
    x=[v for _, v in bg_items],
    y=[k for k, _ in bg_items],
    orientation="h",
    marker_color="#ff6b6b",
))
fig_bigrams.update_layout(
    template=TEMPLATE, title="Top 20 Bigrams", height=500,
    margin=dict(l=200, r=20, t=50, b=40),
    paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
)

# Trigrams
tg = D["top_trigrams"]
tg_sorted = dict(sorted(tg.items(), key=lambda x: x[1]))
tg_items = list(tg_sorted.items())[-15:]
fig_trigrams = go.Figure(go.Bar(
    x=[v for _, v in tg_items],
    y=[k for k, _ in tg_items],
    orientation="h",
    marker_color="#6bcb77",
))
fig_trigrams.update_layout(
    template=TEMPLATE, title="Top 15 Trigrams", height=450,
    margin=dict(l=300, r=20, t=50, b=40),
    paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
)

tab6 = html.Div([
    html.Div(dcc.Graph(figure=fig_title_kw), style=card_style()),
    dbc.Row([
        dbc.Col(html.Div(dcc.Graph(figure=fig_bigrams), style=card_style()), md=6),
        dbc.Col(html.Div(dcc.Graph(figure=fig_trigrams), style=card_style()), md=6),
    ]),
])

# ═══════════════════════════════════════════════════════════════════
# APP LAYOUT
# ═══════════════════════════════════════════════════════════════════

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    title="ChatGPT Analytics",
)

app.layout = dbc.Container([
    html.Div([
        html.H1("ChatGPT Usage Analytics", style={"color": TEXT, "fontWeight": "700", "marginBottom": "4px"}),
        html.P(
            f"{OV['date_range_from']} to {OV['date_range_to']}  |  {OV['months_active']} months  |  {OV['total_conversations']:,} conversations",
            style={"color": "#888", "fontSize": "0.9rem"},
        ),
    ], style={"padding": "20px 0 10px 0"}),

    header,

    dbc.Tabs([
        dbc.Tab(tab1, label="Activity & Temporal", tab_id="tab1"),
        dbc.Tab(tab2, label="Topics & Domains", tab_id="tab2"),
        dbc.Tab(tab3, label="Prompt Intelligence", tab_id="tab3"),
        dbc.Tab(tab4, label="Models & Tools", tab_id="tab4"),
        dbc.Tab(tab5, label="Conversation Depth", tab_id="tab5"),
        dbc.Tab(tab6, label="Word Patterns", tab_id="tab6"),
    ], active_tab="tab1", className="mb-3"),

], fluid=True, style={"backgroundColor": BG, "minHeight": "100vh", "padding": "0 20px 40px 20px"})

if __name__ == "__main__":
    print("Dashboard running at http://localhost:8050")
    app.run(debug=False, host="0.0.0.0", port=8050)
