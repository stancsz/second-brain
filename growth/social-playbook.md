# Social & Viral Playbook — second-brain

The motion: **show the table-flip honestly and let developers who resent paying rent for
their own memory share it.** No engagement bait. Our virality is *indignation +
relief* — "wait, I'm paying $249/mo to rent MY memory? and this is one file I own?"

## The narrative hook (one sentence, repeated everywhere)

> **You're renting your agent's memory. second-brain lets you own it — one file, your git, $0.**

Variants by audience:
- **Builders:** "Mem0's graph is behind a $249/mo wall. This is graph + bi-temporal +
  affect, local, zero-dep, MIT."
- **Privacy/compliance:** "Your memory never leaves your machine. Encrypt the private
  parts. No Neo4j, no cloud, no DPA."
- **PKM crowd:** "Your notes, but first-class to agents — markdown in your git, not a
  vendor's database."
- **zh (掀桌子):** "别再租用你的 AI 记忆了 — 一个文件，存进你自己的 git，$0，还自带情感与时间维度记忆。"

## The shareable artifact (the thing that actually spreads)

A single **side-by-side image / gist**: the comparison table from the landing page
("$249/mo tier → $0 local file", "Neo4j to self-host → one SQLite file", "privacy drift
→ you own the files"). One screenshot, debunk-proof because every claim is sourced. This
is the unit that gets reposted. Pair it with a 20-second asciinema of `brain add` →
`brain recall --as-of` (point-in-time recall is the "whoa" demo nobody expects from a
local file).

## Launch sequence (stage; publishing is human-gated)

1. **Polish first (gate).** Don't launch on a half-wired cockpit — close the high-sev
   review issues (#7 secret hygiene, #9 `.gitattributes`, #8 sync/encryption seam) and
   ideally ship semantic search (R16) so the top HN comment can't be "no vector search."
2. **Show HN: "second-brain – own your AI agent's memory as files in your git (MIT)."**
   Lead with the thesis, the comparison artifact, the 30-sec quickstart. Be in the
   thread to answer the "why not just Mem0 self-hosted?" question (answer: zero-dep,
   one file, psych layer, no Neo4j).
3. **r/LocalLLaMA + r/selfhosted** — the "I built the DIY path" audience is literally
   described in the research; meet them with "you don't have to build it."
4. **dev.to / X thread** — the comparison artifact + the point-in-time recall demo.
5. **zh channels (即刻 / 小红书 / V2EX)** — the 掀桌子 framing lands hard in zh dev culture;
   reuse `README.zh.md`.
6. **Get into the comparison set** — the category is navigated via "Mem0 vs Zep vs …"
   articles. Reach out to those authors / open PRs to comparison repos so second-brain
   appears as the "own-it / local-first" row.

## Metrics (lightweight, honest)

- Leading: GitHub stars/day, Show HN rank + comment sentiment, landing → repo CTR.
- Lagging: skill installs, `sync` setups (proxy: forks with a remote), inbound issues
  asking for features (demand signal → feed `.mochu/gaps.md`).
- **Kill-switch:** if the top comment debunks a claim, pull the claim and fix the
  product before re-launching. Credibility is the whole moat for a dev tool.

## Anti-patterns (never do)

- No fabricated/borrowed benchmarks (the category is full of disputed numbers — our
  edge is that we don't play). 
- No "AI memory revolution" hype copy; the audience is allergic to it. Concrete,
  sourced, slightly indignant.
- No bashing competitors' people — critique the *rental model*, not the engineers.
- Don't launch louder than the product is ready (see step 1).
