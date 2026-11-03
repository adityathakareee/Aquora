import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
import joblib

p = Path(__file__).resolve().parent.parent / "ml" / "models" / "aquora_national_screening_model.joblib"
payload = joblib.load(p)
print("Keys:", list(payload.keys()))
print("Schema version:", payload.get("schema_version"))
print("Model version:", payload.get("model_version"))
print("Status:", payload.get("status"))
print("Feature names:", payload.get("feature_names"))
print("Metadata:", payload.get("metadata"))

