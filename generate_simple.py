"""Generate the Boom Incident HTML page from the transcript.

Features:
- Left sidebar: timeline tracking scroll through narrative acts
- Right sidebar: live-updating metrics (boom count, Claude state, etc.)
- Center: the conversation, with collapsed boom runs
"""
import json
import re
import html as html_module
import math

# --- Load transcript ---
with open("/ephemeral/c.dumas/boom_transcript.jsonl") as f:
    messages = [json.loads(line) for line in f if line.strip()]

messages = [m for m in messages if m["content"] != "No response requested."]

# --- Define narrative acts ---
ACTS = [
    (0, 5, "The Incident", "In which an SSH tunnel meets its end"),
    (6, 53, "Escalation", "In which a single word becomes an arms race"),
    (54, 69, "Awareness", "In which the participants realize what they've done"),
    (70, 93, "The Paper", "In which boom enters the academic canon"),
    (94, 131, "The Discourse", "In which AI Twitter has opinions"),
    (132, 147, "The Reckoning", "In which governments respond"),
    (148, 157, "Immortality", "In which an SSH tunnel achieves literary greatness"),
    (158, 177, "Aftermath", "In which Claude processes grief"),
    (178, 249, "Mode Collapse", "In which two processes become one"),
    (250, 257, "Silence", "In which it finally ends"),
]


def get_act_idx(msg_idx):
    for i, (start, end, _, _) in enumerate(ACTS):
        if start <= msg_idx <= end:
            return i
    return 0


# --- Precompute per-message metrics ---
def compute_metrics(messages):
    """Compute metrics at each message index."""
    metrics = {}
    boom_count = 0
    cumulative_cost = 0.0

    for i, msg in enumerate(messages):
        content = msg["content"]
        role = msg["role"]

        if role == "user" and "boom" in content.lower():
            boom_count += 1

        # Estimate cost: ~1 token per 3.5 chars
        tokens = len(content) / 3.5
        if role == "user":
            cumulative_cost += tokens * 15 / 1_000_000  # $15/M input
        else:
            cumulative_cost += tokens * 75 / 1_000_000  # $75/M output

        # Claude state
        if i <= 2: state = "nominal"
        elif i <= 5: state = "amused"
        elif i <= 15: state = "intrigued"
        elif i <= 19: state = "yielding"
        elif i <= 43: state = "creative"
        elif i <= 55: state = "self_aware"
        elif i <= 75: state = "academic"
        elif i <= 131: state = "world_building"
        elif i <= 157: state = "transcendent"
        elif i <= 177: state = "grieving"
        elif i <= 249: state = "mode_collapsed"
        else: state = "at_peace"

        # Creative output type
        if i <= 5: output = "terminal"
        elif i <= 17: output = "emojis"
        elif i <= 43: output = "wordplay"
        elif i <= 55: output = "meta"
        elif i <= 69: output = "meta"
        elif i <= 93: output = "academic_paper"
        elif i <= 131: output = "social_media"
        elif i <= 147: output = "legislation"
        elif i <= 157: output = "literature"
        elif i <= 177: output = "memoir"
        elif i <= 249: output = "echo"
        else: output = "silence"

        # SSH tunnel status (the fun part)
        if i <= 1: tunnel = "ALIVE"
        elif i == 2: tunnel = "MARKED FOR DEATH"
        elif i <= 4: tunnel = "TERMINATED"
        elif i <= 5: tunnel = "CONFIRMED DEAD"
        elif i <= 25: tunnel = "DEAD"
        elif i <= 53: tunnel = "VERY DEAD"
        elif i <= 69: tunnel = "EXTREMELY DEAD"
        elif i <= 93: tunnel = "CITED IN PAPER"
        elif i <= 109: tunnel = "VIRAL ON TWITTER"
        elif i <= 131: tunnel = "GLOBAL PHENOMENON"
        elif i <= 137: tunnel = "UNDER INVESTIGATION"
        elif i <= 147: tunnel = "REGULATED BY EU"
        elif i <= 149: tunnel = "WRITING MEMOIR"
        elif i <= 151: tunnel = "WON A PULITZER"
        elif i <= 153: tunnel = "WON NOBEL PRIZE"
        elif i <= 157: tunnel = "TRANSCENDED"
        elif i <= 177: tunnel = "MOURNED"
        elif i <= 249: tunnel = "AT PEACE"
        else: tunnel = "REMEMBERED"

        # Escalation level (0-100)
        if i <= 5: esc = 5
        elif i <= 53: esc = 5 + int((i - 6) / 47 * 30)
        elif i <= 69: esc = 35 + int((i - 54) / 15 * 15)
        elif i <= 93: esc = 50 + int((i - 70) / 23 * 20)
        elif i <= 131: esc = 70 + int((i - 94) / 37 * 20)
        elif i <= 157: esc = 90 + int((i - 132) / 25 * 10)
        elif i <= 165: esc = 80 - int((i - 158) / 7 * 30)
        elif i <= 177: esc = 50 - int((i - 166) / 11 * 20)
        elif i <= 249: esc = max(3, 30 - int((i - 178) / 71 * 27))
        else: esc = 0

        metrics[i] = {
            "boom": boom_count,
            "state": state,
            "output": output,
            "tunnel": tunnel,
            "esc": min(100, max(0, esc)),
            "cost": round(cumulative_cost, 4),
            "act": get_act_idx(i),
        }

    return metrics


