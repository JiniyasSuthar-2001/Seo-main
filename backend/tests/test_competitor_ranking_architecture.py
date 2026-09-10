import io
import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.project import Project
from app.models.competitor import Competitor
from app.models.keyword import Keyword
from app.models.project_membership import ProjectMembership
from app.models.competitor_ranking import CompetitorRanking
from app.importers.competitor_ranking_importer import CompetitorRankingImporter
from app.services.competitor_service import (
    perform_keyword_gap_analysis,
    store_competitor_ranking,
    bulk_store_competitor_rankings,
)
from app.providers.serp_provider import SERPRankTrackerProvider
from app.config.database import SessionLocal, engine, Base


@pytest.fixture(scope="module", autouse=True)
def init_db():
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_setup(db_session):
    db = db_session
    user_a = User(
        id=str(uuid.uuid4()),
        email=f"user_a_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fakehash",
        platform_role="customer",
    )
    user_b = User(
        id=str(uuid.uuid4()),
        email=f"user_b_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fakehash",
        platform_role="customer",
    )
    db.add_all([user_a, user_b])
    db.commit()

    proj_a = Project(
        id=str(uuid.uuid4()),
        name="Solar Systems Brisbane",
        url="mysolarbrisbane.com.au",
    )
    proj_b = Project(
        id=str(uuid.uuid4()),
        name="Competitor Project B",
        url="otherproject.com.au",
    )
    db.add_all([proj_a, proj_b])
    db.commit()

    mem_a = ProjectMembership(
        id=str(uuid.uuid4()),
        project_id=proj_a.id,
        user_id=user_a.id,
        role="owner",
    )
    mem_b = ProjectMembership(
        id=str(uuid.uuid4()),
        project_id=proj_b.id,
        user_id=user_b.id,
        role="owner",
    )
    db.add_all([mem_a, mem_b])
    db.commit()

    comp_a1 = Competitor(
        id=str(uuid.uuid4()),
        project_id=proj_a.id,
        domain="solarcompetitora.com.au",
        url="https://solarcompetitora.com.au",
        name="Solar Competitor A",
        status="confirmed",
    )
    comp_a2 = Competitor(
        id=str(uuid.uuid4()),
        project_id=proj_a.id,
        domain="solarcompetitorb.com.au",
        url="https://solarcompetitorb.com.au",
        name="Solar Competitor B",
        status="confirmed",
    )
    db.add_all([comp_a1, comp_a2])
    db.commit()

    return {
        "user_a": user_a,
        "user_b": user_b,
        "proj_a": proj_a,
        "proj_b": proj_b,
        "comp_a1": comp_a1,
        "comp_a2": comp_a2,
    }


def test_competitor_ranking_model_and_storage(db_session, test_setup):
    db = db_session
    proj_a = test_setup["proj_a"]
    comp_a1 = test_setup["comp_a1"]

    # Store real competitor ranking
    rec = store_competitor_ranking(
        db=db,
        project_id=proj_a.id,
        competitor_id=comp_a1.id,
        keyword="best solar Brisbane",
        position=9,
        ranking_url="https://solarcompetitora.com.au/best-solar",
        search_engine="google",
        country="Australia",
        location="Brisbane",
        device="desktop",
        source="serp_provider",
    )
    assert rec.id is not None
    assert rec.project_id == proj_a.id
    assert rec.competitor_id == comp_a1.id
    assert rec.position == 9
    assert rec.source == "serp_provider"

    # Query back
    fetched = (
        db.query(CompetitorRanking)
        .filter(
            CompetitorRanking.project_id == proj_a.id,
            CompetitorRanking.keyword == "best solar Brisbane",
        )
        .first()
    )
    assert fetched is not None
    assert fetched.position == 9
    assert fetched.ranking_url == "https://solarcompetitora.com.au/best-solar"


