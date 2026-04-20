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
OUTPUT = os.environ.get("ANALYSIS_RESULTS", "analysis_results.json")

# ─── Load all conversations ──────────────────────────────────────
all_conversations = []
i = 0
while True:
    fname = f"conversations-{i:03d}.json"
    fpath = os.path.join(BASE, fname)
    if not os.path.exists(fpath):
        break
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
            all_conversations.extend(data)
        print(f"  Loaded {fname}: {len(data)} conversations")
    except Exception as e:
        print(f"  Error loading {fname}: {e}")
    i += 1

print(f"\nTotal conversations loaded: {len(all_conversations)}")

# ─── Extract user messages & metadata ─────────────────────────────
user_prompts = []
conversation_meta = []

for conv in all_conversations:
    title = conv.get("title") or "Untitled"
    create_time = conv.get("create_time")
    update_time = conv.get("update_time")
    model = conv.get("default_model_slug") or "unknown"
    gizmo_id = conv.get("gizmo_id")
    is_archived = conv.get("is_archived", False)
    is_starred = conv.get("is_starred", False)
    voice = conv.get("voice")

    user_msg_count = 0
    assistant_msg_count = 0
    conv_user_texts = []

    mapping = conv.get("mapping", {})
    for node_id, node in mapping.items():
        msg = node.get("message")
        if not msg or not msg.get("author"):
            continue
        role = msg["author"].get("role")
        if role == "user":
            user_msg_count += 1
            content = msg.get("content", {})
            parts = content.get("parts", [])
            text = "\n".join(p for p in parts if isinstance(p, str)).strip()
            if text:
                ts = msg.get("create_time")
                timestamp = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else (
                    datetime.fromtimestamp(create_time, tz=timezone.utc) if create_time else None
                )
                has_attachments = any(not isinstance(p, str) for p in parts)
                user_prompts.append({
                    "text": text,
                    "timestamp": timestamp,
                    "title": title,
                    "model": model,
                    "gizmo_id": gizmo_id,
                    "content_type": content.get("content_type", "text"),
                    "has_attachments": has_attachments,
                })
                conv_user_texts.append(text)
        elif role == "assistant":
            assistant_msg_count += 1

    conversation_meta.append({
        "title": title,
        "create_time": datetime.fromtimestamp(create_time, tz=timezone.utc) if create_time else None,
        "update_time": datetime.fromtimestamp(update_time, tz=timezone.utc) if update_time else None,
        "model": model,
        "gizmo_id": gizmo_id,
        "is_archived": is_archived,
        "is_starred": is_starred,
        "voice": voice,
        "user_msg_count": user_msg_count,
        "assistant_msg_count": assistant_msg_count,
        "total_turns": user_msg_count + assistant_msg_count,
        "first_prompt": conv_user_texts[0][:200] if conv_user_texts else "",
    })

print(f"Total user prompts extracted: {len(user_prompts)}")
timestamps = [p["timestamp"] for p in user_prompts if p["timestamp"]]
if timestamps:
    timestamps.sort()
    print(f"Date range: {timestamps[0].strftime('%Y-%m-%d')} to {timestamps[-1].strftime('%Y-%m-%d')}")

