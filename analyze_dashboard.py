"""
Extended analysis script that produces dashboard_data.json
with cross-dimensional data for the Dash dashboard.
"""
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

def _find_export_dir():
    """Auto-discover ChatGPT export dir: first subfolder containing conversations-000.json."""
    for entry in sorted(os.scandir("."), key=lambda e: e.name):
        if entry.is_dir() and os.path.exists(os.path.join(entry.path, "conversations-000.json")):
            return entry.path
    return "."


BASE = os.environ.get("CHATGPT_EXPORT") or _find_export_dir()
OUTPUT = os.environ.get("DASHBOARD_DATA", "dashboard_data.json")

# ─── Load all conversations ──────────────────────────────────────
all_conversations = []
i = 0
while True:
    fpath = os.path.join(BASE, f"conversations-{i:03d}.json")
    if not os.path.exists(fpath):
        break
    with open(fpath, "r", encoding="utf-8") as f:
        all_conversations.extend(json.load(f))
    i += 1

print(f"Loaded {len(all_conversations)} conversations")

# ─── Topic keywords (same as analyze.py) ─────────────────────────
topic_keywords = {
    "Software Development": ["code", "function", "class", "api", "bug", "error", "debug", "implement", "refactor", "typescript", "javascript", "python", "php", "react", "node", "sql", "database", "git", "deploy", "docker", "test", "unit test", "symfony", "laravel", "nextjs", "next.js", "nestjs", "express", "mongodb", "postgres", "mysql", "redis", "aws", "azure", "gcp", "terraform", "webpack", "vite", "eslint", "npm", "yarn", "component", "hook", "state", "props", "interface", "migration", "schema", "endpoint", "route", "middleware", "controller", "service", "repository", "entity", "dto", "graphql", "rest", "crud", "authentication", "authorization", "jwt", "oauth", "css", "html", "tailwind", "scss"],
    "Writing & Content": ["write", "blog", "article", "content", "copy", "newsletter", "story", "essay", "draft", "proofread", "tone", "headline", "caption", "script", "presentation", "document"],
    "Product & UX": ["design", "ux", "ui", "user experience", "wireframe", "mockup", "prototype", "figma", "user flow", "persona", "usability", "accessibility", "responsive"],
    "Automation": ["automate", "automation", "script", "cron", "webhook", "zapier", "make.com", "n8n", "workflow", "bot", "scrape", "crawl"],
    "Education": ["learn", "explain", "tutorial", "course", "concept", "understand", "how does", "what is", "difference between", "example of", "teach me"],
    "DevOps": ["kubernetes", "k8s", "docker", "container", "helm", "terraform", "ansible", "jenkins", "github actions", "ci/cd", "pipeline", "nginx", "load balancer", "scaling", "monitoring", "grafana", "prometheus", "vpc", "ec2", "s3", "lambda", "serverless", "microservice"],
    "AI / ML": ["machine learning", "neural", "training", "gpt", "llm", "prompt engineering", "embedding", "vector", "langchain", "openai", "anthropic", "claude", "chatgpt", "fine-tune", "rag", "transformer", "deep learning", "nlp", "computer vision"],
    "E-commerce": ["ecommerce", "e-commerce", "shop", "store", "product catalog", "inventory", "order", "cart", "checkout", "payment", "stripe", "shopify", "woocommerce", "fulfillment", "shipping"],
    "Legal": ["legal", "gdpr", "privacy policy", "terms", "contract", "compliance", "regulation", "license", "copyright", "nda"],
    "Data & Analytics": ["analytics", "dashboard", "metric", "report", "chart", "visualization", "csv", "excel", "pandas", "dataframe", "etl", "warehouse", "bigquery", "tableau", "power bi", "statistics", "aggregate"],
    "Personal": ["health", "fitness", "diet", "recipe", "travel", "book", "movie", "music", "hobby", "relationship", "advice", "recommend"],
    "Finance": ["crypto", "bitcoin", "ethereum", "blockchain", "defi", "nft", "token", "wallet", "trading", "investment", "stock", "fintech"],
    "Business": ["business", "strategy", "market", "revenue", "growth", "startup", "saas", "pricing", "monetiz", "competitor", "pitch", "investor", "funding", "roadmap", "okr", "kpi", "stakeholder", "roi", "mvp"],
    "Marketing": ["marketing", "seo", "sem", "campaign", "conversion", "funnel", "brand", "social media", "google ads", "facebook ads", "engagement", "audience", "targeting"],
    "Career": ["resume", "cv", "job", "interview", "career", "salary", "negotiate", "linkedin", "portfolio", "promotion", "certification", "hiring", "cover letter"],
}

