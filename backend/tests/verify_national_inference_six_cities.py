import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.india_feature_pipeline import IndiaFeaturePipelineService
from app.services.ml_model_registry import NationalScreeningModel

cities = [
    ("Patna", 25.5941, 85.1376),
    ("Guwahati", 26.1445, 91.7362),
    ("Mumbai", 19.0760, 72.8777),
    ("Vijayawada", 16.5062, 80.6480),
    ("Nagpur", 21.1458, 79.0882),
    ("Ahmedabad", 23.0225, 72.5714),
]

pipeline = IndiaFeaturePipelineService()
model = NationalScreeningModel()
assert model.is_ready, "Model is not ready!"

print("=" * 80)
print("TEST 1: LIVE OPERATIONAL MODE (Rainfall Unobserved -> Strict Suppression)")
print("=" * 80)

for name, lat, lon in cities:
    extraction = pipeline.extract_point_features(lat, lon, allow_benchmark_rainfall=False)
    core_features = {k: extraction.features.get(k) for k in pipeline.CORE_NATIONAL_FEATURES}
    res = model.predict_risk(core_features)
    print(f"\n{name} ({lat:.4f}°N, {lon:.4f}°E):")
    print(f"  Model Status: {res['model_status']}")
    print(f"  Input Validity: {res.get('input_validity')}")
    print(f"  Missing Predictors: {res.get('missing_predictors')}")
    print(f"  Predicted Probability: {res['predicted_probability']}")
    assert res['model_status'] == "INSUFFICIENT_INPUT_DATA", f"Expected suppression for {name}"
    assert res['predicted_probability'] is None

print("\n" + "=" * 80)
print("TEST 2: HISTORICAL BENCHMARK SCENARIO (Monsoon Deluge Event -> Valid 7-Feature Inference)")
print("=" * 80)

# Realistic historical monsoon rain inputs: 24h=120mm, 72h=220mm, Anomaly=+2.5 sigma
for name, lat, lon in cities:
    extraction = pipeline.extract_point_features(lat, lon, allow_benchmark_rainfall=False)
    core_features = {k: extraction.features.get(k) for k in pipeline.CORE_NATIONAL_FEATURES}
    # Supply authentic benchmark rainfall
    core_features["rainfall_24h_mm"] = 120.0
    core_features["rainfall_72h_mm"] = 220.0
    core_features["rainfall_anomaly_index"] = 2.5
    res = model.predict_risk(core_features)
    print(f"\n{name} ({lat:.4f}°N, {lon:.4f}°E):")
    print(f"  Model Status: {res['model_status']}")
    print(f"  Predicted Probability: {res['predicted_probability']:.4f}")
    print(f"  Susceptibility Grade: {res['susceptibility_grade']}")
    print(f"  Available Predictors: {res.get('available_predictors')}")
    assert res['model_status'] == "OPERATIONAL"
    assert res['predicted_probability'] is not None
    assert 0.0 <= res['predicted_probability'] <= 1.0

print("\n" + "=" * 80)
print("TEST 3: DRY BENCHMARK SCENARIO (Measured Zero Rain -> Valid 7-Feature Low Score)")
print("=" * 80)

for name, lat, lon in cities:
    extraction = pipeline.extract_point_features(lat, lon, allow_benchmark_rainfall=False)
    core_features = {k: extraction.features.get(k) for k in pipeline.CORE_NATIONAL_FEATURES}
    # Measured zero rain
    core_features["rainfall_24h_mm"] = 0.0
    core_features["rainfall_72h_mm"] = 0.0
    core_features["rainfall_anomaly_index"] = -0.5
    res = model.predict_risk(core_features)
    print(f"\n{name} ({lat:.4f}°N, {lon:.4f}°E):")
    print(f"  Model Status: {res['model_status']}")
    print(f"  Predicted Probability: {res['predicted_probability']:.4f}")
    print(f"  Susceptibility Grade: {res['susceptibility_grade']}")
    assert res['model_status'] == "OPERATIONAL"
    assert res['predicted_probability'] < 0.15, f"Expected low score for dry condition, got {res['predicted_probability']}"

print("\n" + "=" * 80)
print("ALL INFERENCE TESTS PASSED FOR ALL 6 CITIES!")
print("=" * 80)
