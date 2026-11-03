"""
AQUORA Phase 6B.5: Tests for Multi-Source Flood Evidence Corroboration.

Validates:
1. Manifest structure, provenance, and zero-fabrication governance.
2. Independent separation of precipitation, hydrodynamic model, municipal logs, and SAR.
3. Non-conflation of rainfall alone as proof of surface inundation.
4. Non-conflation of SAR candidate evidence as self-validation.
5. Spatial corroboration with municipal critical facilities (Kurla, Sion, BKC).
6. Explicit recording of validation gaps and lack of certified GIS ground-truth polygons.
"""

from pathlib import Path
import json
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6b5_corroboration_manifest.yaml"
SUMMARY_JSON = PROJECT_ROOT / "data" / "processed" / "phase6b4" / "sar" / "E03_corroboration_summary.json"


@pytest.fixture(scope="module")
def corroboration_manifest():
    assert MANIFEST_PATH.exists(), f"Missing manifest at {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_corroboration_manifest_structure_and_governance(corroboration_manifest):
    """Verify manifest governance disallows certified ground-truth claims."""
    assert corroboration_manifest["phase"] == "PHASE_6B_5_MULTI_SOURCE_CORROBORATION"
    assert corroboration_manifest["event_target"]["event_id"] == "E03"

    gov = corroboration_manifest["governance"]
    assert gov["status"] == "CORROBORATED_PROVISIONAL_EVIDENCE"
    assert gov["label_classification"] == "CANDIDATE_SAR_FLOOD_EVIDENCE"
    assert gov["certified_ground_truth"] is False
    assert gov["zero_ml_training_enforced"] is True
    assert gov["zero_label_fabrication_enforced"] is True


def test_independent_sources_separated_without_conflation(corroboration_manifest):
    """Verify 4 distinct sources are recorded with individual provenance and uncertainties."""
    sources = corroboration_manifest["evidence_sources"]
    assert "source_1_precipitation" in sources
    assert "source_2_deterministic_hydrodynamic_simulation" in sources
    assert "source_3_municipal_incident_and_rescue_records" in sources
    assert "source_4_sentinel1_temporal_baselines" in sources

    # Source 1: Authentic IMD gauge
    src1 = sources["source_1_precipitation"]
    assert src1["observation_stations"]["imd_santacruz"]["24h_rainfall_total_mm"] == 375.2
    assert "conflation_guard" in src1
    assert "NOT constitute proof" in src1["conflation_guard"]

    # Source 2: Deterministic Hydrodynamic Model
    src2 = sources["source_2_deterministic_hydrodynamic_simulation"]
    assert "conflation_guard" in src2
    assert "clearly separated from observed" in src2["conflation_guard"]

    # Source 3: Municipal records
    src3 = sources["source_3_municipal_incident_and_rescue_records"]
    assert any("Kranti Nagar" in h["location"] for h in src3["documented_incident_hotspots"])
    assert any("Sion" in h["location"] for h in src3["documented_incident_hotspots"])


def test_temporal_baseline_tradeoffs_documented(corroboration_manifest):
    """Verify 8 June baseline limitation and 14 July optional recession scene are documented."""
    src4 = corroboration_manifest["evidence_sources"]["source_4_sentinel1_temporal_baselines"]
    assert "24-day baseline gap" in src4["pre_event_baseline_limitations"]
    assert "+1.77 dB" in src4["pre_event_baseline_limitations"] or "+1.78 dB" in src4["pre_event_baseline_limitations"]

    post = src4["optional_14_july_recession_scene"]
    assert "20190714" in post["granule_name"]
    assert post["role"] == "POST_EVENT_MONSOON_RECESSION_BASELINE"
    assert "12 days post-event" in post["tradeoff_limitation"]


def test_critical_facilities_proximity_corroboration(corroboration_manifest):
    """Verify municipal critical facilities in Kurla, Sion, and BKC capture surrounding flood evidence."""
    facilities = corroboration_manifest["facility_corroboration"]
    assert len(facilities) >= 5

    facility_names = [f["name"] for f in facilities]
    assert any("Sion Hospital" in name for name in facility_names)
    assert any("Kurla" in name for name in facility_names)
    assert any("BKC" in name for name in facility_names)

    # Sion Hospital and Kurla shelter are documented flooded zones
    sion_hosp = next(f for f in facilities if "Sion Hospital" in f["name"])
    assert sion_hosp["buffer_150m_has_open_water_drop"] is True or sion_hosp["buffer_150m_has_double_bounce"] is True


def test_validation_gaps_explicitly_documented(corroboration_manifest):
    """Verify that absent municipal GIS inundation polygons are explicitly listed as validation gaps."""
    gaps = corroboration_manifest["validation_gaps"]
    assert len(gaps) >= 3
    assert any("Absence of Official GIS Inundation Polygons" in g for g in gaps)
    assert any("Monsoon Onset Gap" in g for g in gaps)
    assert any("Urban Canyon Multipath" in g for g in gaps)
