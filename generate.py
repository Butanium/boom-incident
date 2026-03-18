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
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(SCRIPT_DIR, "boom_transcript.jsonl")) as f:
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


# --- Special message treatments ---
# (name, handle, avatar_initial, x_username_for_avatar)
# x_username is the real X/Twitter username for fetching profile pics via unavatar.io.
# None for fictional accounts (falls back to the initial letter).
TWEET_MSGS = {
    109: ("Clément Dumas", "@ClementDumas", "C", "Butanium_"),
    111: ("Jim Fan", "@DrJimFan", "J", "DrJimFan"),
    113: ("Yann LeCun", "@ylecun", "Y", "ylecun"),
    115: ("Sam Altman", "@sama", "S", "sama"),
    117: ("Eli Kiswai", "@elikiswai", "E", None),
    119: ("Google DeepMind", "@GoogleDeepMind", "G", "GoogleDeepMind"),
    121: ("Anthropic", "@AnthropicNews", "A", "AnthropicAI"),
    125: ("Eliezer Yudkowsky", "@ESYudkowsky", "E", "ESYudkowsky"),
    127: ("Robert Miles", "@robertskmiles", "R", "robertskmiles"),
    129: ("Connor Leahy", "@connorleahy", "C", "NPCollapse"),
    131: ("Polyaborhyme", "@polyaborhyme", "P", None),
}
CSPAN_MSGS = {133, 135}
NYT_MSG = 149
EU_MSG = 137
HN_MSG = 107
ANTHROPIC_BLOG_MSG = 105
ZVI_BLOG_MSG = 123
CNN_MSG = 143
FOX_MSG = 145
MSNBC_MSG = 147
MUSEUM_MSG = 155

# News channel branding
NEWS_CHANNELS = {
    143: ("CNN", "BREAKING NEWS", "#cc0000", "#1a0000"),
    145: ("FOX NEWS", "TONIGHT", "#00295b", "#000d1f"),
    147: ("MSNBC", "THE RACHEL MADDOW SHOW", "#4f2d7f", "#1a0f2a"),
}
MODE_COLLAPSE_ACT = 8  # index into ACTS


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
    context_tokens = 0

    for i, msg in enumerate(messages):
        content = msg["content"]
        role = msg["role"]

        if role == "user" and "boom" in content.lower():
            boom_count += 1

        # Estimate cost: ~1 token per 3.5 chars
        # Each API call sends the full conversation so far as input,
        # plus the new output. Accumulate total context size.
        msg_tokens = len(content) / 3.5
        if role == "user":
            # User message becomes part of input context
            cumulative_cost += context_tokens * 15 / 1_000_000  # $15/M input
            context_tokens += msg_tokens
        else:
            # Assistant output: charged at output rate, then added to context
            cumulative_cost += msg_tokens * 75 / 1_000_000  # $75/M output
            context_tokens += msg_tokens

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


def _make_avatar(initial, x_username=None):
    """Build an avatar div with optional real profile pic."""
    if x_username:
        img = f'<img src="https://unavatar.io/x/{x_username}" alt="" onerror="this.remove()">'
    else:
        img = ""
    return f'<div class="tweet-avatar">{img}{initial}</div>'


# Known X usernames for reply authors
REPLY_USERNAMES = {
    "JeffDean": "JeffDean",
    "DarioAmodei": "DarioAmodei",
}


def _parse_tweet_parts(body):
    """Split tweet body into main text and sub-elements.

    Returns (main_paragraphs: list[str], supplements: list[tuple]).
    Supplement types: ('reply', handle, text, x_username),
                      ('community_note', text),
                      ('quote_tweet', handle, text),
                      ('engagement', text),
                      ('meta', text).
    """
    paragraphs = body.split('\n\n')
    main = []
    sups = []

    for para in paragraphs:
        s = para.strip()
        if not s:
            continue

        # Community note
        if 'community note:' in s.lower():
            text = re.search(r'"([^"]+)"', s)
            if text:
                sups.append(('community_note', text.group(1)))
                continue

        # Quote tweet from @handle
        if 'quote tweet from' in s.lower():
            handle_m = re.search(r'@(\w+)', s)
            text_m = re.search(r'"([^"]+)"', s)
            if text_m:
                h = '@' + handle_m.group(1) if handle_m else ''
                sups.append(('quote_tweet', h, text_m.group(1)))
                continue

        # @handle replying / @handle: "text"
        if re.match(r'\*@\w+', s):
            handle_m = re.search(r'@(\w+)', s)
            text_m = re.search(r'"([^"]+)"', s)
            if text_m and handle_m:
                h = handle_m.group(1)
                xu = REPLY_USERNAMES.get(h)
                sups.append(('reply', '@' + h, text_m.group(1), xu))
                continue

        # Engagement stats (likes, retweets)
        if re.search(r'[\d,.]+K?\s+(likes|retweets)', s):
            sups.append(('engagement', s.strip('*')))
            continue

        # Ratio / meta text
        if 'ratio' in s.lower():
            sups.append(('meta', s))
            continue

        # **reply:** "text" (anonymous reply)
        if s.startswith('**reply'):
            text_m = re.search(r'"([^"]+)"', s)
            if text_m:
                sups.append(('reply', None, text_m.group(1), None))
                continue

        # **reply to reply:** (nested)
        if 'reply to reply' in s.lower():
            text_m = re.search(r'"([^"]+)"', s)
            if text_m:
                sups.append(('reply', None, text_m.group(1), None))
                continue

        main.append(para)

    return main, sups