prog_lang_kw = {
    "PHP": ["<?php", "php", "symfony", "laravel", "eloquent", "artisan", "composer", "namespace "],
    "TypeScript/JS": ["typescript", "javascript", ".tsx", ".jsx", "const ", "=> {", "async ", "import {", "export ", "interface ", "react", "next.js", "nextjs", "node", "express", "nestjs"],
    "Python": ["python", "def ", "import ", "pip", "django", "flask", "pandas", "numpy", ".py", "self."],
    "SQL": ["select ", "insert ", "update ", "delete from", "create table", "alter table", "join ", "where ", "group by"],
    "HTML": ["html", "<div", "<form", "<input", "<button", "dom"],
    "CSS/Tailwind": ["css", "scss", "sass", "tailwind", "styled-component", "flex", "grid"],
    "Shell": ["bash", "#!/", "chmod", "curl ", "wget "],
    "YAML/Config": ["yaml", "yml", "dockerfile", "docker-compose", ".env"],
    "Java/Kotlin": ["java", "kotlin", "spring", "maven", "gradle", "public class"],
    "Rust": ["rust", "cargo", "fn main", "impl ", "trait "],
    "Go": ["golang", "func ", "goroutine", "package main"],
}

imperative_verbs = {"create", "make", "build", "write", "generate", "fix", "add", "remove", "update", "change", "implement", "show", "list", "convert", "explain", "help", "give", "tell", "find", "search", "refactor", "optimize", "design", "set", "configure", "deploy", "check", "run", "use", "get", "put", "delete", "send", "move", "copy", "merge", "split", "format", "parse", "validate", "transform", "translate", "summarize", "analyze", "compare", "provide", "suggest", "improve", "replace", "modify"}

code_patterns = [r"```", r"function\s", r"class\s", r"const\s", r"import\s", r"<\?php", r"def\s", r"async\s", r"export\s"]

# ─── Extract all data ─────────────────────────────────────────────
user_prompts = []
conversation_records = []

for conv in all_conversations:
    title = conv.get("title") or "Untitled"
    create_time = conv.get("create_time")
    model = conv.get("default_model_slug") or "unknown"
    gizmo_id = conv.get("gizmo_id")
    voice = conv.get("voice")

    user_msg_count = 0
    assistant_msg_count = 0
    conv_texts = []

    mapping = conv.get("mapping", {})
    for node in mapping.values():
        msg = node.get("message")
        if not msg or not msg.get("author"):
            continue
        role = msg["author"].get("role")
        if role == "user":
            user_msg_count += 1
            parts = msg.get("content", {}).get("parts", [])
            text = "\n".join(p for p in parts if isinstance(p, str)).strip()
            if text:
                ts = msg.get("create_time")
                timestamp = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else (
                    datetime.fromtimestamp(create_time, tz=timezone.utc) if create_time else None
                )
                has_attachments = any(not isinstance(p, str) for p in parts)
                has_code = any(re.search(pat, text) for pat in code_patterns)

                # Classify topics
                lower = text.lower()
                topics_matched = [t for t, kws in topic_keywords.items() if any(kw in lower for kw in kws)]

                # Sophistication
                words = len(text.split())
                sentences = len(re.split(r"[.!?]+", text))
                has_constraints = bool(re.search(r"\b(must|should not|don't|avoid|ensure|require|constraint)\b", text, re.I))
                has_structure = bool(re.search(r"\d+[.)]\s|[-*]\s", text))
                if words > 100 or has_code or (has_constraints and sentences > 3) or has_structure:
                    sophistication = "advanced"
                elif words > 30 or sentences > 2:
                    sophistication = "intermediate"
                else:
                    sophistication = "basic"

                # Sentence type
                first_word = re.split(r"\s+", text)[0].lower().rstrip(".,!?:;")
                if "?" in text:
                    sentence_type = "interrogative"
                elif first_word in imperative_verbs:
                    sentence_type = "imperative"
                else:
                    sentence_type = "declarative"

                user_prompts.append({
                    "text": text,
                    "timestamp": timestamp,
                    "title": title,
                    "model": model,
                    "gizmo_id": gizmo_id,
                    "has_attachments": has_attachments,
                    "has_code": has_code,
                    "topics": topics_matched,
                    "sophistication": sophistication,
                    "sentence_type": sentence_type,
                    "word_count": words,
                })
                conv_texts.append(text)
        elif role == "assistant":
            assistant_msg_count += 1

    conversation_records.append({
        "title": title,
        "create_time": datetime.fromtimestamp(create_time, tz=timezone.utc) if create_time else None,
        "model": model,
        "gizmo_id": gizmo_id,
        "voice": voice,
        "user_msg_count": user_msg_count,
        "assistant_msg_count": assistant_msg_count,
        "total_turns": user_msg_count + assistant_msg_count,
    })

