from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import projects, pages, keywords, crawl, technical, internal_links, ai, backlinks, rankings, datasources, reports, imports, competitors
from app.config.database import engine, Base
from app.config.migration import run_schema_migrations

# Import all models to ensure they are registered with Base
from app.models import project, dataset, page, keyword, crawl_session

# Run idempotent column migrations & create missing database tables
run_schema_migrations(engine)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SEO Intelligence API")

origins = [
    "http://localhost:8030",
    "http://127.0.0.1:8030",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "*"],
)

# Register routers
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(crawl.router, prefix="/api/projects", tags=["crawl"])
app.include_router(pages.router, prefix="/api/projects/{project_id}/pages", tags=["pages"])
app.include_router(keywords.router, prefix="/api/projects/{project_id}/keywords", tags=["keywords"])
app.include_router(technical.router, prefix="/api/projects/{project_id}/technical", tags=["technical"])
app.include_router(internal_links.router, prefix="/api/projects/{project_id}/internal-links", tags=["internal-links"])
app.include_router(backlinks.router, prefix="/api/projects/{project_id}/backlinks", tags=["backlinks"])
app.include_router(rankings.router, prefix="/api/projects/{project_id}/rankings", tags=["rankings"])
app.include_router(datasources.router, prefix="/api/projects/{project_id}/datasources", tags=["datasources"])
app.include_router(reports.router, prefix="/api/projects/{project_id}", tags=["reports"])
app.include_router(ai.router, prefix="/api/projects", tags=["ai"])
app.include_router(imports.router, prefix="/api/projects/{project_id}/imports", tags=["imports"])
app.include_router(competitors.router, prefix="/api/projects/{project_id}/competitors", tags=["competitors"])

@app.get("/api/health", tags=["System"])
def health_check():
    return {"status": "ok", "message": "Clean open-source architecture active"}
