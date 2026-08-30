# SEO Intelligence & Full Website Health Platform

A high-performance, local-first SEO Intelligence & Website Audit Platform. Built with a FastAPI backend and a lightweight Vanilla JavaScript SPA frontend, it provides deep crawler analysis, technical SEO auditing, AI-powered recommendations, business context integration, and client-ready multi-format reporting without costly SaaS subscriptions or cloud data lock-in.

---

## 🌟 Key Capabilities & Features

### 1. High-Speed Asynchronous Website Crawler
- Crawls target domains asynchronously with configurable depth and concurrency limits.
- Extracts HTML title tags, meta descriptions, robots directives, canonical URLs, heading hierarchy (`<h1>`-`<h6>`), Open Graph tags, image `alt` attributes, and page word counts.
- Maps internal link graphs and outgoing external links.
- Stores immutable, timestamped JSON crawl snapshots on disk for historical audits.

### 2. 14-Point Technical SEO Audit Engine
- Inspects HTTP status codes (broken 404s, 500s, 301/302 redirects), missing/short/long title tags, missing meta descriptions, thin content (<300 words), heading hierarchy gaps, duplicate or missing canonical tags, and search engine indexability.
- Calculates an objective **0–100 Website Health Score** with weighted severity penalties (Critical, High, Warning, Info).

### 3. Business Context Intelligence Layer
- Allows configuring real business parameters per project: **Business Name**, **Industry / Niche**, **Core Services**, **Target Service Areas / Locations**, and **Target Country / Language**.
- Automatically infers topic themes from crawled page titles/H1s when unconfigured, without fabricating unverified business services.

### 4. Grounded AI Intelligence Layer
- Integrates with user-configured LLM providers (**Groq**, **Google Gemini**, **Anthropic Claude**, **OpenAI**, or local **Ollama**).
- Processes audit findings in batched prompts to generate tailored, evidence-grounded solutions, future roadmap steps, executive summaries, and score explanations.
- **Strict Data Grounding:** AI never invents SEO metrics or ranking positions. Each problem includes transparent `ai_generated: true/false` indicators and gracefully falls back to deterministic rule templates when offline.

### 5. Universal Multi-Format Master Reporting Pipeline
Every export derives from a single authoritative source of truth: `MasterReportBuilder.build_master_report()`.
- **PDF Export (`report.pdf`):** Multi-page executive health report built with ReportLab, featuring styled tables, severity badges, and AI recommendations.
- **XLSX Export (`export.xlsx`):** Multi-sheet workbook formatted like top agency audit trackers, with a front **📊 Dashboard** (KPI cards, AI overview, severity breakdown) + 10 dedicated category audit sheets (`Technical SEO`, `On-Page SEO`, `Local SEO`, `Content & Links`, `Keywords`, `AEO`, `GEO`, `AI Citations`, `Opportunities & Roadmap`, `Affected Pages`, `Data Limitations`).
- **PPTX Export (`export.pptx`):** Executive slide deck for client and stakeholder presentations.
- **CSV Summaries (`summary.csv`, etc.):** Human-readable, structured data exports.
- **Complete ZIP Data Package (`complete-export.zip`):** Self-contained archive with Master PDF, XLSX, PPTX, all CSV slices, and a data definitions `README.txt`.

### 6. Scoped Page-Specific Downloads
- Export buttons on individual views (e.g. Pages, Keywords, Technical Issues, Opportunities) download scoped datasets specifically filtered to that section, preventing data confusion.

### 7. External OAuth 2.0 Integrations & Encryption
- Connects directly to Google Search Console, Google Analytics 4, Google Ads / Keyword Planner, Google Calendar, Gmail, and Meta.
- Encrypts API keys and OAuth tokens at rest using **AES-256 Fernet** encryption.

---

## 🏛️ System Architecture

```
                       ┌──────────────────────────────┐
                       │       User Web Browser       │
                       │   (Vanilla JS SPA :8030)     │
                       └──────────────┬───────────────┘
                                      │ REST API / JSON
                       ┌──────────────▼───────────────┐
                       │     FastAPI Backend :8020    │
                       └──────────────┬───────────────┘
                                      │
           ┌──────────────────────────┼──────────────────────────┐
           │                          │                          │
┌──────────▼──────────┐    ┌──────────▼──────────┐    ┌──────────▼──────────┐
│   Async Crawler     │    │  SQLAlchemy/SQLite  │    │  LLM Provider API   │
│ (HTML/Meta/Links)   │    │ (Projects/Metadata) │    │ (Groq/Gemini/Local) │
└──────────┬──────────┘    └──────────┬──────────┘    └──────────┬──────────┘
           │                          │                          │
           └──────────────────────────┼──────────────────────────┘
                                      │
                       ┌──────────────▼───────────────┐
                       │     MasterReportBuilder      │
                       │  (Single Source of Truth)    │
                       └──────────────┬───────────────┘
                                      │
         ┌────────────┬───────────────┼───────────────┬────────────┐
         │            │               │               │            │
    ┌────▼───┐   ┌────▼───┐      ┌────▼───┐      ┌────▼───┐   ┌────▼───┐
    │  PDF   │   │  XLSX  │      │  PPTX  │      │  CSV   │   │  ZIP   │
    │ Report │   │ (Multi-│      │ Slides │      │ Slices │   │Archive │
    │        │   │ Sheet) │      │        │      │        │   │        │
    └────────┘   └────────┘      └────────┘      └────────┘   └────────┘
```

---

## 🚀 Quickstart & Development

### 1. Prerequisites
- Python 3.10+ (Python 3.12 / 3.14 fully supported)

### 2. Installation
Clone the repository and install required Python packages:

```bash
git clone <repo-url>
cd "seo new"
pip install -r backend/requirements.txt
```

### 3. Start Development Environment
Run the unified one-click launcher from the project root:

```bash
python start_dev.py
```

This will automatically:
1. Start the **FastAPI backend** on `http://127.0.0.1:8020`
2. Start the **SPA frontend server** on `http://localhost:8030`
3. Verify backend and frontend health checks
4. Automatically open `http://localhost:8030` in your default browser

---

## ⚙️ Configuration

### Business Context Configuration
In the Web UI, navigate to **Settings > Workspace & Team** to configure your project's business context:
- **Industry / Business Niche** (e.g. `Electrical Contracting & Solar Installation`)
- **Target Service Areas / Locations** (e.g. `Sydney, NSW, Parramatta, Penrith`)
- **Core Services / Topic Focus** (e.g. `Commercial Electrician, Solar Panel Installation, EV Charger Setup`)

### AI Provider Keys
In **Settings > AI Settings**, select your preferred provider and add your API key:
- **Groq API Key** (`gsk_...`)
- **Google Gemini API Key** (`AIzaSy...`)
- **OpenAI API Key** (`sk-...`)
- **Anthropic Claude API Key** (`sk-ant-...`)
- **Ollama Local Endpoint** (e.g. `http://localhost:11434`)

---

## 🧪 Testing

Run the automated regression test suite to verify export consistency and reporting integrity:

```bash
cd backend
python -m pytest tests/test_master_export_consistency.py tests/test_universal_master_reporting.py tests/test_page_specific_exports.py tests/test_full_master_health_report.py -v
```

All 19 tests assert:
- `MasterReportBuilder` generates complete, unified report dictionaries for any project.
- PDF, XLSX, PPTX, CSV, and ZIP exports generate valid, non-empty files without crashing.
- Multi-project isolation is maintained without cross-website data leakage.
- Page-specific export endpoints remain scoped strictly to their respective views.

---

## 📄 License
MIT License. Free for personal, commercial, and agency use.