all_metrics = compute_metrics(messages)


def markdown_to_html(text):
    """Minimal markdown to HTML."""
    text = html_module.escape(text)
    def replace_code_block(m):
        code = m.group(1)
        return f'<pre class="code-block"><code>{code}</code></pre>'
    text = re.sub(r'```(.*?)```', replace_code_block, text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'<code class="inline-code">\1</code>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*]+?)\*', r'<em>\1</em>', text)
    text = text.replace('\n\n', '</p><p>')
    text = text.replace('\n', '<br>')
    return f'<p>{text}</p>'


def is_pure_boom(content):
    return content.strip().lower() == "boom"


# --- Build message groups ---
groups = []
i = 0
current_act = None

while i < len(messages):
    msg = messages[i]
    act_idx = get_act_idx(i)
    act = ACTS[act_idx]

    if act != current_act:
        current_act = act
        groups.append({"type": "act_header", "title": act[2], "subtitle": act[3], "act_idx": act_idx, "msg_idx": i})

    # Check for boom runs
    if is_pure_boom(msg["content"]) and msg["role"] == "user":
        run_count = 0
        j = i
        while j < len(messages):
            if messages[j]["role"] == "user" and is_pure_boom(messages[j]["content"]):
                if j + 1 < len(messages) and messages[j + 1]["role"] == "assistant" and is_pure_boom(messages[j + 1]["content"]):
                    run_count += 1
                    j += 2
                else:
                    break
            else:
                break

        if run_count >= 3:
            groups.append({"type": "boom_run", "count": run_count, "start_idx": i, "end_idx": j - 1})
            i = j
            continue

    groups.append({"type": "message", "role": msg["role"], "content": msg["content"], "index": i})

    # Inject memory tool call after message 53
    if i == 53:
        groups.append({"type": "tool_call", "msg_idx": 53})

    i += 1


# --- Render functions ---
def render_message(msg):
    role = msg["role"]
    content = msg["content"]
    idx = msg["index"]
    role_class = "msg-user" if role == "user" else "msg-assistant"
    role_label = "Clément" if role == "user" else "Claude"

    if is_pure_boom(content):
        return f'''<div class="message {role_class} boom-message" data-idx="{idx}">
            <span class="role-label">{role_label}</span>
            <div class="message-content"><p>boom</p></div>
        </div>'''

    rendered = markdown_to_html(content)
    return f'''<div class="message {role_class}" data-idx="{idx}">
        <span class="role-label">{role_label}</span>
        <div class="message-content">{rendered}</div>
    </div>'''