# ─── 1. TOPIC & USE CASE CLASSIFICATION ──────────────────────────
topic_keywords = {
    "Software Development / Coding": ["code", "function", "class", "api", "bug", "error", "debug", "implement", "refactor", "typescript", "javascript", "python", "php", "react", "node", "sql", "database", "git", "deploy", "docker", "test", "unit test", "symfony", "laravel", "nextjs", "next.js", "nestjs", "express", "mongodb", "postgres", "mysql", "redis", "aws", "azure", "gcp", "terraform", "webpack", "vite", "eslint", "npm", "yarn", "component", "hook", "state", "props", "interface", "migration", "schema", "endpoint", "route", "middleware", "controller", "service", "repository", "entity", "dto", "graphql", "rest", "crud", "authentication", "authorization", "jwt", "oauth", "css", "html", "tailwind", "scss"],
    "DevOps / Infrastructure": ["kubernetes", "k8s", "docker", "container", "helm", "terraform", "ansible", "jenkins", "github actions", "ci/cd", "pipeline", "nginx", "load balancer", "scaling", "monitoring", "grafana", "prometheus", "vpc", "ec2", "s3", "lambda", "serverless", "microservice"],
    "Data & Analytics": ["analytics", "dashboard", "metric", "report", "chart", "visualization", "csv", "excel", "pandas", "dataframe", "etl", "warehouse", "bigquery", "tableau", "power bi", "statistics", "aggregate"],
    "AI / Machine Learning": ["machine learning", "neural", "training", "gpt", "llm", "prompt engineering", "embedding", "vector", "langchain", "openai", "anthropic", "claude", "chatgpt", "fine-tune", "rag", "transformer", "deep learning", "nlp", "computer vision", "dall-e", "midjourney", "stable diffusion"],
    "Business / Strategy": ["business", "strategy", "market", "revenue", "growth", "startup", "saas", "pricing", "monetiz", "competitor", "pitch", "investor", "funding", "roadmap", "okr", "kpi", "stakeholder", "roi", "mvp", "product market fit", "go-to-market"],
    "Writing / Content Creation": ["write", "blog", "article", "content", "copy", "newsletter", "story", "essay", "draft", "proofread", "tone", "headline", "caption", "script", "presentation", "document"],
    "Career / Professional": ["resume", "cv", "job", "interview", "career", "salary", "negotiate", "linkedin", "portfolio", "promotion", "certification", "hiring", "cover letter"],
    "Product / UX Design": ["design", "ux", "ui", "user experience", "wireframe", "mockup", "prototype", "figma", "user flow", "persona", "usability", "accessibility", "responsive"],
    "Marketing / SEO": ["marketing", "seo", "sem", "campaign", "conversion", "funnel", "brand", "social media", "google ads", "facebook ads", "engagement", "audience", "targeting"],
    "E-commerce": ["ecommerce", "e-commerce", "shop", "store", "product catalog", "inventory", "order", "cart", "checkout", "payment", "stripe", "shopify", "woocommerce", "fulfillment", "shipping"],
    "Personal / Life": ["health", "fitness", "diet", "recipe", "travel", "book", "movie", "music", "hobby", "relationship", "advice", "recommend"],
    "Education / Learning": ["learn", "explain", "tutorial", "course", "concept", "understand", "how does", "what is", "difference between", "example of", "teach me"],
    "Legal / Compliance": ["legal", "gdpr", "privacy policy", "terms", "contract", "compliance", "regulation", "license", "copyright", "nda"],
    "Finance / Crypto": ["crypto", "bitcoin", "ethereum", "blockchain", "defi", "nft", "token", "wallet", "trading", "investment", "stock", "fintech"],
    "Automation / Scripting": ["automate", "automation", "script", "cron", "webhook", "zapier", "make.com", "n8n", "workflow", "bot", "scrape", "crawl"],
}

topic_counts = Counter()
topic_examples = defaultdict(list)

for p in user_prompts:
    lower = p["text"].lower()
    for topic, keywords in topic_keywords.items():
        if any(kw in lower for kw in keywords):
            topic_counts[topic] += 1
            if len(topic_examples[topic]) < 5:
                topic_examples[topic].append(p["title"])

