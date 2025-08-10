import os
from pathlib import Path


def test_backend_has_no_yaml_loaders():
    # backend/tests/unit/v2 -> parents[3] is the backend dir
    backend_root = Path(__file__).resolve().parents[3] / "src"
    assert backend_root.exists()

    forbidden_substrings = ["yaml.safe_load", ".yaml"]

    for root, _, files in os.walk(backend_root):
        for fname in files:
            if not fname.endswith((".py", ".md", ".json")):
                continue
            fpath = Path(root) / fname
            try:
                text = fpath.read_text(encoding="utf-8")
            except Exception:
                continue
            for needle in forbidden_substrings:
                assert needle not in text, f"Found forbidden '{needle}' in {fpath}"