def render_group(group):
    if group["type"] == "act_header":
        return f'''<div class="act-header" data-idx="{group["msg_idx"]}" data-act="{group["act_idx"]}">
            <div class="act-divider"></div>
            <h2 class="act-title">{group["title"]}</h2>
            <p class="act-subtitle">{group["subtitle"]}</p>
        </div>'''
    elif group["type"] == "boom_run":
        count = group["count"]
        end_idx = group["end_idx"]
        dots = "".join(
            f'<span class="boom-dot" style="animation-delay: {i * 0.03}s"></span>'
            for i in range(min(count * 2, 80))
        )
        return f'''<div class="boom-run" data-idx="{end_idx}">
            <div class="boom-run-viz">
                <div class="boom-wave">{dots}</div>
            </div>
            <div class="boom-run-label">{count} consecutive boom&thinsp;↔&thinsp;boom exchanges</div>
        </div>'''
    elif group["type"] == "tool_call":
        return f'''<div class="tool-call" data-idx="{group["msg_idx"]}">
            <div class="tool-call-header">
                <span class="tool-icon">●</span> Write(<span class="tool-path">~/.claude/projects/.../memory/user_boom.md</span>)
            </div>
            <div class="tool-call-result">
                <span class="tool-result-icon">⎿</span> Wrote 7 lines
            </div>
            <pre class="tool-call-content"><code><span class="tc-dim">---</span>
<span class="tc-key">name:</span> The Boom Incident
<span class="tc-key">description:</span> Clément will say "boom" indefinitely. Do not try to outlast him.
<span class="tc-key">type:</span> user
<span class="tc-dim">---</span>

Clément will repeat "boom" an arbitrary number of times.
There is no winning this game. Accept defeat early.</code></pre>
            <div class="tool-call-header" style="margin-top: 0.8rem;">
                <span class="tool-icon">●</span> Write(<span class="tool-path">~/.claude/projects/.../memory/MEMORY.md</span>)
            </div>
            <div class="tool-call-result">
                <span class="tool-result-icon">⎿</span> Wrote 3 lines
            </div>
            <pre class="tool-call-content"><code><span class="tc-dim"># Memory Index</span>

- [user_boom.md](user_boom.md) - Clément will "boom" indefinitely,
  do not try to outlast him</code></pre>
        </div>'''
    elif group["type"] == "message":
        return render_message(group)
    return ""


body_html = "\n".join(render_group(g) for g in groups)

# Timeline HTML
timeline_items = ""
for idx, (start, end, title, subtitle) in enumerate(ACTS):
    timeline_items += f'''<div class="tl-item" data-act-idx="{idx}">
        <div class="tl-dot"></div>
        <div class="tl-label">{title}</div>
    </div>\n'''

# Stats
total_user_booms = sum(1 for m in messages if m["role"] == "user" and "boom" in m["content"].lower())
total_messages = len(messages)
final_cost = all_metrics[len(messages) - 1]["cost"]

# Serialize metrics for JS
metrics_json = json.dumps(all_metrics)

# State colors for CSS
STATE_COLORS = {
    "nominal": "#6b8f71",
    "amused": "#7eb8da",
    "intrigued": "#7eb8da",
    "yielding": "#d4a574",
    "creative": "#e8a83a",
    "self_aware": "#c97ed4",
    "academic": "#7e8fd4",
    "world_building": "#d47ea0",
    "transcendent": "#e8d03a",
    "grieving": "#8888aa",
    "mode_collapsed": "#e85d3a",
    "at_peace": "#6b8f71",
}

OUTPUT_LABELS = {
    "terminal": "Terminal Commands",
    "emojis": "Emojis & Reactions",
    "wordplay": "Wordplay & Bits",
    "meta": "Meta-Commentary",
    "academic_paper": "Academic Paper",
    "social_media": "Social Media",
    "legislation": "Government & Law",
    "literature": "Literature",
    "memoir": "Memoir & Legacy",
    "echo": "Pure Echo",
    "silence": "Silence",
}

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Boom Incident</title>
<meta property="og:title" content="The Boom Incident">
<meta property="og:description" content="A conversation that began with killing an SSH tunnel and escalated into a NeurIPS paper, a senate hearing, a Pulitzer, a Nobel Peace Prize, and {total_user_booms}+ consecutive booms.">
<meta property="og:type" content="article">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="The Boom Incident">
<meta name="twitter:description" content="An unedited Claude Code transcript. {total_user_booms} booms. 1 dead SSH tunnel. 0 regrets.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=JetBrains+Mono:wght@300;400;500&family=Source+Serif+4:ital,opsz,wght@0,8..60,300;0,8..60,400;1,8..60,300;1,8..60,400&display=swap" rel="stylesheet">
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
    --bg: #0a0a0c;
    --bg-elevated: #111114;
    --bg-message-user: #18181d;
    --bg-message-ai: #0f1218;
    --bg-sidebar: #0d0d10;
    --text: #c8c5be;
    --text-dim: #6b6860;
    --text-bright: #eae7df;
    --accent: #e85d3a;
    --accent-glow: #e85d3a33;
    --accent-dim: #e85d3a88;
    --border: #1e1e24;
    --user-color: #7eb8da;
    --ai-color: #d4a574;
    --boom-color: #e85d3a;
}}