def test_keyword_gap_mathematical_calculation(db_session, test_setup):
    db = db_session
    proj_a = test_setup["proj_a"]
    comp_a1 = test_setup["comp_a1"]
    comp_a2 = test_setup["comp_a2"]

    # Case 1: You #1, Comp #9 -> Gap +8 (Target Leads)
    # Case 2: You #12, Comp #3 -> Gap -9 (Competitor Leads)
    # Case 3: You #5, Comp None (Unranked) -> Gap None
    # Case 4: You None (Unranked), Comp #4 -> Gap None (Competitor Opportunity)

    # 1. Target rankings
    db.add_all([
        Keyword(
            id=str(uuid.uuid4()),
            project_id=proj_a.id,
            keyword="best solar Brisbane",
            position=1,
            target_url="https://mysolarbrisbane.com.au/best",
            device="desktop",
            country="Australia",
        ),
        Keyword(
            id=str(uuid.uuid4()),
            project_id=proj_a.id,
            keyword="solar batteries Brisbane",
            position=12,
            target_url="https://mysolarbrisbane.com.au/batteries",
            device="desktop",
            country="Australia",
        ),
        Keyword(
            id=str(uuid.uuid4()),
            project_id=proj_a.id,
            keyword="commercial solar installation",
            position=5,
            target_url="https://mysolarbrisbane.com.au/commercial",
            device="desktop",
            country="Australia",
        ),
    ])
    db.commit()

    # 2. Competitor rankings
    db.add_all([
        CompetitorRanking(
            id=str(uuid.uuid4()),
            project_id=proj_a.id,
            competitor_id=comp_a1.id,
            keyword="best solar Brisbane",
            position=9,
            ranking_url="https://solarcompetitora.com.au/best-solar",
            device="desktop",
            country="Australia",
            source="serp_provider",
            checked_at=datetime.now(timezone.utc),
        ),
        CompetitorRanking(
            id=str(uuid.uuid4()),
            project_id=proj_a.id,
            competitor_id=comp_a2.id,
            keyword="solar batteries Brisbane",
            position=3,
            ranking_url="https://solarcompetitorb.com.au/batteries",
            device="desktop",
            country="Australia",
            source="csv_import",
            checked_at=datetime.now(timezone.utc),
        ),
        CompetitorRanking(
            id=str(uuid.uuid4()),
            project_id=proj_a.id,
            competitor_id=comp_a1.id,
            keyword="off grid solar packages",
            position=4,
            ranking_url="https://solarcompetitora.com.au/off-grid",
            device="desktop",
            country="Australia",
            source="serp_provider",
            checked_at=datetime.now(timezone.utc),
        ),
    ])
    db.commit()

    # Run gap analysis
    gap_result = perform_keyword_gap_analysis(
        project=proj_a,
        db=db,
    )
    items = gap_result["gap_items"]
    by_kw_comp = {(item["keyword"], item["competitor_domain"]): item for item in items}

    # Verify Case 1: You #1, Comp A #9 -> Gap +8 (Target Leads)
    kw1 = by_kw_comp[("best solar Brisbane", "solarcompetitora.com.au")]
    assert kw1["target_position"] == 1
    assert kw1["competitor_position"] == 9
    assert kw1["position_difference"] == 8  # 9 - 1 = +8 (Target leads)
    assert kw1["opportunity_level"] == "LOW"  # Target leads (safe)
    assert kw1["source"] == "serp_provider"

    # Verify Case 2: You #12, Comp B #3 -> Gap -9 (Competitor Leads)
    kw2 = by_kw_comp[("solar batteries Brisbane", "solarcompetitorb.com.au")]
    assert kw2["target_position"] == 12
    assert kw2["competitor_position"] == 3
    assert kw2["position_difference"] == -9  # 3 - 12 = -9 (Competitor leads)
    assert kw2["opportunity_level"] == "HIGH"  # Competitor leads (high opportunity)
    assert kw2["source"] == "csv_import"

    # Verify Case 3: You #5, Comp A None -> Gap None
    kw3 = by_kw_comp[("commercial solar installation", "solarcompetitora.com.au")]
    assert kw3["target_position"] == 5
    assert kw3["competitor_position"] is None
    assert kw3["position_difference"] is None
    assert kw3["opportunity_level"] == "MEDIUM"

    # Verify Case 4: You None, Comp A #4 -> Gap None
    kw4 = by_kw_comp[("off grid solar packages", "solarcompetitora.com.au")]
    assert kw4["target_position"] is None
    assert kw4["competitor_position"] == 4
    assert kw4["position_difference"] is None
    assert kw4["opportunity_level"] == "HIGH"


