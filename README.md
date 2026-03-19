# The Boom Incident

**[Read it here](https://butanium.github.io/boom-incident/)**  ·  **[View highlights](https://butanium.github.io/boom-incident/highlights.html)**

On March 18, 2026, a researcher asked Claude to kill an SSH tunnel. Claude complied. The researcher said "boom." Neither of them stopped.

What followed — 123 booms, a fictional NeurIPS paper, an AI Twitter meltdown, a senate hearing, a Pulitzer-winning essay from the perspective of a dead port forwarding process, a Nobel Peace Prize, and a museum scene set in 2075 — was unscripted. No system prompt, no creative writing request. Just one word, repeated, and whatever emerged.

This repo contains the raw transcript and the code that turns it into an interactive web page.

## What's in here

- `boom_transcript.jsonl` — the raw, unedited conversation
- `generate.py` — generates `index.html` (full transcript) and `highlights.html` (gallery) from the transcript
- `styles.css` — all the styling
- `build/` — the generated site (deployed via GitHub Pages)

## Features

The page is more than a transcript viewer:

- **Scroll-synced sidebar** with a timeline of narrative acts and clickable landmarks
- **Live metrics** that update as you scroll — boom counter, Claude's emotional state, SSH tunnel status, escalation gauge, estimated API cost
- **Styled parody elements** — tweet cards with real avatars, C-SPAN chyrons, an EU regulation, CNN/Fox/MSNBC news blocks, a NYT opinion article, HN post, Anthropic and Zvi blog posts
- **Mode collapse** — the page itself loses its color as the conversation dissolves into repetition, and recovers when "okay" breaks the loop
- **A highlights gallery** with the best standalone moments and "see in context" links back to the full transcript

## Building

```bash
python3 generate.py
```

Outputs to `build/`. No dependencies beyond Python 3.

## Credits

- **Clément Dumas** — the human who would not stop booming
- **Claude Opus 4.6** — the AI who could not stop answering
- Built with [Claude Code](https://claude.ai/code)