# ─── 2. LINGUISTIC ANALYSIS ──────────────────────────────────────
lengths = [len(p["text"]) for p in user_prompts]
word_counts = [len(p["text"].split()) for p in user_prompts]
avg_len = sum(lengths) / len(lengths)
avg_words = sum(word_counts) / len(word_counts)
sorted_wc = sorted(word_counts)
median_words = sorted_wc[len(sorted_wc) // 2]
max_words = max(word_counts)
p95_words = sorted_wc[int(len(sorted_wc) * 0.95)]

sentence_counts = [len(re.split(r"[.!?]+", p["text"])) for p in user_prompts]
avg_sentences = sum(sentence_counts) / len(sentence_counts)

# Question rate
question_count = sum(1 for p in user_prompts if "?" in p["text"])
question_rate = question_count / len(user_prompts)

# Imperative / Interrogative / Declarative
imperative_verbs = {"create", "make", "build", "write", "generate", "fix", "add", "remove", "update", "change", "implement", "show", "list", "convert", "explain", "help", "give", "tell", "find", "search", "refactor", "optimize", "design", "set", "configure", "deploy", "check", "run", "use", "get", "put", "delete", "send", "move", "copy", "merge", "split", "format", "parse", "validate", "transform", "translate", "summarize", "analyze", "compare", "provide", "suggest", "improve", "replace", "modify"}

imperative = 0
interrogative = 0
declarative = 0

for p in user_prompts:
    text = p["text"].strip()
    first_word = re.split(r"\s+", text)[0].lower().rstrip(".,!?:;")
    if "?" in text:
        interrogative += 1
    elif first_word in imperative_verbs:
        imperative += 1
    else:
        declarative += 1

# Code inclusion
code_patterns = [r"```", r"function\s", r"class\s", r"const\s", r"import\s", r"<\?php", r"def\s", r"async\s", r"export\s"]
code_count = sum(1 for p in user_prompts if any(re.search(pat, p["text"]) for pat in code_patterns))
code_rate = code_count / len(user_prompts)

# ─── 3. LANGUAGE DETECTION ───────────────────────────────────────
lang_patterns = {
    "English": re.compile(r"\b(the|is|are|was|were|have|has|this|that|with|for|and|but|not|can|will|how|what|why|when|please|should|could|would)\b", re.I),
    "Dutch": re.compile(r"\b(het|een|van|dat|dit|zijn|niet|maar|voor|met|ook|nog|wel|kan|moet|hebben|deze|wordt|naar|zijn|hoe|wat|waarom|wanneer|graag|alsjeblieft)\b", re.I),
    "Turkish": re.compile(r"\b(bir|bu|için|ile|olan|gibi|var|ben|sen|biz|nasıl|neden|ama|çok|olarak|değil|mı|mi|mu|mü)\b", re.I),
    "German": re.compile(r"\b(der|die|das|ein|eine|ist|und|für|mit|auf|auch|nicht|sich|haben|werden|können|bitte)\b", re.I),
    "French": re.compile(r"\b(le|la|les|un|une|des|est|sont|avec|pour|dans|sur|pas|plus|mais|aussi|très|fait|comment|pourquoi)\b", re.I),
}

lang_counts = Counter()
lang_examples = defaultdict(list)
for p in user_prompts:
    for lang, pat in lang_patterns.items():
        matches = pat.findall(p["text"])
        if len(matches) >= 3:  # at least 3 indicator words
            lang_counts[lang] += 1
            if len(lang_examples[lang]) < 3:
                lang_examples[lang].append(p["text"][:80])

# ─── 4. COMMUNICATION STYLE ──────────────────────────────────────
polite_count = sum(1 for p in user_prompts if re.search(r"\b(please|thank|thanks|could you|would you|kindly|appreciate|sorry)\b", p["text"], re.I))
informal_count = sum(1 for p in user_prompts if re.search(r"\b(gonna|wanna|gotta|yeah|yep|nope|lol|haha|btw|fyi|tbh|imo|ok so|hey|hi|sup|yo)\b", p["text"], re.I))
contextual_count = sum(1 for p in user_prompts if len(p["text"]) > 200 or re.search(r"\b(context|background|currently|situation|working on|trying to|goal is|need to|purpose|project)\b", p["text"], re.I))
short_count = sum(1 for p in user_prompts if len(p["text"].split()) < 10)

# Tech jargon density
tech_terms = ["api", "endpoint", "middleware", "microservice", "containeriz", "orchestrat", "deployment", "ci/cd", "pipeline", "kubernetes", "terraform", "webhook", "payload", "schema", "migration", "serializ", "singleton", "factory pattern", "observer", "repository pattern", "dependency injection", "async", "promise", "callback", "closure", "recursion", "polymorphism", "inheritance", "encapsulation", "abstraction", "mutex", "semaphore", "deadlock", "race condition"]
tech_total = sum(sum(1 for t in tech_terms if t in p["text"].lower()) for p in user_prompts)

# ─── 5. PROMPT SOPHISTICATION ────────────────────────────────────
basic = intermediate = advanced = 0
for p in user_prompts:
    words = len(p["text"].split())
    sentences = len(re.split(r"[.!?]+", p["text"]))
    has_code = bool(re.search(r"```|function\s|class\s|const\s|import\s|def\s", p["text"]))
    has_constraints = bool(re.search(r"\b(must|should not|don't|avoid|ensure|require|constraint|specific|exact|always|never)\b", p["text"], re.I))
    has_structure = bool(re.search(r"\d+[.)]\s|[-*]\s", p["text"]))
    has_multipart = bool(re.search(r"\b(first|second|third|then|also|additionally|moreover|finally)\b", p["text"], re.I))

    if words > 100 or has_code or (has_constraints and sentences > 3) or has_structure or (has_multipart and words > 50):
        advanced += 1
    elif words > 30 or sentences > 2:
        intermediate += 1
    else:
        basic += 1

# ─── 6. TEMPORAL ANALYSIS ────────────────────────────────────────
hour_counts = Counter()
day_counts = Counter()
month_counts = Counter()
day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

for p in user_prompts:
    ts = p["timestamp"]
    if ts:
        hour_counts[ts.hour] += 1
        day_counts[ts.weekday()] += 1
        month_counts[ts.strftime("%Y-%m")] += 1

peak_hour = hour_counts.most_common(1)[0][0] if hour_counts else 0
late_night = sum(hour_counts[h] for h in range(22, 24)) + sum(hour_counts[h] for h in range(0, 5))
work_hours = sum(hour_counts[h] for h in range(9, 18))
total_timed = len(timestamps)

# ─── 7. MODEL USAGE ──────────────────────────────────────────────
model_counts = Counter(c["model"] for c in conversation_meta)

# ─── 8. CONVERSATION DEPTH ───────────────────────────────────────
turns = [c["total_turns"] for c in conversation_meta]
avg_turns = sum(turns) / len(turns) if turns else 0
deep_convs = sum(1 for t in turns if t > 20)
single_turn = sum(1 for c in conversation_meta if c["user_msg_count"] <= 1)

# ─── 9. CUSTOM GPTs ──────────────────────────────────────────────
gizmo_convs = [c for c in conversation_meta if c["gizmo_id"]]
gizmo_counts = Counter(c["gizmo_id"] for c in gizmo_convs)

# ─── 10. VOICE CONVERSATIONS ─────────────────────────────────────
voice_convs = [c for c in conversation_meta if c.get("voice")]
voice_counts = Counter(c["voice"] for c in voice_convs)

# ─── 11. N-GRAM ANALYSIS ─────────────────────────────────────────
stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "is", "it", "that", "this", "was", "are", "be", "has", "had", "have", "not", "can", "will", "do", "if", "my", "me", "you", "your", "its", "all", "our", "we", "they", "them"}

