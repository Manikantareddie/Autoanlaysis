import importlib.util
from pathlib import Path

from app.services.profiler import profile_csv

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "data" / "scripts" / "generate_retail_data.py"
SPEC = importlib.util.spec_from_file_location("retail_generator", SCRIPT)
assert SPEC and SPEC.loader
retail_generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(retail_generator)


def test_profiler_reports_known_messy_dataset_quality_issues(tmp_path: Path) -> None:
    retail_generator.generate(tmp_path)

    profile, _ = profile_csv(tmp_path / "retail_sales_messy.csv")

    assert profile["row_count"] == 20_150
    assert profile["column_count"] == 16
    assert profile["duplicate_row_count"] >= 150
    discount = next(column for column in profile["columns"] if column["name"] == "discount")
    assert discount["missing_count"] == 240
    assert any(warning["code"] == "duplicate_rows" for warning in profile["warnings"])

