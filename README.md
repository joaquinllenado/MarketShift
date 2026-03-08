# MarketShift

**Competitive intelligence from a single product URL.** Paste a competitor’s or your own product URL; MarketShift discovers similar companies, gathers news (launches, funding, partnerships, market moves), classifies signals, and surfaces market opportunities, competitive risks, and suggested next steps. Optional: get a short spoken briefing (audio summary) of the results.

---

## What it does

- **One input:** A product or company URL (e.g. Notion, Coda, your own landing page).
- **Pipeline:** Scrapes the URL, finds the top 5 relevant competitors (Exa + LLM), then for each competitor and the market runs news, web, and Product Hunt searches.
- **Structured output:** An LLM classifies items into **product announcements**, **funding**, **partnerships**, and **market signals**, then synthesises **market opportunities**, **competitive risks**, and **action steps**.
- **Dashboard:** A single view of “what changed” and “what to do” (product announcements, funding, partnerships, market signals, opportunities, risks, next steps).
- **Voice brief (optional):** Generate an MP3 summary (30–60 seconds) of the analysis via text-to-speech.

---

## Tech stack

| Layer   | Stack |
|--------|--------|
| Frontend | React 19, Vite, Tailwind CSS v4 (JavaScript) |
| Backend  | Python, FastAPI, Prefect (workflow orchestration) |
| Search   | [Exa](https://exa.ai/) (company/news search, scraping) |
| LLM      | DeepSeek (V3/R1) via GMI Cloud — intake, analysis, narrative summary |
| TTS      | ElevenLabs via GMI Cloud (voice summary) |

---

## Quick start

### 1. Backend

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

Set environment variables (see [Environment](#environment)), then:

```bash
uvicorn main:app --reload
```

API: **http://localhost:8000**

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: **http://localhost:5173**

Frontend proxies `/api/*` to the backend (see `frontend/vite.config.js`).

### 3. Run the pipeline

- **POST** a product URL to run the full pipeline:
  ```bash
  curl -X POST http://localhost:8000/pipeline \
    -H "Content-Type: application/json" \
    -d '{"url": "https://www.notion.so"}'
  ```
- **GET** cached results: `GET http://localhost:8000/pipeline/results`
- **POST** voice summary (uses latest pipeline results): `POST http://localhost:8000/pipeline/voice-summary` → returns MP3.

---

## Environment

Create a `.env` in `backend/` with:

| Variable     | Purpose |
|-------------|---------|
| `EXA_API_KEY` | Exa search and content API |
| `GMI_API_KEY` | GMI Cloud (DeepSeek LLM + ElevenLabs TTS) |

---

## Project layout

```
MarketShift/
├── frontend/                 # React + Vite + Tailwind
│   ├── src/
│   │   ├── App.jsx
│   │   ├── LandingPage.jsx   # Hero input → AgentTimeline → Dashboard
│   │   ├── AgentTimeline.jsx # Research progress UI
│   │   └── MarketShiftDashboard.jsx  # Signals, sentiment, competitors, actions
│   └── vite.config.js        # API proxy /api → :8000
├── backend/
│   ├── main.py               # FastAPI app, /research, /pipeline, /pipeline/voice-summary
│   ├── agents/
│   │   ├── orchestrator.py   # Pipeline: intake → sub_1 → sub_2 → analysis → sub_3
│   │   ├── intake_agent.py   # URL → scrape → competitor discovery (Exa + LLM)
│   │   ├── sub_agent_1.py    # Per-competitor & market news/web/Product Hunt
│   │   ├── sub_agent_2.py    # Aggregate, dedupe, persist to data/results.json
│   │   ├── analysis_agent.py # LLM classification + opportunities/risks/actions
│   │   ├── sub_agent_3.py    # Shape output for frontend
│   │   └── voice_summary.py  # Pipeline output → narrative → TTS → MP3
│   └── data/                 # results.json, voice_summary.mp3 (gitignored)
└── AGENTS.md                 # Developer/agent notes (commands, architecture)
```

---

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/hello` | Health check |
| POST | `/research` | Company search and/or URL scraping (query + optional `urls[]`) |
| POST | `/pipeline` | Full pipeline: single product `url` → structured intelligence |
| GET | `/pipeline/results` | Latest pipeline output (from `data/results.json`) |
| POST | `/pipeline/voice-summary` | Generate MP3 briefing from latest pipeline results |

---

## Pipeline data flow

1. **Intake** — Scrape product URL (Exa), find similar companies (Exa), LLM picks top 5 competitors and market context.
2. **Sub-agent 1** — For each competitor and the market: news, web, Product Hunt searches (Exa).
3. **Sub-agent 2** — Deduplicate by URL, tag source, append run to `data/results.json`.
4. **Analysis** — LLM classifies items into product announcements, funding, partnerships, market signals; synthesises opportunities, risks, action steps.
5. **Sub-agent 3** — Format for frontend (same structure as `PipelineResponse`).

Result includes: `product_announcements`, `funding`, `partnerships`, `market_signals`, `market_opportunities`, `competitive_risks`, `action_steps`, plus `query`, `persisted_at`, and optional product/competitor metadata.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