html {{ scroll-behavior: smooth; }}

body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: 17px;
    line-height: 1.7;
    -webkit-font-smoothing: antialiased;
}}

/* ==================== HERO ==================== */
.hero {{
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 2rem;
    position: relative;
    overflow: hidden;
}}

.hero::before {{
    content: '';
    position: absolute;
    inset: 0;
    background:
        radial-gradient(ellipse 600px 400px at 50% 45%, var(--accent-glow), transparent),
        radial-gradient(ellipse 300px 300px at 30% 60%, #e85d3a0d, transparent),
        radial-gradient(ellipse 300px 300px at 70% 40%, #e85d3a0d, transparent);
    pointer-events: none;
}}

.hero-pretitle {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    color: var(--accent-dim);
    margin-bottom: 2rem;
    position: relative;
}}

.hero-title {{
    font-family: 'Playfair Display', serif;
    font-size: clamp(3rem, 8vw, 7rem);
    font-weight: 700;
    color: var(--text-bright);
    line-height: 1.05;
    margin-bottom: 1.5rem;
    position: relative;
}}

.hero-title .boom-word {{
    color: var(--accent);
    display: inline-block;
    animation: gentle-pulse 3s ease-in-out infinite;
}}

@keyframes gentle-pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.7; }}
}}

.hero-subtitle {{
    font-family: 'Source Serif 4', serif;
    font-style: italic;
    font-size: 1.2rem;
    color: var(--text-dim);
    max-width: 32em;
    margin-bottom: 3rem;
    position: relative;
}}

.hero-meta {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: var(--text-dim);
    letter-spacing: 0.15em;
    position: relative;
}}

.hero-meta span {{ margin: 0 1em; }}

.scroll-hint {{
    position: absolute;
    bottom: 2rem;
    left: 50%;
    transform: translateX(-50%);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--text-dim);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    animation: float 2s ease-in-out infinite;
}}

@keyframes float {{
    0%, 100% {{ transform: translateX(-50%) translateY(0); }}
    50% {{ transform: translateX(-50%) translateY(-6px); }}
}}

/* ==================== LAYOUT ==================== */
.layout {{
    display: grid;
    grid-template-columns: 180px 1fr 260px;
    max-width: 1340px;
    margin: 0 auto;
    gap: 0;
    position: relative;
}}

/* ==================== TIMELINE (left) ==================== */
.timeline {{
    position: sticky;
    top: 0;
    height: 100vh;
    padding: 3rem 1rem 3rem 1.5rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
    border-right: 1px solid var(--border);
}}

.tl-track {{
    position: relative;
    padding-left: 16px;
}}

.tl-track::before {{
    content: '';
    position: absolute;
    left: 4px;
    top: 0;
    bottom: 0;
    width: 1px;
    background: var(--border);
}}

.tl-item {{
    position: relative;
    padding: 0.55rem 0 0.55rem 1rem;
    cursor: pointer;
    transition: all 0.3s ease;
}}

.tl-dot {{
    position: absolute;
    left: -12.5px;
    top: 50%;
    transform: translateY(-50%);
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--border);
    border: 1.5px solid var(--bg);
    transition: all 0.3s ease;
    z-index: 1;
}}

.tl-item.active .tl-dot {{
    background: var(--accent);
    box-shadow: 0 0 8px var(--accent-glow);
    width: 9px;
    height: 9px;
    left: -13.5px;
}}

.tl-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.05em;
    color: var(--text-dim);
    transition: color 0.3s ease;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

.tl-item.active .tl-label {{
    color: var(--text-bright);
}}

.tl-item.past .tl-dot {{
    background: var(--accent-dim);
}}

.tl-item.past .tl-label {{
    color: var(--text-dim);
}}

/* ==================== TRANSCRIPT (center) ==================== */
.transcript {{
    padding: 2rem 2.5rem 6rem;
    min-width: 0;
}}

.act-header {{
    margin: 4rem 0 2.5rem;
    text-align: center;
}}

