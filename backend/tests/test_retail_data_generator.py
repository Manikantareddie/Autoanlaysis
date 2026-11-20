import csv
import importlib.util
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "data" / "scripts" / "generate_retail_data.py"
SPEC = importlib.util.spec_from_file_location("retail_generator", SCRIPT)
assert SPEC and SPEC.loader
retail_generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(retail_generator)


def test_generator_creates_reproducible_datasets_and_ground_truth(tmp_path: Path) -> None:
    retail_generator.generate(tmp_path)

    with (tmp_path / "retail_sales_clean.csv").open(encoding="utf-8", newline="") as handle:
        clean_rows = list(csv.DictReader(handle))
    with (tmp_path / "retail_sales_messy.csv").open(encoding="utf-8", newline="") as handle:
        messy_rows = list(csv.DictReader(handle))
    ground_truth = json.loads((tmp_path / "retail_ground_truth.json").read_text(encoding="utf-8"))

    assert len(clean_rows) == 20_000
    assert len(messy_rows) == 20_150
    assert sum(Decimal(row["net_revenue"]) for row in clean_rows) == Decimal(ground_truth["net_revenue"])
    assert {row["product_id"] for row in clean_rows} == {f"P{index:04d}" for index in range(1, 501)}
    assert sum(row["discount"] == "" for row in messy_rows) == 240
    assert sum(row["quantity"] in {"0", "-1"} for row in messy_rows) == 70


def test_generator_is_deterministic(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    retail_generator.generate(first)
    retail_generator.generate(second)
    assert (first / "retail_sales_clean.csv").read_bytes() == (second / "retail_sales_clean.csv").read_bytes()

