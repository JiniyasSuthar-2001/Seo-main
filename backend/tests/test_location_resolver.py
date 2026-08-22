import os
import sys
import unittest

# Ensure backend directory is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.location_resolver import resolve_location, LocationConfidence
from app.services.competitor_service import extract_location_info

def test_location_resolution_system():
    print("============================================================", flush=True)
    print(" LOCATION RESOLVER & EVIDENCE AUDIT SUITE", flush=True)
    print("============================================================\n", flush=True)

    # 1. Sydney evidence -> Sydney
    loc1 = resolve_location(notes="Location: Sydney, NSW")
    assert loc1["city"] == "Sydney", f"Expected Sydney, got {loc1['city']}"
    assert loc1["confidence"] == LocationConfidence.MEDIUM

    # 2. Melbourne evidence -> Melbourne
    loc2 = resolve_location(notes="Headquarters: Melbourne")
    assert loc2["city"] == "Melbourne", f"Expected Melbourne, got {loc2['city']}"

    # 3. Brisbane evidence -> Brisbane
    loc3 = resolve_location(notes="Address: Brisbane, QLD")
    assert loc3["city"] == "Brisbane", f"Expected Brisbane, got {loc3['city']}"

    # 4. Adelaide evidence -> Adelaide
    loc4 = resolve_location(notes="Location: Adelaide")
    assert loc4["city"] == "Adelaide", f"Expected Adelaide, got {loc4['city']}"

    # 5. Perth evidence -> Perth
    loc5 = resolve_location(notes="Location: Perth")
    assert loc5["city"] == "Perth", f"Expected Perth, got {loc5['city']}"

    # 6. Canberra evidence -> Canberra
    loc6 = resolve_location(notes="Location: Canberra")
    assert loc6["city"] == "Canberra", f"Expected Canberra, got {loc6['city']}"

    # 7. Hobart evidence -> Hobart
    loc7 = resolve_location(notes="Location: Hobart")
    assert loc7["city"] == "Hobart", f"Expected Hobart, got {loc7['city']}"

    # 8. Darwin evidence -> Darwin
    loc8 = resolve_location(notes="Location: Darwin")
    assert loc8["city"] == "Darwin", f"Expected Darwin, got {loc8['city']}"

    # 9. Non-Australian location -> correct country/location when evidence exists
    loc9 = resolve_location(
        schema_data=[{
            "@type": "LocalBusiness",
            "address": {
                "addressLocality": "London",
                "addressRegion": "Greater London",
                "addressCountry": "United Kingdom"
            }
        }]
    )
    assert loc9["city"] == "London"
    assert loc9["country"] == "United Kingdom"
    assert loc9["confidence"] == LocationConfidence.HIGH

    # 10. CRITICAL REGRESSION: .au domain without city evidence -> city remains None / Unknown (NOT Brisbane!)
    loc10 = resolve_location(project_url="https://example.au")
    assert loc10["city"] is None, f"Expected city None for example.au, got '{loc10['city']}'"
    assert loc10["country"] == "Australia"
    assert loc10["confidence"] == LocationConfidence.LOW

    # Verify extract_location_info wrapper for .au domain
    class MockProject:
        url = "https://example.au"
        domain = "example.au"
        target_country = None
        notes = None
        description = None

    extracted_au = extract_location_info(MockProject())
    assert extracted_au["city"] == "Unknown", f"CRITICAL REGRESSION FAIL: example.au returned city '{extracted_au['city']}' instead of 'Unknown'"
    assert extracted_au["country"] == "Australia"
    print("      [PASS] Verified CRITICAL REGRESSION: 'example.au' does NOT automatically become Brisbane.\n", flush=True)

    # 11. US domain without location evidence -> no Australian location
    loc11 = resolve_location(project_url="https://example.com")
    assert loc11["country"] is None or loc11["country"] != "Australia"

    # 12. UK domain without location evidence -> no Australian location
    loc12 = resolve_location(project_url="https://example.co.uk")
    assert loc12["country"] == "United Kingdom"

    # 13. Structured Schema takes precedence over weak text
    loc14 = resolve_location(
        notes="Location: Sydney",
        schema_data=[{
            "@type": "LocalBusiness",
            "address": {"addressLocality": "Adelaide", "addressCountry": "Australia"}
        }]
    )
    assert loc14["city"] == "Adelaide"
    assert loc14["confidence"] == LocationConfidence.HIGH

    # 14. No location evidence -> Unknown
    loc15 = resolve_location()
    assert loc15["city"] is None
    assert loc15["country"] is None
    assert loc15["confidence"] == LocationConfidence.UNKNOWN

    print("All location resolution regression tests passed successfully!", flush=True)

if __name__ == "__main__":
    test_location_resolution_system()