bigram_counts = Counter()
trigram_counts = Counter()

for p in user_prompts:
    words = re.sub(r"[^\w\s]", "", p["text"].lower()).split()
    words = [w for w in words if len(w) > 2 and w not in stop_words]
    for i in range(len(words) - 1):
        bigram_counts[f"{words[i]} {words[i+1]}"] += 1
    for i in range(len(words) - 2):
        trigram_counts[f"{words[i]} {words[i+1]} {words[i+2]}"] += 1

# ─── 12. PROGRAMMING LANGUAGES ───────────────────────────────────
prog_lang_kw = {
    "TypeScript/JavaScript": ["typescript", "javascript", ".tsx", ".jsx", "const ", "=> {", "async ", "import {", "export ", "interface ", "react", "next.js", "nextjs", "node", "express", "nestjs", "vue", "angular", "svelte"],
    "PHP": ["<?php", "php", "symfony", "laravel", "eloquent", "artisan", "composer", "namespace "],
    "Python": ["python", "def ", "import ", "pip", "django", "flask", "pandas", "numpy", ".py", "self."],
    "SQL": ["select ", "insert ", "update ", "delete from", "create table", "alter table", "join ", "where ", "group by"],
    "Shell/Bash": ["bash", "#!/", "chmod", "curl ", "wget ", "apt ", "brew "],
    "CSS/SCSS/Tailwind": ["css", "scss", "sass", "tailwind", "styled-component", "flex", "grid", "media query"],
    "HTML": ["html", "<div", "<form", "<input", "<button", "dom"],
    "Go": ["golang", "func ", "goroutine", "package main", "go mod"],
    "Rust": ["rust", "cargo", "fn main", "impl ", "trait "],
    "Java/Kotlin": ["java", "kotlin", "spring", "maven", "gradle", "public class"],
    "YAML/Config": ["yaml", "yml", "dockerfile", "docker-compose", ".env"],
}