print(f"Extracted {len(user_prompts)} user prompts")

# ─── Compute all dashboard dimensions ─────────────────────────────

# 1. Overview metrics
total_convs = len(all_conversations)
total_prompts = len(user_prompts)
timestamps = sorted([p["timestamp"] for p in user_prompts if p["timestamp"]])
months_active = len(set(t.strftime("%Y-%m") for t in timestamps))
voice_convs = sum(1 for c in conversation_records if c["voice"])
attachment_prompts = sum(1 for p in user_prompts if p["has_attachments"])

# 2. Topic distribution
topic_counts = Counter()
for p in user_prompts:
    for t in p["topics"]:
        topic_counts[t] += 1

# 3. Topic × Month matrix
topic_month = defaultdict(lambda: defaultdict(int))
for p in user_prompts:
    if p["timestamp"]:
        month_key = p["timestamp"].strftime("%Y-%m")
        for t in p["topics"]:
            topic_month[t][month_key] += 1

all_months = sorted(set(t.strftime("%Y-%m") for t in timestamps))
topic_month_matrix = {}
for topic in topic_counts:
    topic_month_matrix[topic] = [topic_month[topic].get(m, 0) for m in all_months]

# 4. Hour × Day-of-Week heatmap
hour_day_matrix = [[0]*7 for _ in range(24)]
for p in user_prompts:
    if p["timestamp"]:
        hour_day_matrix[p["timestamp"].hour][p["timestamp"].weekday()] += 1

# 5. Hourly and daily distributions
hour_counts = Counter()
day_counts = Counter()
month_counts = Counter()
for p in user_prompts:
    if p["timestamp"]:
        hour_counts[p["timestamp"].hour] += 1
        day_counts[p["timestamp"].weekday()] += 1
        month_counts[p["timestamp"].strftime("%Y-%m")] += 1

# 6. Prompt length distribution (buckets)
length_buckets = {"1-5": 0, "6-10": 0, "11-25": 0, "26-50": 0, "51-100": 0, "101-200": 0, "201-500": 0, "500+": 0}
for p in user_prompts:
    w = p["word_count"]
    if w <= 5: length_buckets["1-5"] += 1
    elif w <= 10: length_buckets["6-10"] += 1
    elif w <= 25: length_buckets["11-25"] += 1
    elif w <= 50: length_buckets["26-50"] += 1
    elif w <= 100: length_buckets["51-100"] += 1
    elif w <= 200: length_buckets["101-200"] += 1
    elif w <= 500: length_buckets["201-500"] += 1
    else: length_buckets["500+"] += 1

# 7. Conversation depth distribution
depth_buckets = {"1": 0, "2-5": 0, "6-10": 0, "11-20": 0, "21-50": 0, "51-100": 0, "100+": 0}
depth_by_topic = defaultdict(list)
longest_convs = []