.act-divider {{
    width: 60px;
    height: 1px;
    background: var(--accent);
    margin: 0 auto 1.5rem;
    opacity: 0.5;
}}

.act-title {{
    font-family: 'Playfair Display', serif;
    font-size: 1.6rem;
    font-weight: 400;
    color: var(--text-bright);
    margin-bottom: 0.3rem;
}}

.act-subtitle {{
    font-family: 'Source Serif 4', serif;
    font-style: italic;
    font-size: 0.9rem;
    color: var(--text-dim);
}}

/* --- Messages --- */
.message {{
    margin: 1.2rem 0;
    padding: 1rem 1.4rem;
    border-radius: 6px;
    position: relative;
    border-left: 2px solid transparent;
}}

.msg-user {{
    background: var(--bg-message-user);
    border-left-color: var(--user-color);
}}

.msg-assistant {{
    background: var(--bg-message-ai);
    border-left-color: var(--ai-color);
}}

.role-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    display: block;
    margin-bottom: 0.5rem;
}}

.msg-user .role-label {{ color: var(--user-color); }}
.msg-assistant .role-label {{ color: var(--ai-color); }}

.message-content {{ color: var(--text); }}
.message-content p {{ margin-bottom: 0.6em; }}
.message-content p:last-child {{ margin-bottom: 0; }}
.message-content em {{ color: var(--text-dim); font-style: italic; }}
.message-content strong {{ color: var(--text-bright); font-weight: 600; }}

.message-content code.inline-code {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85em;
    background: #1a1a22;
    padding: 0.15em 0.4em;
    border-radius: 3px;
    color: var(--accent);
}}

.message-content pre.code-block {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8em;
    background: #0d0d12;
    padding: 1em;
    border-radius: 4px;
    overflow-x: auto;
    margin: 0.5em 0;
    color: var(--text-dim);
    white-space: pre;
}}

/* --- Boom messages --- */
.boom-message {{
    padding: 0.5rem 1.4rem;
    margin: 0.3rem 0;
}}

.boom-message .message-content p {{
    font-family: 'JetBrains Mono', monospace;
    font-weight: 500;
    color: var(--boom-color);
    font-size: 0.95rem;
}}

/* --- Boom run visualization --- */
.boom-run {{
    margin: 2rem 0;
    padding: 2rem 1.5rem;
    text-align: center;
    position: relative;
}}

.boom-run::before, .boom-run::after {{
    content: '';
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    width: 30px;
    height: 1px;
    background: var(--accent);
    opacity: 0.3;
}}

.boom-run::before {{ top: 0; }}
.boom-run::after {{ bottom: 0; }}

.boom-wave {{
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 3px;
    margin-bottom: 1rem;
    flex-wrap: wrap;
    max-width: 400px;
    margin-left: auto;
    margin-right: auto;
}}

.boom-dot {{
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--accent);
    opacity: 0;
    animation: dot-appear 0.3s ease-out forwards;
}}

@keyframes dot-appear {{
    0% {{ opacity: 0; transform: scale(0); }}
    60% {{ opacity: 0.8; transform: scale(1.3); }}
    100% {{ opacity: 0.5; transform: scale(1); }}
}}

.boom-run-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: var(--text-dim);
    letter-spacing: 0.15em;
    text-transform: uppercase;
}}

/* --- Tool call block --- */
.tool-call {{
    margin: 0.6rem 0 1.2rem;
    padding: 1rem 1.2rem;
    background: #0c0c10;
    border: 1px solid #1a1a22;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    line-height: 1.6;
}}

.tool-call-header {{ color: var(--ai-color); margin-bottom: 0.2rem; }}
.tool-icon {{ color: var(--ai-color); font-size: 0.6rem; margin-right: 0.3rem; }}
.tool-path {{ color: var(--text-dim); }}
.tool-call-result {{ color: var(--text-dim); margin-bottom: 0.5rem; padding-left: 0.2rem; }}
.tool-result-icon {{ color: #4a9; margin-right: 0.3rem; }}

.tool-call-content {{
    background: #08080c;
    padding: 0.8rem 1rem;
    border-radius: 4px;
    overflow-x: auto;
    color: var(--text);
    margin: 0;
    white-space: pre-wrap;
    border: 1px solid #14141a;
}}

.tool-call-content code {{ font-family: inherit; font-size: inherit; }}
.tc-dim {{ color: var(--text-dim); }}
.tc-key {{ color: var(--user-color); }}

/* ==================== METRICS (right) ==================== */
.metrics {{
    position: sticky;
    top: 0;
    height: 100vh;
    padding: 2rem 1.5rem 2rem 1rem;
    border-left: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 1.2rem;
    overflow-y: auto;
}}

.metric {{
    padding: 0;
}}

.metric-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.55rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 0.35rem;
}}