prog_counts = Counter()
for p in user_prompts:
    lower = p["text"].lower()
    for lang, kws in prog_lang_kw.items():
        if any(kw in lower for kw in kws):
            prog_counts[lang] += 1

# ─── 13. CONVERSATION TITLE ANALYSIS ─────────────────────────────
title_words = Counter()
skip_titles = {"new chat", "untitled", "chatgpt", ""}
for c in conversation_meta:
    t = (c["title"] or "").lower()
    if t in skip_titles:
        continue
    words = re.sub(r"[^\w\s]", "", t).split()
    for w in words:
        if len(w) > 2 and w not in stop_words:
            title_words[w] += 1

# ─── 14. ATTACHMENT/MULTIMODAL USAGE ─────────────────────────────
attachment_count = sum(1 for p in user_prompts if p["has_attachments"])

# ─── 15. STARRED CONVERSATION TOPICS ─────────────────────────────
starred = [c for c in conversation_meta if c["is_starred"]]

# ─── BUILD OUTPUT ─────────────────────────────────────────────────
total = len(user_prompts)

output = {
    "OVERVIEW": {
        "total_conversations": len(all_conversations),
        "total_user_prompts": total,
        "date_range": f"{timestamps[0].strftime('%Y-%m-%d')} to {timestamps[-1].strftime('%Y-%m-%d')}" if timestamps else "N/A",
        "months_active": len(month_counts),
        "avg_prompts_per_conversation": round(total / len(all_conversations), 1),
        "starred_conversations": len(starred),
        "archived_conversations": sum(1 for c in conversation_meta if c["is_archived"]),
        "conversations_with_attachments": attachment_count,
        "voice_conversations": len(voice_convs),
    },
    "TOPIC_DISTRIBUTION": [
        {"topic": t, "count": c, "pct": f"{c/total*100:.1f}%"}
        for t, c in topic_counts.most_common()
    ],
    "PROGRAMMING_LANGUAGES": [
        {"language": l, "mentions": c, "pct": f"{c/total*100:.1f}%"}
        for l, c in prog_counts.most_common() if c > 0
    ],
    "PROMPT_COMPLEXITY": {
        "avg_chars": round(avg_len),
        "avg_words": round(avg_words),
        "median_words": median_words,
        "p95_words": p95_words,
        "max_words": max_words,
        "avg_sentences": round(avg_sentences, 1),
        "sophistication": {
            "basic_short": f"{basic} ({basic/total*100:.1f}%)",
            "intermediate": f"{intermediate} ({intermediate/total*100:.1f}%)",
            "advanced_detailed": f"{advanced} ({advanced/total*100:.1f}%)",
        },
    },
    "COMMUNICATION_STYLE": {
        "sentence_types": {
            "imperative_commands": f"{imperative} ({imperative/total*100:.1f}%)",
            "interrogative_questions": f"{interrogative} ({interrogative/total*100:.1f}%)",
            "declarative_statements": f"{declarative} ({declarative/total*100:.1f}%)",
        },
        "politeness_rate": f"{polite_count/total*100:.1f}%",
        "informal_language_rate": f"{informal_count/total*100:.1f}%",
        "context_providing_rate": f"{contextual_count/total*100:.1f}%",
        "code_inclusion_rate": f"{code_rate*100:.1f}%",
        "short_prompt_rate": f"{short_count/total*100:.1f}% (<10 words)",
        "tech_jargon_density": f"{tech_total/total:.2f} terms/prompt",
    },
    "NATURAL_LANGUAGE": {
        "languages_detected": [
            {"language": l, "prompts": c, "pct": f"{c/total*100:.1f}%"}
            for l, c in lang_counts.most_common()
        ],
    },
    "TEMPORAL_PATTERNS": {
        "peak_hour": f"{peak_hour:02d}:00",
        "hourly_distribution": {f"{h:02d}:00": hour_counts[h] for h in range(24)},
        "day_of_week": {day_names[d]: day_counts[d] for d in range(7)},
        "late_night_pct": f"{late_night/total_timed*100:.1f}% (22:00-05:00)" if total_timed else "N/A",
        "work_hours_pct": f"{work_hours/total_timed*100:.1f}% (09:00-18:00)" if total_timed else "N/A",
        "monthly_activity": {m: c for m, c in sorted(month_counts.items())},
    },
    "MODEL_USAGE": [
        {"model": m, "conversations": c}
        for m, c in model_counts.most_common()
    ],
    "CONVERSATION_DEPTH": {
        "avg_turns": round(avg_turns, 1),
        "deep_conversations_gt20": deep_convs,
        "single_turn_conversations": single_turn,
        "max_turns": max(turns) if turns else 0,
    },
    "CUSTOM_GPTS": {
        "total_conversations_with_gpts": len(gizmo_convs),
        "unique_gpts_used": len(gizmo_counts),
        "top_gpts": [{"id": g, "uses": c} for g, c in gizmo_counts.most_common(10)],
    },
    "VOICE_USAGE": {
        "total_voice_conversations": len(voice_convs),
        "voices_used": dict(voice_counts.most_common()),
    },
    "TOP_BIGRAMS": [{"phrase": bg, "count": c} for bg, c in bigram_counts.most_common(30)],
    "TOP_TRIGRAMS": [{"phrase": tg, "count": c} for tg, c in trigram_counts.most_common(20)],
    "TOP_TITLE_KEYWORDS": [{"word": w, "count": c} for w, c in title_words.most_common(50)],
    "STARRED_CONVERSATIONS": [{"title": c["title"], "model": c["model"]} for c in starred[:20]],
}