for c in conversation_records:
    t = c["total_turns"]
    if t <= 1: depth_buckets["1"] += 1
    elif t <= 5: depth_buckets["2-5"] += 1
    elif t <= 10: depth_buckets["6-10"] += 1
    elif t <= 20: depth_buckets["11-20"] += 1
    elif t <= 50: depth_buckets["21-50"] += 1
    elif t <= 100: depth_buckets["51-100"] += 1
    else: depth_buckets["100+"] += 1
    longest_convs.append({"title": c["title"], "turns": t, "model": c["model"]})

longest_convs.sort(key=lambda x: x["turns"], reverse=True)

# 8. Model usage
model_counts = Counter(c["model"] for c in conversation_records)

# 9. Model × Month
model_month = defaultdict(lambda: defaultdict(int))
for c in conversation_records:
    if c["create_time"]:
        mk = c["create_time"].strftime("%Y-%m")
        model_month[c["model"]][mk] += 1

top_models = [m for m, _ in model_counts.most_common(6)]
model_month_matrix = {}
for model in top_models:
    model_month_matrix[model] = [model_month[model].get(m, 0) for m in all_months]

# 10. Programming languages
prog_counts = Counter()
for p in user_prompts:
    lower = p["text"].lower()
    for lang, kws in prog_lang_kw.items():
        if any(kw in lower for kw in kws):
            prog_counts[lang] += 1

# 11. Natural languages
lang_patterns = {
    "English": re.compile(r"\b(the|is|are|was|were|have|has|this|that|with|for|and|but|not|can|will|how|what|why|when|please|should|could|would)\b", re.I),
    "Romanian": re.compile(r"[ăîșțâ]|\b(pentru|din|care|sunt|este|sau|dar|foarte|poate|trebuie|acum|aici|cum|unde)\b", re.I),
    "Dutch": re.compile(r"\b(het|een|van|dat|dit|zijn|niet|maar|voor|met|ook|nog|wel|kan|moet|deze|wordt|naar)\b", re.I),
    "Turkish": re.compile(r"\b(bir|bu|için|ile|olan|gibi|var|ben|sen|nasıl|neden|ama|çok)\b", re.I),
    "French": re.compile(r"\b(le|la|les|un|une|des|est|sont|avec|pour|dans|sur|pas|plus|mais)\b", re.I),
}
nat_lang_counts = Counter()
for p in user_prompts:
    for lang, pat in lang_patterns.items():
        if len(pat.findall(p["text"])) >= 3:
            nat_lang_counts[lang] += 1

# 12. Sophistication distribution
soph_counts = Counter(p["sophistication"] for p in user_prompts)

# 13. Sophistication × Topic
soph_topic = defaultdict(lambda: {"basic": 0, "intermediate": 0, "advanced": 0})
for p in user_prompts:
    for t in p["topics"]:
        soph_topic[t][p["sophistication"]] += 1

# 14. Communication style
style_counts = Counter(p["sentence_type"] for p in user_prompts)
polite = sum(1 for p in user_prompts if re.search(r"\b(please|thank|thanks|could you|would you)\b", p["text"], re.I))
informal = sum(1 for p in user_prompts if re.search(r"\b(gonna|wanna|yeah|yep|nope|lol|haha|btw|fyi|tbh)\b", p["text"], re.I))
with_context = sum(1 for p in user_prompts if len(p["text"]) > 200 or re.search(r"\b(context|background|currently|working on|trying to|goal is)\b", p["text"], re.I))
with_code = sum(1 for p in user_prompts if p["has_code"])
short = sum(1 for p in user_prompts if p["word_count"] < 10)

# 15. Custom GPTs
gizmo_counts = Counter(c["gizmo_id"] for c in conversation_records if c["gizmo_id"])

# 16. Voice usage
voice_type_counts = Counter(c["voice"] for c in conversation_records if c["voice"])