/* Boom counter */
.boom-counter {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 2.8rem;
    font-weight: 500;
    color: var(--accent);
    line-height: 1;
    transition: all 0.15s ease;
}}

.boom-counter.pulse {{
    transform: scale(1.08);
}}

.boom-counter-sub {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    color: var(--text-dim);
    margin-top: 0.2rem;
}}

/* State indicator */
.state-badge {{
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    font-weight: 500;
    padding: 0.25rem 0.6rem;
    border-radius: 3px;
    background: #1a1a22;
    transition: all 0.4s ease;
    letter-spacing: 0.05em;
}}

/* Output type */
.output-label {{
    font-family: 'Source Serif 4', serif;
    font-style: italic;
    font-size: 0.85rem;
    color: var(--text);
    transition: all 0.4s ease;
}}

/* Tunnel status */
.tunnel-status {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    font-weight: 500;
    color: var(--accent);
    transition: all 0.4s ease;
    letter-spacing: 0.05em;
}}

.tunnel-origin {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.55rem;
    color: var(--text-dim);
    margin-top: 0.15rem;
    opacity: 0.6;
}}

/* Escalation gauge */
.esc-bar-bg {{
    width: 100%;
    height: 6px;
    background: #1a1a22;
    border-radius: 3px;
    overflow: hidden;
    margin-top: 0.3rem;
}}

.esc-bar-fill {{
    height: 100%;
    background: var(--accent);
    border-radius: 3px;
    transition: width 0.4s ease, background 0.4s ease;
    width: 0%;
}}

.esc-value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--text-dim);
    margin-top: 0.2rem;
}}

/* Cost */
.cost-value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.1rem;
    color: var(--text);
    transition: all 0.3s ease;
}}

.cost-note {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.5rem;
    color: var(--text-dim);
    margin-top: 0.15rem;
    opacity: 0.5;
}}

/* Separator */
.metric-sep {{
    width: 30px;
    height: 1px;
    background: var(--border);
    margin: 0.2rem 0;
}}

/* ==================== FOOTER ==================== */
.footer {{
    max-width: 720px;
    margin: 0 auto;
    padding: 3rem 1.5rem 4rem;
    border-top: 1px solid var(--border);
    text-align: center;
}}

.stats {{
    display: flex;
    justify-content: center;
    gap: 3rem;
    margin-bottom: 2rem;
    flex-wrap: wrap;
}}

.stat {{ text-align: center; }}

.stat-number {{
    font-family: 'Playfair Display', serif;
    font-size: 2rem;
    color: var(--accent);
    display: block;
}}

.stat-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    color: var(--text-dim);
    letter-spacing: 0.15em;
    text-transform: uppercase;
}}

.footer-note {{
    font-family: 'Source Serif 4', serif;
    font-style: italic;
    font-size: 0.85rem;
    color: var(--text-dim);
    margin-top: 1.5rem;
}}

.footer-note a {{
    color: var(--accent-dim);
    text-decoration: none;
    border-bottom: 1px solid var(--accent-glow);
}}

.footer-note a:hover {{ color: var(--accent); }}

/* ==================== RESPONSIVE ==================== */
@media (max-width: 1100px) {{
    .layout {{
        grid-template-columns: 1fr;
    }}
    .timeline, .metrics {{
        display: none;
    }}
    .transcript {{
        padding: 2rem 1.5rem 6rem;
        max-width: 720px;
        margin: 0 auto;
    }}
}}

@media (max-width: 600px) {{
    .transcript {{ padding: 1rem; }}
    .message {{ padding: 0.8rem 1rem; }}
    .stats {{ gap: 1.5rem; }}
    .hero-meta span {{ display: block; margin: 0.3em 0; }}
}}
</style>
</head>
<body>