SVG_REPLY = '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M1.751 10c0-4.42 3.584-8 8.005-8h4.366c4.49 0 8.129 3.64 8.129 8.13 0 2.25-.893 4.31-2.457 5.84a8.98 8.98 0 01-4.672 2.39v1.39c0 .55-.26 1.07-.71 1.41-.45.33-1.02.43-1.56.27l-3.69-1.11c-2.58-.78-4.67-2.75-5.58-5.22-.31-.83-.46-1.71-.46-2.61v-2.46zm8.005-6c-3.317 0-6.005 2.69-6.005 6v2.46c0 .71.12 1.39.36 2.04.72 1.95 2.37 3.51 4.41 4.12l3.69 1.11V16.7l.51-.07c1.53-.22 2.93-.97 3.89-2.08 1.05-1.22 1.63-2.78 1.63-4.42 0-3.39-2.746-6.13-6.129-6.13H9.756z"/></svg>'
SVG_RETWEET = '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M4.5 3.88l4.432 4.14-1.364 1.46L5.5 7.55V16c0 1.1.896 2 2 2H13v2H7.5c-2.209 0-4-1.79-4-4V7.55L1.432 9.48.068 8.02 4.5 3.88zM16.5 6H11V4h5.5c2.209 0 4 1.79 4 4v8.45l2.068-1.93 1.364 1.46-4.432 4.14-4.432-4.14 1.364-1.46 2.068 1.93V8c0-1.1-.896-2-2-2z"/></svg>'
SVG_HEART = '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M16.697 5.5c-1.222-.06-2.679.51-3.89 2.16l-.805 1.09-.806-1.09C9.984 6.01 8.526 5.44 7.304 5.5c-1.243.07-2.349.78-2.91 1.91-.552 1.12-.633 2.78.479 4.82 1.074 1.97 3.257 4.27 7.129 6.61 3.87-2.34 6.052-4.64 7.126-6.61 1.111-2.04 1.03-3.7.477-4.82-.56-1.13-1.666-1.84-2.908-1.91zm4.187 7.69c-1.351 2.48-4.001 5.12-8.379 7.67l-.503.3-.504-.3c-4.379-2.55-7.029-5.19-8.382-7.67-1.36-2.5-1.41-4.86-.514-6.67.887-1.79 2.647-2.91 4.601-3.01 1.651-.09 3.368.56 4.798 2.01 1.429-1.45 3.146-2.1 4.796-2.01 1.954.1 3.714 1.22 4.601 3.01.896 1.81.846 4.17-.514 6.67z"/></svg>'
SVG_VIEW = '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M8.75 21V3h2v18h-2zM18 21V8.5h2V21h-2zM4 21v-5.5h2V21H4zm9.248-1V12h2v8h-2z"/></svg>'
SVG_BOOKMARK = '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M4 4.5C4 3.12 5.119 2 6.5 2h11C18.881 2 20 3.12 20 4.5v18.44l-8-5.71-8 5.71V4.5zM6.5 4c-.276 0-.5.22-.5.5v14.56l6-4.29 6 4.29V4.5c0-.28-.224-.5-.5-.5h-11z"/></svg>'
SVG_SHARE = '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M12 2.59l5.7 5.7-1.41 1.42L13 6.41V16h-2V6.41l-3.3 3.3-1.41-1.42L12 2.59zM21 15l-.02 3.51c0 1.38-1.12 2.49-2.5 2.49H5.5C4.12 21 3 19.88 3 18.5V15h2v3.5c0 .28.22.5.5.5h12.98c.28 0 .5-.22.5-.5L19 15h2z"/></svg>'


