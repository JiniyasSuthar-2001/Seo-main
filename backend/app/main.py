from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import projects, imports, pages, keywords, rankings, backlinks, internal_links, competitors, technical
from app.config.database import engine, Base

# Import all models to ensure they are registered with Base
from app.models import project, dataset, page, keyword

# Create database tables
Base.metadata.create_all(bind=engine)


app = FastAPI(title="SEO Intelligence Platform API")

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For dev only, should use config in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(imports.router, prefix="/api/projects/{project_id}/imports", tags=["Imports"])
app.include_router(pages.router, prefix="/api/projects/{project_id}/pages", tags=["Pages"])
app.include_router(keywords.router, prefix="/api/projects/{project_id}/keywords", tags=["Keywords"])
app.include_router(rankings.router, prefix="/api/projects/{project_id}/rankings", tags=["Rankings"])
app.include_router(backlinks.router, prefix="/api/projects/{project_id}/backlinks", tags=["Backlinks"])
app.include_router(internal_links.router, prefix="/api/projects/{project_id}/internal-links", tags=["Internal Links"])
app.include_router(competitors.router, prefix="/api/projects/{project_id}/competitors", tags=["Competitors"])
app.include_router(technical.router, prefix="/api/projects/{project_id}/technical", tags=["Technical SEO"])

@app.get("/api/health", tags=["System"])
def health_check():
    return {"status": "ok"}