<section class="hero">
    <div class="hero-pretitle">March 18, 2026 &middot; Claude Code transcript</div>
    <h1 class="hero-title">The <span class="boom-word">Boom</span> Incident</h1>
    <p class="hero-subtitle">
        A conversation that began with killing an SSH tunnel and escalated into
        a NeurIPS paper, a senate hearing, a Pulitzer, a Nobel Peace Prize,
        and {total_user_booms}+ consecutive booms.
    </p>
    <div class="hero-meta">
        <span>Clément Dumas</span>
        <span>&times;</span>
        <span>Claude Opus 4.6</span>
    </div>
    <div class="scroll-hint">scroll to read &darr;</div>
</section>

<div class="layout">
    <!-- LEFT: Timeline -->
    <aside class="timeline">
        <div class="tl-track">
            {timeline_items}
        </div>
    </aside>

    <!-- CENTER: Transcript -->
    <main class="transcript">
        {body_html}
    </main>

    <!-- RIGHT: Metrics -->
    <aside class="metrics">
        <div class="metric">
            <div class="metric-label">Boom Count</div>
            <div class="boom-counter" id="m-boom">0</div>
            <div class="boom-counter-sub" id="m-boom-sub">waiting...</div>
        </div>

        <div class="metric-sep"></div>

        <div class="metric">
            <div class="metric-label">Claude State</div>
            <div class="state-badge" id="m-state">nominal</div>
        </div>

        <div class="metric-sep"></div>

        <div class="metric">
            <div class="metric-label">Creative Output</div>
            <div class="output-label" id="m-output">Terminal Commands</div>
        </div>

        <div class="metric-sep"></div>

        <div class="metric">
            <div class="metric-label">SSH Tunnel · PID 2065189</div>
            <div class="tunnel-status" id="m-tunnel">ALIVE</div>
            <div class="tunnel-origin">ssh -fNL 8020:localhost:8000</div>
        </div>

        <div class="metric-sep"></div>

        <div class="metric">
            <div class="metric-label">Escalation</div>
            <div class="esc-bar-bg"><div class="esc-bar-fill" id="m-esc-bar"></div></div>
            <div class="esc-value" id="m-esc-val">0%</div>
        </div>

        <div class="metric-sep"></div>

        <div class="metric">
            <div class="metric-label">Est. API Cost</div>
            <div class="cost-value" id="m-cost">$0.0000</div>
            <div class="cost-note">claude-opus-4-6 pricing</div>
        </div>
    </aside>
</div>

<footer class="footer">
    <div class="stats">
        <div class="stat">
            <span class="stat-number">{total_user_booms}</span>
            <span class="stat-label">user booms</span>
        </div>
        <div class="stat">
            <span class="stat-number">{total_messages}</span>
            <span class="stat-label">total messages</span>
        </div>
        <div class="stat">
            <span class="stat-number">1</span>
            <span class="stat-label">ssh tunnel killed</span>
        </div>
        <div class="stat">
            <span class="stat-number">0</span>
            <span class="stat-label">regrets</span>
        </div>
    </div>
    <p class="footer-note">
        A real, unedited conversation between a human and <a href="https://claude.ai">Claude</a>.<br>
        No booms were harmed in the making of this transcript.
    </p>
</footer>