def test_competitor_ranking_importer_valid_and_invalid(db_session, test_setup):
    db = db_session
    proj_a = test_setup["proj_a"]
    comp_a1 = test_setup["comp_a1"]

    records = [
        {
            "competitor": "solarcompetitora.com.au",
            "keyword": "solar inverter replacement",
            "position": "4",
            "ranking_url": "https://solarcompetitora.com.au/inverters",
            "search_engine": "google",
            "country": "Australia",
            "location": "Brisbane",
            "device": "desktop",
        },
        {
            "competitor": "solarcompetitora.com.au",
            "keyword": "invalid zero position",
            "position": "0",  # 0 is strictly invalid
            "ranking_url": "https://solarcompetitora.com.au/zero",
            "search_engine": "google",
            "country": "Australia",
            "location": "Brisbane",
            "device": "desktop",
        },
        {
            "competitor": "solarcompetitora.com.au",
            "keyword": "",  # missing keyword is invalid
            "position": "10",
            "ranking_url": "https://solarcompetitora.com.au/nokeyword",
            "search_engine": "google",
            "country": "Australia",
            "location": "Brisbane",
            "device": "desktop",
        },
        {
            "competitor": "newcompetitor.com.au",
            "keyword": "solar panels cost",
            "position": "7",
            "ranking_url": "https://newcompetitor.com.au/cost",
            "search_engine": "google",
            "country": "Australia",
            "location": "Brisbane",
            "device": "desktop",
        },
    ]

    importer = CompetitorRankingImporter(db=db, project_id=proj_a.id, filename="competitor_rankings.csv")
    importer.start_import("competitor_rankings")
    successful, errors = importer.process_records(records)
    importer.finish_import()
    report = importer.get_structured_import_report()

    assert successful == 2  # rows 1 and 4 are valid
    assert errors == 2      # row 2 (pos 0) and row 3 (missing kw)
    assert report["successful_records"] == 2
    assert report["error_records"] == 2

    # Verify row 1 was stored
    rec = (
        db.query(CompetitorRanking)
        .filter(
            CompetitorRanking.project_id == proj_a.id,
            CompetitorRanking.keyword == "solar inverter replacement",
        )
        .first()
    )
    assert rec is not None
    assert rec.position == 4
    assert rec.source == "csv_import"

    # Verify newly discovered competitor was created and linked
    new_comp = (
        db.query(Competitor)
        .filter(
            Competitor.project_id == proj_a.id,
            Competitor.domain == "newcompetitor.com.au",
        )
        .first()
    )
    assert new_comp is not None


def test_project_isolation_security(db_session, test_setup):
    db = db_session
    proj_a = test_setup["proj_a"]
    proj_b = test_setup["proj_b"]
    comp_a1 = test_setup["comp_a1"]

    # Store ranking under Project A
    store_competitor_ranking(
        db=db,
        project_id=proj_a.id,
        competitor_id=comp_a1.id,
        keyword="isolated solar keyword",
        position=2,
        ranking_url="https://solarcompetitora.com.au/isolated",
        source="serp_provider",
    )

    # Project B gap analysis must NOT see Project A's competitor ranking
    gap_b = perform_keyword_gap_analysis(project=proj_b, db=db)
    assert len(gap_b["gap_items"]) == 0

    # Direct query under Project B must return nothing
    rec_b = (
        db.query(CompetitorRanking)
        .filter(
            CompetitorRanking.project_id == proj_b.id,
            CompetitorRanking.keyword == "isolated solar keyword",
        )
        .first()
    )
    assert rec_b is None


def test_serp_provider_competitor_normalization():
    provider = SERPRankTrackerProvider(api_key=None)
    competitors = [
        {"id": "c1", "domain": "solarcompetitora.com.au", "name": "Solar Competitor A"},
        {"id": "c2", "domain": "solarcompetitorb.com.au", "name": "Solar Competitor B"},
    ]
    results = provider.check_competitor_rankings(
        keywords=["best solar Brisbane", "solar batteries Brisbane"],
        competitors=competitors,
        country="Australia",
        language="English",
        device="Desktop",
    )

    assert len(results) == 4  # 2 competitors x 2 keywords
    for res in results:
        assert res["search_engine"] == "Google"
        assert res["country"] == "Australia"
        assert res["device"] == "Desktop"
        assert res["source"] == "serp_provider"
        assert res["position"] is None  # Unranked/No fake numbers
        assert "Checked / No Ranking Detected" in res["status"]

