from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings, validate_startup_config
from app.routers import projects, pages, keywords, crawl, technical, internal_links, ai, backlinks, rankings, datasources, reports, imports, competitors, integrations, opportunities, alerts

from app.config.database import engine, Base

from app.config.migration import run_schema_migrations

# Import all models to ensure they are registered with Base
from app.models import project, dataset, page, keyword, keyword_group, crawl_session, competitor, external_connection, audit_issue, action_opportunity

# Run startup configuration validation & schema migrations
validate_startup_config(strict=False)
run_schema_migrations(engine)
Base.metadata.create_all(bind=engine)

from fastapi.responses import JSONResponse
import traceback

app = FastAPI(title="SEO Intelligence API")

# Configure CORS dynamically from settings (no wildcards)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"[GLOBAL EXCEPTION HANDLER] Unhandled error on {request.url.path}: {exc}", flush=True)
    traceback.print_exc()
    origin = request.headers.get("origin") or "http://127.0.0.1:8030"
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    )


# Register routers
app.include_router(integrations.router, prefix="/api/integrations", tags=["integrations"])
app.include_router(reports.router, prefix="/api/projects/{project_id}", tags=["reports"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(crawl.router, prefix="/api/projects", tags=["crawl"])
app.include_router(opportunities.router, prefix="/api/projects/{project_id}/opportunities", tags=["opportunities"])

app.include_router(pages.router, prefix="/api/projects/{project_id}/pages", tags=["pages"])
app.include_router(keywords.router, prefix="/api/projects/{project_id}/keywords", tags=["keywords"])
app.include_router(technical.router, prefix="/api/projects/{project_id}/technical", tags=["technical"])
app.include_router(internal_links.router, prefix="/api/projects/{project_id}/internal-links", tags=["internal-links"])
app.include_router(backlinks.router, prefix="/api/projects/{project_id}/backlinks", tags=["backlinks"])
app.include_router(rankings.router, prefix="/api/projects/{project_id}/rankings", tags=["rankings"])
app.include_router(datasources.router, prefix="/api/projects/{project_id}/datasources", tags=["datasources"])
app.include_router(ai.router, prefix="/api/projects", tags=["ai"])
app.include_router(imports.router, prefix="/api/projects/{project_id}/imports", tags=["imports"])
app.include_router(competitors.router, prefix="/api/projects/{project_id}/competitors", tags=["competitors"])
app.include_router(alerts.router, prefix="/api/projects/{project_id}/alerts", tags=["alerts"])


@app.get("/api/health", tags=["System"])
def health_check():
    return {"status": "ok", "message": "Clean open-source architecture active"}