# Save full results
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, default=str)

print("\n" + "=" * 60)
print("   ANALYSIS COMPLETE - Results saved to analysis_results.json")
print("=" * 60)

# Print key highlights
print(f"\n{len(all_conversations)} conversations | {total} user prompts")
print(f"Active period: {output['OVERVIEW']['date_range']}")
print(f"Voice conversations: {len(voice_convs)}")
print(f"Prompts with attachments: {attachment_count}")
print(f"\n--- TOP TOPICS ---")
for item in output["TOPIC_DISTRIBUTION"][:8]:
    print(f"  {item['topic']}: {item['count']} ({item['pct']})")
print(f"\n--- PROGRAMMING LANGUAGES ---")
for item in output["PROGRAMMING_LANGUAGES"][:6]:
    print(f"  {item['language']}: {item['mentions']} ({item['pct']})")
print(f"\n--- PROMPT STYLE ---")
print(f"  Avg words/prompt: {round(avg_words)}")
print(f"  Imperative: {imperative/total*100:.0f}% | Questions: {interrogative/total*100:.0f}% | Declarative: {declarative/total*100:.0f}%")
print(f"  Politeness: {polite_count/total*100:.0f}% | Informal: {informal_count/total*100:.0f}%")
print(f"  Code inclusion: {code_rate*100:.0f}% | Context providing: {contextual_count/total*100:.0f}%")
print(f"\n--- TEMPORAL ---")
print(f"  Peak hour: {peak_hour:02d}:00 | Work hours: {work_hours/total_timed*100:.0f}% | Late night: {late_night/total_timed*100:.0f}%")
print(f"\n--- MODELS ---")
for m, c in model_counts.most_common(5):
    print(f"  {m}: {c}")
print(f"\n--- CONVERSATION DEPTH ---")
print(f"  Avg turns: {avg_turns:.1f} | Deep (>20): {deep_convs} | Single-turn: {single_turn} | Max: {max(turns)}")