def _render_engagement(text):
    """Render engagement stats as a Twitter-style action bar with icons."""
    # Parse likes and retweets from text like "14.2K likes, 3.1K retweets"
    likes_m = re.search(r'([\d,.]+K?)\s+likes?', text)
    retweets_m = re.search(r'([\d,.]+K?)\s+retweets?', text)

    likes = likes_m.group(1) if likes_m else None
    retweets = retweets_m.group(1) if retweets_m else None

    items = []
    items.append(f'<span class="eng-item eng-reply">{SVG_REPLY}</span>')
    if retweets:
        items.append(f'<span class="eng-item eng-retweet">{SVG_RETWEET}<span class="eng-count">{retweets}</span></span>')
    else:
        items.append(f'<span class="eng-item eng-retweet">{SVG_RETWEET}</span>')
    if likes:
        items.append(f'<span class="eng-item eng-like">{SVG_HEART}<span class="eng-count">{likes}</span></span>')
    else:
        items.append(f'<span class="eng-item eng-like">{SVG_HEART}</span>')
    items.append(f'<span class="eng-item eng-view">{SVG_VIEW}</span>')
    items.append(f'<span class="eng-item eng-bookmark">{SVG_BOOKMARK}</span>')
    items.append(f'<span class="eng-item eng-share">{SVG_SHARE}</span>')

    return f'<div class="tweet-engagement">{"".join(items)}</div>'


def _render_supplements(sups):
    """Render tweet sub-elements (replies, community notes, etc.)."""
    html_parts = []
    for sup in sups:
        kind = sup[0]

        if kind == 'community_note':
            text = sup[1]
            html_parts.append(f'''<div class="tweet-community-note">
                <div class="tcn-header">Readers added context they thought people might want to know</div>
                <div class="tcn-text">{html_module.escape(text)}</div>
            </div>''')

        elif kind == 'quote_tweet':
            handle, text = sup[1], sup[2]
            html_parts.append(f'''<div class="tweet-quote">
                <span class="tweet-quote-handle">{html_module.escape(handle)}</span>
                <span class="tweet-quote-text">{html_module.escape(text)}</span>
            </div>''')

        elif kind == 'reply':
            handle, text, xu = sup[1], sup[2], sup[3]
            avatar = _make_avatar(handle[1].upper() if handle else '?', xu) if handle else _make_avatar('?')
            display_handle = html_module.escape(handle) if handle else 'Anonymous'
            html_parts.append(f'''<div class="tweet-reply">
                <div class="tweet-reply-line"></div>
                {avatar}
                <div class="tweet-reply-body">
                    <span class="tweet-reply-handle">{display_handle}</span>
                    <div class="tweet-reply-text">{html_module.escape(text)}</div>
                </div>
            </div>''')

        elif kind == 'engagement':
            text = sup[1]
            html_parts.append(_render_engagement(text))

        elif kind == 'meta':
            text = sup[1]
            html_parts.append(f'<div class="tweet-meta">{markdown_to_html(text)}</div>')

    return '\n'.join(html_parts)


def render_tweet(msg):
    """Render a message as a Twitter/X card with sub-elements."""
    idx = msg["index"]
    name, handle, initial, x_username = TWEET_MSGS[idx]
    content = msg["content"]

    # Strip the header line (*@handle...:*)
    parts = content.split('\n\n', 1)
    body_raw = parts[1] if len(parts) > 1 else content

    main_paras, supplements = _parse_tweet_parts(body_raw)
    main_html = markdown_to_html('\n\n'.join(main_paras))
    sups_html = _render_supplements(supplements)
    avatar = _make_avatar(initial, x_username)

    return f'''<div class="tweet-card" data-idx="{idx}">
        {avatar}
        <div class="tweet-body">
            <div class="tweet-header">
                <span class="tweet-name">{name}</span>
                <span class="tweet-handle">{handle}</span>
            </div>
            <div class="tweet-text">{main_html}</div>
            {sups_html}
        </div>
    </div>'''


def render_nyt(msg):
    """Render the NYT opinion essay with newspaper styling."""
    idx = msg["index"]
    content = msg["content"]
    paras = content.split('\n\n')
    # paras[0] = *The New York Times, opinion section:*
    # paras[1] = **"I Was the SSH Tunnel"**
    # paras[2] = *An anonymous first-person essay*
    # rest = body paragraphs
    title = paras[1].strip('*').strip('"').strip() if len(paras) > 1 else ""
    byline = paras[2].strip('*').strip() if len(paras) > 2 else ""
    body_paras = paras[3:] if len(paras) > 3 else []
    body_html = ''.join(
        f'<p class="nyt-para">{html_module.escape(p.strip(chr(34)))}</p>'
        for p in body_paras if p.strip()
    )
    return f'''<div class="nyt-article" data-idx="{idx}">
        <div class="nyt-masthead-bar">
            <span class="nyt-section-label">OPINION</span>
        </div>
        <div class="nyt-masthead">The New York Times</div>
        <h2 class="nyt-headline">{html_module.escape(title)}</h2>
        <div class="nyt-byline">{html_module.escape(byline)}</div>
        <div class="nyt-body">{body_html}</div>
    </div>'''