# 17. Title keywords
stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "is", "it", "that", "this", "was", "are", "be", "has", "had", "have", "not", "can", "will", "do", "if", "my", "me", "you", "your", "its", "all", "our", "we", "they"}
title_words = Counter()
for c in conversation_records:
    t = (c["title"] or "").lower()
    if t in {"new chat", "untitled", ""}:
        continue
    words = re.sub(r"[^\w\s]", "", t).split()
    for w in words:
        if len(w) > 2 and w not in stop_words:
            title_words[w] += 1

# 18. N-grams
bigram_counts = Counter()
trigram_counts = Counter()
for p in user_prompts:
    words = re.sub(r"[^\w\s]", "", p["text"].lower()).split()
    words = [w for w in words if len(w) > 2 and w not in stop_words]
    for i in range(len(words) - 1):
        bigram_counts[f"{words[i]} {words[i+1]}"] += 1
    for i in range(len(words) - 2):
        trigram_counts[f"{words[i]} {words[i+1]} {words[i+2]}"] += 1

# 19. Code vs non-code by topic
code_by_topic = defaultdict(lambda: {"with_code": 0, "without_code": 0})
for p in user_prompts:
    for t in p["topics"]:
        if p["has_code"]:
            code_by_topic[t]["with_code"] += 1
        else:
            code_by_topic[t]["without_code"] += 1

# 20. Monthly active days
monthly_active_days = defaultdict(set)
for p in user_prompts:
    if p["timestamp"]:
        mk = p["timestamp"].strftime("%Y-%m")
        monthly_active_days[mk].add(p["timestamp"].day)

# ─── Build output ─────────────────────────────────────────────────
day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

output = {
    "overview": {
        "total_conversations": total_convs,
        "total_prompts": total_prompts,
        "date_range_from": timestamps[0].strftime("%Y-%m-%d"),
        "date_range_to": timestamps[-1].strftime("%Y-%m-%d"),
        "months_active": months_active,
        "avg_per_month": round(total_prompts / months_active, 1),
        "voice_conversations": voice_convs,
        "attachment_prompts": attachment_prompts,
    },
    "months": all_months,
    "topic_distribution": {t: c for t, c in topic_counts.most_common()},
    "topic_month_matrix": topic_month_matrix,
    "hour_day_heatmap": hour_day_matrix,
    "hourly": [hour_counts.get(h, 0) for h in range(24)],
    "daily": {day_names[d]: day_counts.get(d, 0) for d in range(7)},
    "monthly_activity": {m: month_counts.get(m, 0) for m in all_months},
    "monthly_active_days": {m: len(monthly_active_days.get(m, set())) for m in all_months},
    "prompt_length_buckets": length_buckets,
    "conversation_depth_buckets": depth_buckets,
    "longest_conversations": longest_convs[:25],
    "model_usage": {m: c for m, c in model_counts.most_common()},
    "model_month_matrix": model_month_matrix,
    "programming_languages": {l: c for l, c in prog_counts.most_common() if c > 0},
    "natural_languages": {l: c for l, c in nat_lang_counts.most_common()},
    "sophistication": dict(soph_counts),
    "sophistication_by_topic": {t: dict(v) for t, v in soph_topic.items()},
    "communication_style": {
        "sentence_types": dict(style_counts),
        "polite_pct": round(polite / total_prompts * 100, 1),
        "informal_pct": round(informal / total_prompts * 100, 1),
        "context_pct": round(with_context / total_prompts * 100, 1),
        "code_pct": round(with_code / total_prompts * 100, 1),
        "short_pct": round(short / total_prompts * 100, 1),
    },
    "code_by_topic": {t: dict(v) for t, v in code_by_topic.items()},
    "custom_gpts": {g: c for g, c in gizmo_counts.most_common(10)},
    "voice_types": dict(voice_type_counts),
    "title_keywords": {w: c for w, c in title_words.most_common(40)},
    "top_bigrams": {bg: c for bg, c in bigram_counts.most_common(25)},
    "top_trigrams": {tg: c for tg, c in trigram_counts.most_common(15)},
}

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, default=str)

print("dashboard_data.json generated successfully")
print(f"  Months: {len(all_months)}")
print(f"  Topics: {len(topic_counts)}")
print(f"  Models: {len(model_counts)}")
