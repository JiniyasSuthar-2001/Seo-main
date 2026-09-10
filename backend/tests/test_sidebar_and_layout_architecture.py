import os
import re
import pytest

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))

def test_layout_css_sidebar_rules():
    layout_css_path = os.path.join(FRONTEND_DIR, "styles", "layout.css")
    assert os.path.exists(layout_css_path), "layout.css must exist"

    with open(layout_css_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify sidebar container fixed width and vertical constraints
    assert "#sidebar-container" in content
    assert "width: 250px" in content or "min-width: 250px" in content
    assert "position: fixed" in content

    # Verify nav-group flex direction column
    assert ".nav-group" in content
    assert "flex-direction: column" in content

    # Verify nav-item display flex row alignment
    assert ".nav-item" in content
    assert "display: flex" in content
    assert "align-items: center" in content

    # Verify scroll area has vertical scroll and no horizontal scroll
    assert ".sidebar-scroll-area" in content
    assert "overflow-y: auto" in content
    assert "overflow-x: hidden" in content


def test_customer_sidebar_structure_and_no_master_badge():
    customer_sidebar_path = os.path.join(FRONTEND_DIR, "src", "components", "CustomerSidebar.js")
    assert os.path.exists(customer_sidebar_path), "CustomerSidebar.js must exist"

    with open(customer_sidebar_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must NOT have master badge in customer sidebar
    assert "master-switch-badge" not in content, "Customer sidebar must not display MASTER switch badge"
    assert "MASTER SPACE" not in content
    assert "Admin Console" not in content

    # Must have expected customer navigation sections
    assert "WEBSITE" in content
    assert "GROWTH" in content
    assert "REPORTS" in content
    assert "DATA & SETTINGS" in content

    # Must have core customer nav items
    expected_items = [
        "Overview", "My Website", "Pages", "Website Check",
        "Keywords", "Search Rankings", "Links", "Internal Links", "Competitors", "Recommended Actions",
        "Reports", "Crawl Data", "Website Scan History", "Alerts",
        "Import Data", "Connections", "Settings", "Help"
    ]
    for item in expected_items:
        assert f"<span>{item}</span>" in content, f"Missing customer nav item: {item}"


def test_master_sidebar_structure_and_isolation():
    master_sidebar_path = os.path.join(FRONTEND_DIR, "src", "components", "MasterSidebar.js")
    assert os.path.exists(master_sidebar_path), "MasterSidebar.js must exist"

    with open(master_sidebar_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must have Master space operations
    assert "MASTER SPACE OPERATIONS" in content or "MASTER SPACE" in content
    assert "Admin Console" in content

    # Must have expected Master admin nav items
    expected_master_items = [
        "Dashboard", "Customers", "Websites", "AI Analytics", "AI Control",
        "Credits", "Providers", "Activity", "System Health", "Audit Logs"
    ]
    for item in expected_master_items:
        assert f"<span>{item}</span>" in content, f"Missing master nav item: {item}"

    # Customer workspace navigation must NOT be inside Master sidebar
    assert "WEBSITE" not in content
    assert "GROWTH" not in content
    assert "<span>Keywords</span>" not in content
    assert "<span>Search Rankings</span>" not in content