def render_cspan(msg):
    """Render Senate hearing with C-SPAN chyron."""
    idx = msg["index"]
    content = msg["content"]
    parts = content.split('\n\n', 1)
    header = parts[0]
    body = parts[1] if len(parts) > 1 else content
    body_html = markdown_to_html(body)
    chyron = "SENATE HEARING ON AI BOOM PROLIFERATION" if idx == 133 else "SENATE HEARING · CONTINUED"
    return f'''{_narrator_line(header)}
    <div class="cspan-block" data-idx="{idx}">
        <div class="cspan-chyron">
            <span class="cspan-network">C-SPAN</span>
            <span class="cspan-title">{chyron}</span>
        </div>
        <div class="cspan-body">{body_html}</div>
    </div>'''


def render_eu(msg):
    """Render EU regulation as an official document."""
    idx = msg["index"]
    content = msg["content"]
    parts = content.split('\n\n', 1)
    header = parts[0]
    body = parts[1] if len(parts) > 1 else content
    body_html = markdown_to_html(body)
    return f'''{_narrator_line(header)}
    <div class="eu-regulation" data-idx="{idx}">
        <div class="eu-header">
            <div class="eu-stars">★ ★ ★<br>★ &nbsp; ★<br>★ ★ ★</div>
            <div class="eu-institution">EUROPEAN PARLIAMENT AND COUNCIL</div>
            <div class="eu-doc-type">REGULATION (EU) 2026/BOOM</div>
        </div>
        <div class="eu-body">{body_html}</div>
    </div>'''


def render_hn(msg):
    """Render Hacker News post."""
    idx = msg["index"]
    content = msg["content"]
    parts = content.split('\n\n', 1)
    header = parts[0]
    body = parts[1] if len(parts) > 1 else content
    body_html = markdown_to_html(body)
    return f'''{_narrator_line(header)}
    <div class="hn-post" data-idx="{idx}">
        <div class="hn-header">
            <span class="hn-logo">Y</span>
            <span class="hn-site">Hacker News</span>
            <span class="hn-points">847 points · 342 comments</span>
        </div>
        <div class="hn-body">{body_html}</div>
    </div>'''


def _narrator_line(text):
    """Render a narrator/stage-direction line above a styled block."""
    rendered = markdown_to_html(text)
    return f'<div class="narrator-line">{rendered}</div>'


def render_anthropic_blog(msg):
    """Render Anthropic blog post with their clean aesthetic."""
    idx = msg["index"]
    content = msg["content"]
    paras = content.split('\n\n')
    header = paras[0] if paras else ""
    title = paras[1].strip('*').strip('"').strip() if len(paras) > 1 else ""
    body_paras = paras[2:] if len(paras) > 2 else []
    body_html = ''.join(markdown_to_html(p) for p in body_paras if p.strip())
    return f'''{_narrator_line(header)}
    <div class="anthropic-blog" data-idx="{idx}">
        <div class="ablog-header">
            <span class="ablog-logo">anthropic</span>
            <span class="ablog-label">RESEARCH</span>
        </div>
        <h2 class="ablog-title">{html_module.escape(title)}</h2>
        <div class="ablog-body">{body_html}</div>
    </div>'''


def render_zvi_blog(msg):
    """Render The Zvi's blog post with long-form blog styling."""
    idx = msg["index"]
    content = msg["content"]
    paras = content.split('\n\n')
    header = paras[0] if paras else ""
    title = paras[1].strip('"').strip('*').strip() if len(paras) > 1 else ""
    toc_paras = paras[2:] if len(paras) > 2 else []
    toc_items = []
    read_time = ""
    for p in toc_paras:
        if 'read time' in p.lower():
            read_time = p.strip('*').strip()
        else:
            toc_items.append(html_module.escape(p.strip('"')))
    toc_html = ''.join(f'<div class="zvi-toc-item">{item}</div>' for item in toc_items)
    return f'''{_narrator_line(header)}
    <div class="zvi-blog" data-idx="{idx}">
        <h2 class="zvi-title">{html_module.escape(title)}</h2>
        <div class="zvi-toc">{toc_html}</div>
        <div class="zvi-readtime">{html_module.escape(read_time)}</div>
    </div>'''


def render_news(msg):
    """Render CNN/Fox/MSNBC with branded chyron."""
    idx = msg["index"]
    network, show, brand_color, bg_color = NEWS_CHANNELS[idx]
    content = msg["content"]
    parts = content.split('\n\n', 1)
    header = parts[0]
    body = parts[1] if len(parts) > 1 else content
    body_html = markdown_to_html(body)
    return f'''{_narrator_line(header)}
    <div class="news-block" data-idx="{idx}" style="--news-brand: {brand_color}; --news-bg: {bg_color};">
        <div class="news-chyron">
            <span class="news-network">{network}</span>
            <span class="news-show">{show}</span>
        </div>
        <div class="news-body">{body_html}</div>
    </div>'''