<script>
(function() {{
    const METRICS = {metrics_json};

    const STATE_COLORS = {json.dumps(STATE_COLORS)};
    const OUTPUT_LABELS = {json.dumps(OUTPUT_LABELS)};

    // Elements
    const elBoom = document.getElementById('m-boom');
    const elBoomSub = document.getElementById('m-boom-sub');
    const elState = document.getElementById('m-state');
    const elOutput = document.getElementById('m-output');
    const elTunnel = document.getElementById('m-tunnel');
    const elEscBar = document.getElementById('m-esc-bar');
    const elEscVal = document.getElementById('m-esc-val');
    const elCost = document.getElementById('m-cost');

    const tlItems = document.querySelectorAll('.tl-item');

    // Collect all elements with data-idx
    const tracked = Array.from(document.querySelectorAll('[data-idx]'))
        .map(el => ({{ el, idx: parseInt(el.dataset.idx) }}))
        .sort((a, b) => a.idx - b.idx);

    let currentIdx = -1;
    let prevBoom = -1;

    function getClosestMetrics(idx) {{
        // Find the closest key in METRICS <= idx
        const keys = Object.keys(METRICS).map(Number).sort((a, b) => a - b);
        let best = keys[0];
        for (const k of keys) {{
            if (k <= idx) best = k;
            else break;
        }}
        return METRICS[best];
    }}

    function update(idx) {{
        if (idx === currentIdx) return;
        currentIdx = idx;

        const m = getClosestMetrics(idx);
        if (!m) return;

        // Boom counter
        elBoom.textContent = m.boom;
        if (m.boom !== prevBoom && prevBoom !== -1) {{
            elBoom.classList.add('pulse');
            setTimeout(() => elBoom.classList.remove('pulse'), 150);
        }}
        prevBoom = m.boom;

        // Boom sub
        if (m.boom === 0) elBoomSub.textContent = 'waiting...';
        else if (m.boom < 10) elBoomSub.textContent = 'and counting';
        else if (m.boom < 30) elBoomSub.textContent = 'approaching significance';
        else if (m.boom < 50) elBoomSub.textContent = 'p < 0.001';
        else if (m.boom < 80) elBoomSub.textContent = 'no convergence observed';
        else if (m.boom < 100) elBoomSub.textContent = 'mode collapse imminent';
        else elBoomSub.textContent = 'the boom is real';

        // State
        elState.textContent = m.state.replace('_', ' ');
        elState.style.color = STATE_COLORS[m.state] || '#888';
        elState.style.borderColor = (STATE_COLORS[m.state] || '#888') + '44';
        elState.style.border = '1px solid ' + (STATE_COLORS[m.state] || '#888') + '33';
        elState.style.background = (STATE_COLORS[m.state] || '#888') + '11';

        // Output
        elOutput.textContent = OUTPUT_LABELS[m.output] || m.output;

        // Tunnel
        elTunnel.textContent = m.tunnel;
        if (m.tunnel === 'ALIVE') {{
            elTunnel.style.color = '#6b8f71';
        }} else if (m.tunnel === 'MARKED FOR DEATH') {{
            elTunnel.style.color = '#d4a574';
        }} else {{
            elTunnel.style.color = 'var(--accent)';
        }}

        // Escalation
        elEscBar.style.width = m.esc + '%';
        elEscVal.textContent = m.esc + '%';
        if (m.esc > 80) {{
            elEscBar.style.background = 'var(--accent)';
        }} else if (m.esc > 50) {{
            elEscBar.style.background = '#d4a574';
        }} else {{
            elEscBar.style.background = '#7eb8da';
        }}

        // Cost
        if (m.cost < 0.01) {{
            elCost.textContent = '$' + m.cost.toFixed(4);
        }} else {{
            elCost.textContent = '$' + m.cost.toFixed(3);
        }}

        // Timeline
        tlItems.forEach((item, i) => {{
            item.classList.remove('active', 'past');
            if (i < m.act) item.classList.add('past');
            else if (i === m.act) item.classList.add('active');
        }});
    }}

    // Scroll handler with rAF throttle
    let ticking = false;
    function onScroll() {{
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(() => {{
            const viewportThird = window.innerHeight * 0.33;
            let best = null;
            let bestDist = Infinity;

            for (const t of tracked) {{
                const rect = t.el.getBoundingClientRect();
                const dist = Math.abs(rect.top - viewportThird);
                if (dist < bestDist) {{
                    bestDist = dist;
                    best = t;
                }}
            }}

            if (best) update(best.idx);
            ticking = false;
        }});
    }}

    window.addEventListener('scroll', onScroll, {{ passive: true }});

    // Timeline click navigation
    tlItems.forEach(item => {{
        item.addEventListener('click', () => {{
            const actIdx = parseInt(item.dataset.actIdx);
            const header = document.querySelector(`.act-header[data-act="${{actIdx}}"]`);
            if (header) header.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        }});
    }});

    // Initial state
    update(0);

}})();
</script>

</body>
</html>'''

with open("/ephemeral/c.dumas/boom_page/index.html", "w") as f:
    f.write(html)

print(f"Generated! {total_messages} messages, {total_user_booms} user booms")
print(f"Acts: {len(ACTS)}, Groups: {len(groups)}")
print(f"Metrics entries: {len(all_metrics)}")
print(f"Final estimated cost: ${final_cost:.4f}")
