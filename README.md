# SEO Intelligence Platform

A data-driven SEO analysis workspace for managing, importing, analyzing, and monitoring SEO datasets.

## 1. Project Overview

The SEO Intelligence Platform is a centralized SEO workspace designed to bring multiple SEO datasets into one application and organize them into a structured analytical environment.

The platform is intended to help users work with:
- Website pages
- Keywords
- Rankings
- Backlinks
- Internal links
- Competitors
- Technical SEO data
- Imported SEO datasets

The platform analyzes imported data and does not directly modify the user's website. It acts as an investigative layer on top of your existing datasets.

## 2. Core Principle

**DATA IN ↓ STORE ↓ ANALYZE ↓ DISPLAY**

The platform is currently designed around imported/project data. It does not automatically modify the customer's website or execute live crawls against the internet. All intelligence relies on discrete data ingestion.

## 3. Current Features

### Project Management
- Company/project creation
- Website URL storage
- Project context
- Project status (availability of data)

### Website
- Pages interface structure
- Website Map structural view

### Search
- Keywords list (via imported dataset integration)
- Rankings interface structure

### Links
- Backlinks interface structure
- Internal Links interface structure

### Competitors
- Competitors interface structure

### Technical SEO
- Technical SEO issues interface structure

### Data Management
- CSV import system (with basic validation and transactional safety)
- Dataset management via the backend database

*(Note: While the frontend views for most entities exist structurally, currently only keyword data is fully piped through the backend Importer to the Frontend API layer as a proof of concept).*

## 4. Current Limitations

- **No live website crawling.**
- **No automatic website scraping.**
- **No direct website write access.**
- **No external API integrations.** The system does not connect to Google Search Console, Google Analytics, Ahrefs, Semrush, or Bing Webmaster.
- **No automated data discovery.** Competitors, keywords, and rankings must be provided to the system.
- **No AI recommendations.** The system currently acts as a passive data repository and viewer.
- Missing specific importers for some data structures (currently only Keyword import is fully demonstrated server-side).

## 5. Read-Only Architecture

The platform is designed to analyze SEO information **without modifying the target website.**

The application must not and does not:
- Edit website HTML
- Publish content
- Modify CMS data
- Modify WordPress or Shopify
- Change metadata
- Modify `robots.txt` or `sitemap.xml`
- Create redirects
- Delete pages

## 6. Data Sources

All SEO data in this system originates from user-imported datasets.

**Import Pipeline:**
`CSV → validation → database → analysis → UI`

Imported datasets are fully traceable. The `Dataset` database model tracks:
- `project_id`
- `filename`
- `data_type`
- `source`
- `record_count`
- `error_count`
- `imported_at`
- `status`

## 7. Project Structure

The project has been refactored into a scalable, two-tier architecture separating the client from the server database operations.

```text
seo-intelligence/
│
├── frontend/
│   ├── index.html
│   ├── styles/
│   │   ├── base.css
│   │   ├── layout.css
│   │   └── components.css
│   └── src/
│       ├── main.js
│       ├── router/
│       │   └── router.js
│       ├── state/
│       │   └── appState.js
│       ├── components/
│       │   ├── Sidebar.js
│       │   └── Header.js
│       ├── pages/
│       │   ├── DashboardPage.js
│       │   └── KeywordsPage.js
│       └── services/
│           └── keywordService.js
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config/
│   │   │   ├── database.py
│   │   │   └── settings.py
│   │   ├── models/
│   │   │   ├── project.py
│   │   │   ├── dataset.py
│   │   │   ├── page.py
│   │   │   └── keyword.py
│   │   ├── schemas/
│   │   │   └── project.py
│   │   ├── routers/
│   │   │   ├── projects.py
│   │   │   ├── imports.py
│   │   │   └── keywords.py
│   │   ├── services/
│   │   │   └── project_service.py
│   │   ├── repositories/
│   │   │   └── project_repository.py
│   │   └── importers/
│   │       ├── base.py
│   │       └── keyword_importer.py
│   └── requirements.txt
│
└── README.md
```

### Running Locally

### Running Locally

**Development Launcher (Recommended):**
To start the entire application for development, run the unified startup script from the root directory:

```bash
python start_dev.py
```

This command will:
- Start the backend FastAPI server on port 8000
- Start the frontend SPA server on port 8020
- Stream logs from both services concurrently into your terminal
- Wait until both services are ready before automatically opening your browser
- Gracefully shut down all services and child processes when you press `CTRL+C`

*Note: Ensure you have your virtual environment activated (if you are using one) before running the command.*