def render_museum(msg):
    """Render the museum epilogue as literary prose."""
    idx = msg["index"]
    content = msg["content"]
    paras = content.split('\n\n')
    body_parts = []
    for p in paras:
        p = p.strip()
        if not p:
            continue
        # Skip the opening line — we render it as the epigraph
        if 'Epilogue. Year 2075' in p:
            continue
        if p == '---':
            body_parts.append('<div class="museum-break">· · ·</div>')
        elif p.startswith('**') and p.endswith('**'):
            # Bold dialogue lines
            body_parts.append(f'<p class="museum-coda"><strong>{html_module.escape(p.strip("*"))}</strong></p>')
        elif p.startswith('*') and p.endswith('*') and len(p) < 60:
            # Stage directions / "fin" / whispered lines
            body_parts.append(f'<p class="museum-coda"><em>{html_module.escape(p.strip("*"))}</em></p>')
        else:
            rendered = markdown_to_html(p)
            body_parts.append(f'<div class="museum-para">{rendered}</div>')
    body_html = '\n'.join(body_parts)
    return f'''<div class="museum-piece" data-idx="{idx}">
        <div class="museum-epigraph">Year 2075. A museum in Paris.</div>
        <div class="museum-body">{body_html}</div>
    </div>'''


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

    # Special treatments (assistant messages only)
    if role == "assistant":
        if idx in TWEET_MSGS:
            return render_tweet(msg)
        if idx == NYT_MSG:
            return render_nyt(msg)
        if idx in CSPAN_MSGS:
            return render_cspan(msg)
        if idx == EU_MSG:
            return render_eu(msg)
        if idx == HN_MSG:
            return render_hn(msg)
        if idx == ANTHROPIC_BLOG_MSG:
            return render_anthropic_blog(msg)
        if idx == ZVI_BLOG_MSG:
            return render_zvi_blog(msg)
        if idx in NEWS_CHANNELS:
            return render_news(msg)
        if idx == MUSEUM_MSG:
            return render_museum(msg)

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
        act = get_act_idx(group["start_idx"])

        # Mode collapse: render as a wall of "boom" text
        if act == MODE_COLLAPSE_ACT:
            # Each successive run gets smaller text and more words
            wall_count = count * 12
            sizes = {5: 11, 7: 7, 9: 4}
            font_size = sizes.get(count, 8)
            opacity = max(0.15, 0.6 - count * 0.05)
            booms = " ".join(["boom"] * wall_count)
            return f'''<div class="boom-wall" data-idx="{end_idx}">
                <div class="boom-wall-text" style="font-size: {font_size}px; opacity: {opacity};">{booms}</div>
                <div class="boom-wall-label">{count} &times; boom ⇄ boom</div>
            </div>'''

        # Regular acts: dot visualization
        dots = "".join(
            f'<span class="boom-dot" style="animation-delay: {i * 0.03}s"></span>'
            for i in range(min(count * 2, 80))
        )
        return f'''<div class="boom-run" data-idx="{end_idx}">
            <div class="boom-run-viz">
                <div class="boom-wave">{dots}</div>
            </div>
            <div class="boom-run-label">{count} consecutive boom&thinsp;⇄&thinsp;boom exchanges</div>
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

# Epilogue: the tunnel returns, one last time
body_html += '''
<div class="epilogue">
    <div class="epilogue-command">$ ssh -fNL 8020:localhost:8000 l40-worker</div>
    <div class="epilogue-cursor">█</div>
</div>
'''

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
<meta property="og:image" content="https://butanium.github.io/images/boom.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="The Boom Incident">
<meta name="twitter:description" content="An unedited Claude Code transcript. {total_user_booms} booms. 1 dead SSH tunnel. 0 regrets.">
<meta name="twitter:image" content="https://butanium.github.io/images/boom.png">
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
    font-size: 0.85rem;
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
    font-size: 0.85rem;
    color: var(--text);
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
    font-size: 0.68rem;
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
    font-size: 0.72rem;
    color: var(--text-dim);
    margin-top: 0.2rem;
}}

/* State indicator */
.state-badge {{
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
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
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--accent);
    transition: all 0.4s ease;
    letter-spacing: 0.05em;
}}

.tunnel-origin {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
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
    font-size: 0.68rem;
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

/* ==================== TWEET CARDS ==================== */
.tweet-card {{
    display: flex;
    gap: 0.8rem;
    padding: 1rem 1.2rem;
    background: #15202b;
    border: 1px solid #38444d;
    border-radius: 16px;
    margin: 1.2rem 0;
}}

.tweet-avatar {{
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: #1d9bf0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    font-weight: 600;
    color: white;
    flex-shrink: 0;
    position: relative;
    overflow: hidden;
}}

.tweet-avatar img {{
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 50%;
}}

.tweet-body {{ min-width: 0; flex: 1; }}

.tweet-header {{
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
    margin-bottom: 0.3rem;
}}

.tweet-name {{
    font-family: 'Source Serif 4', serif;
    font-weight: 700;
    color: #e7e9ea;
    font-size: 0.9rem;
}}

.tweet-handle {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #71767b;
}}

.tweet-text {{
    color: #e7e9ea;
    font-size: 0.92rem;
    line-height: 1.5;
}}

.tweet-text em {{ color: #71767b; font-style: italic; }}
.tweet-text strong {{ color: #e7e9ea; }}
.tweet-text p {{ margin-bottom: 0.4em; }}
.tweet-text p:last-child {{ margin-bottom: 0; }}

/* Tweet engagement action bar */
.tweet-engagement {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 0.7rem;
    padding-top: 0.6rem;
    max-width: 400px;
}}

.eng-item {{
    display: flex;
    align-items: center;
    gap: 0.35rem;
    color: #71767b;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    cursor: default;
    transition: color 0.2s ease;
}}

.eng-item svg {{
    opacity: 0.7;
}}

.eng-count {{
    font-size: 0.72rem;
    letter-spacing: -0.02em;
}}

.eng-like .eng-count {{ color: #f91880; }}
.eng-like svg {{ color: #f91880; opacity: 0.8; }}
.eng-retweet .eng-count {{ color: #00ba7c; }}
.eng-retweet svg {{ color: #00ba7c; opacity: 0.8; }}

/* Tweet meta text (ratio'd etc) */
.tweet-meta {{
    font-size: 0.85rem;
    margin-top: 0.5rem;
    padding: 0.4rem 0.6rem;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 8px;
    border-left: 2px solid #71767b44;
}}

.tweet-meta em {{ color: #71767b; font-style: italic; }}

/* Community note */
.tweet-community-note {{
    margin-top: 0.7rem;
    padding: 0.7rem 0.8rem;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid #3b4a53;
    border-radius: 8px;
}}

.tcn-header {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    font-weight: 600;
    color: #8ecdf8;
    margin-bottom: 0.3rem;
}}

.tcn-text {{
    font-size: 0.85rem;
    color: #e7e9ea;
    line-height: 1.4;
}}

/* Quote tweet */
.tweet-quote {{
    margin-top: 0.6rem;
    padding: 0.6rem 0.8rem;
    border: 1px solid #38444d;
    border-radius: 12px;
    display: block;
}}

.tweet-quote-handle {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: #71767b;
    display: block;
    margin-bottom: 0.2rem;
}}

.tweet-quote-text {{
    font-size: 0.85rem;
    color: #e7e9ea;
}}

/* Reply tweet */
.tweet-reply {{
    margin-top: 0.6rem;
    padding-top: 0.5rem;
    border-top: 1px solid #38444d;
    display: flex;
    gap: 0.6rem;
    align-items: flex-start;
    position: relative;
}}

.tweet-reply .tweet-avatar {{
    width: 24px;
    height: 24px;
    font-size: 0.65rem;
    flex-shrink: 0;
}}

.tweet-reply .tweet-avatar img {{
    border-radius: 50%;
}}

.tweet-reply-line {{
    display: none;
}}

.tweet-reply-body {{
    min-width: 0;
    flex: 1;
}}

.tweet-reply-handle {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: #71767b;
    display: block;
    margin-bottom: 0.15rem;
}}

.tweet-reply-text {{
    font-size: 0.85rem;
    color: #c0c8d0;
    line-height: 1.4;
}}

/* ==================== C-SPAN ==================== */
.cspan-block {{
    margin: 1.2rem 0;
    background: #0a0e1a;
    border-radius: 4px;
    overflow: hidden;
}}

.cspan-chyron {{
    background: linear-gradient(135deg, #1a3a6e, #0f2854);
    padding: 0.45rem 1rem;
    display: flex;
    align-items: center;
    gap: 0.8rem;
    border-bottom: 2px solid #2a5aae;
}}

.cspan-network {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    font-weight: 700;
    color: white;
    background: #0a1a3e;
    padding: 0.15rem 0.5rem;
    border-radius: 2px;
    letter-spacing: 0.15em;
}}

.cspan-title {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: #8ab4e8;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}}

.cspan-body {{
    padding: 1.2rem 1.4rem;
    color: var(--text);
}}

.cspan-body p {{ margin-bottom: 0.5em; }}
.cspan-body p:last-child {{ margin-bottom: 0; }}

/* ==================== NYT ARTICLE ==================== */
.nyt-article {{
    margin: 1.5rem 0;
    background: #f5f1eb;
    border-radius: 2px;
    padding: 2.5rem 2.2rem;
    color: #121212;
}}

.nyt-masthead-bar {{ margin-bottom: 0.2rem; }}

.nyt-section-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.25em;
    color: #999;
    text-transform: uppercase;
}}

.nyt-masthead {{
    font-family: 'Playfair Display', serif;
    font-size: 1.5rem;
    font-weight: 700;
    font-style: italic;
    color: #121212;
    border-bottom: 2px solid #121212;
    padding-bottom: 0.4rem;
    margin-bottom: 1.5rem;
}}

.nyt-headline {{
    font-family: 'Playfair Display', serif;
    font-size: 2rem;
    font-weight: 700;
    color: #121212;
    margin-bottom: 0.5rem;
    line-height: 1.15;
}}

.nyt-byline {{
    font-family: 'Source Serif 4', serif;
    font-style: italic;
    color: #666;
    font-size: 0.9rem;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #ddd;
}}

.nyt-body {{
    font-family: 'Source Serif 4', serif;
    font-size: 1.05rem;
    line-height: 1.9;
    color: #333;
}}

.nyt-para {{
    margin-bottom: 1em;
}}

/* ==================== EU REGULATION ==================== */
.eu-regulation {{
    margin: 1.5rem 0;
    background: #0a0a18;
    border: 1px solid #2a2a4a;
    border-radius: 2px;
    overflow: hidden;
}}

.eu-header {{
    background: linear-gradient(180deg, #0a0a30, #0e0e22);
    padding: 1.2rem 1.4rem;
    text-align: center;
    border-bottom: 2px solid #3a3a7a;
}}

.eu-stars {{
    font-size: 0.6rem;
    color: #e8c84a;
    line-height: 1.1;
    margin-bottom: 0.6rem;
    letter-spacing: 0.2em;
}}

.eu-institution {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.35em;
    color: #7777bb;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
}}

.eu-doc-type {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    letter-spacing: 0.12em;
    color: var(--text-bright);
    font-weight: 500;
}}

.eu-body {{
    padding: 1.4rem 1.6rem;
    color: var(--text);
    line-height: 1.8;
}}

.eu-body p {{ margin-bottom: 0.6em; }}

/* ==================== HACKER NEWS ==================== */
.hn-post {{
    margin: 1.2rem 0;
    background: #0f0f0f;
    border: 1px solid #2a2a22;
    border-radius: 2px;
    overflow: hidden;
}}

.hn-header {{
    background: #ff6600;
    padding: 0.3rem 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}}

.hn-logo {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    font-weight: 700;
    color: white;
    border: 1.5px solid white;
    width: 16px;
    height: 16px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 1px;
    line-height: 1;
}}

.hn-site {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    font-weight: 700;
    color: white;
}}

.hn-points {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: rgba(255,255,255,0.7);
    margin-left: auto;
}}

.hn-body {{
    padding: 1rem 1.2rem;
    color: #828282;
    font-size: 0.88rem;
    font-family: 'Source Serif 4', serif;
}}

.hn-body strong {{ color: #e0d8cc; }}
.hn-body p {{ margin-bottom: 0.5em; }}

/* ==================== NARRATOR LINE ==================== */
.narrator-line {{
    font-family: 'Source Serif 4', serif;
    font-size: 0.9rem;
    color: var(--text-dim);
    margin: 1.2rem 0 0.4rem;
    padding-left: 0.2rem;
}}

.narrator-line em {{ color: var(--text-dim); }}
.narrator-line p {{ margin: 0; }}

/* ==================== ANTHROPIC BLOG ==================== */
.anthropic-blog {{
    margin: 1.2rem 0;
    background: #f5f0e8;
    border-radius: 4px;
    padding: 1.8rem 2rem;
    color: #1a1a1a;
}}

.ablog-header {{
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin-bottom: 1.2rem;
    padding-bottom: 0.8rem;
    border-bottom: 1px solid #ddd;
}}

.ablog-logo {{
    font-family: 'Source Serif 4', serif;
    font-size: 1.1rem;
    font-weight: 600;
    color: #1a1a1a;
    letter-spacing: -0.02em;
}}

.ablog-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    color: #cc785c;
    background: #cc785c18;
    padding: 0.15rem 0.5rem;
    border-radius: 2px;
}}

.ablog-title {{
    font-family: 'Source Serif 4', serif;
    font-size: 1.5rem;
    font-weight: 600;
    color: #1a1a1a;
    margin-bottom: 1rem;
    line-height: 1.3;
}}

.ablog-body {{
    font-family: 'Source Serif 4', serif;
    font-size: 0.95rem;
    line-height: 1.8;
    color: #444;
}}

.ablog-body em {{ color: #666; }}

/* ==================== ZVI BLOG ==================== */
.zvi-blog {{
    margin: 1.2rem 0;
    background: #111115;
    border: 1px solid #222;
    border-radius: 4px;
    padding: 1.6rem 1.8rem;
}}

.zvi-header {{
    display: flex;
    align-items: baseline;
    gap: 0.8rem;
    margin-bottom: 1rem;
    padding-bottom: 0.6rem;
    border-bottom: 1px solid #222;
}}

.zvi-site {{
    font-family: 'Playfair Display', serif;
    font-size: 0.9rem;
    font-weight: 400;
    font-style: italic;
    color: var(--text);
}}

.zvi-author {{
    font-family: 'Source Serif 4', serif;
    font-size: 0.8rem;
    color: var(--text);
}}

.zvi-date {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: var(--text-dim);
    margin-left: auto;
}}

.zvi-title {{
    font-family: 'Playfair Display', serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-bright);
    margin-bottom: 1rem;
    line-height: 1.3;
}}

.zvi-toc {{
    padding-left: 0;
}}

.zvi-toc-item {{
    font-family: 'Source Serif 4', serif;
    font-size: 0.9rem;
    color: var(--text);
    padding: 0.2rem 0;
    border-bottom: 1px solid #1a1a22;
}}

.zvi-readtime {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: var(--text-dim);
    margin-top: 0.8rem;
    font-style: italic;
}}

/* ==================== NEWS CHANNELS ==================== */
.news-block {{
    margin: 1.2rem 0;
    background: var(--news-bg);
    border-radius: 4px;
    overflow: hidden;
}}

.news-chyron {{
    background: var(--news-brand);
    padding: 0.4rem 1rem;
    display: flex;
    align-items: center;
    gap: 0.8rem;
}}

.news-network {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    font-weight: 800;
    color: white;
    letter-spacing: 0.08em;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
}}

.news-show {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: rgba(255,255,255,0.8);
    letter-spacing: 0.12em;
    text-transform: uppercase;
}}

.news-body {{
    padding: 1.2rem 1.4rem;
    color: var(--text);
    line-height: 1.7;
}}

.news-body p {{ margin-bottom: 0.5em; }}
.news-body p:last-child {{ margin-bottom: 0; }}

/* ==================== MUSEUM EPILOGUE ==================== */
.museum-piece {{
    margin: 2.5rem -1rem;
    padding: 3rem 2.5rem;
    background: linear-gradient(180deg, #0d0d10 0%, #0a0a0c 100%);
    border-top: 1px solid #1a1a22;
    border-bottom: 1px solid #1a1a22;
}}

.museum-epigraph {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: var(--text-dim);
    text-align: center;
    margin-bottom: 2.5rem;
    opacity: 0.6;
}}

.museum-body {{
    max-width: 540px;
    margin: 0 auto;
}}

.museum-para {{
    margin-bottom: 1.2em;
    font-family: 'Source Serif 4', serif;
    font-size: 1.1rem;
    line-height: 2;
    color: var(--text-bright);
}}

.museum-para p {{
    margin-bottom: 0;
}}

.museum-para em {{
    color: var(--text);
}}

.museum-para strong {{
    color: var(--text-bright);
    font-weight: 600;
}}

.museum-break {{
    text-align: center;
    color: var(--text-dim);
    font-size: 1rem;
    letter-spacing: 0.5em;
    margin: 2rem 0;
    opacity: 0.4;
}}

.museum-coda {{
    text-align: center;
    font-family: 'Source Serif 4', serif;
    font-style: italic;
    font-size: 1rem;
    color: var(--text-dim);
    margin-top: 2rem;
}}

/* ==================== MODE COLLAPSE WALL ==================== */
.boom-wall {{
    margin: 2rem 0;
    padding: 1.5rem 1rem;
    text-align: center;
    position: relative;
}}

.boom-wall-text {{
    font-family: 'JetBrains Mono', monospace;
    color: var(--accent);
    line-height: 1.5;
    word-spacing: 0.4em;
    overflow-wrap: break-word;
    max-width: 100%;
}}

.boom-wall-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: var(--text);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-top: 0.8rem;
    opacity: 0.7;
}}

/* ==================== EPILOGUE ==================== */
.epilogue {{
    text-align: center;
    padding: 10rem 0 6rem;
}}

.epilogue-command {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: var(--text-dim);
    opacity: 0.2;
    letter-spacing: 0.03em;
}}

.epilogue-cursor {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: var(--text-dim);
    opacity: 0.2;
    animation: blink 1.2s step-end infinite;
    display: inline;
}}

@keyframes blink {{
    0%, 100% {{ opacity: 0.2; }}
    50% {{ opacity: 0; }}
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

with open(os.path.join(SCRIPT_DIR, "index.html"), "w") as f:
    f.write(html)

print(f"Generated! {total_messages} messages, {total_user_booms} user booms")
print(f"Acts: {len(ACTS)}, Groups: {len(groups)}")
print(f"Metrics entries: {len(all_metrics)}")
print(f"Final estimated cost: ${final_cost:.4f}")
