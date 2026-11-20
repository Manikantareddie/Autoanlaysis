"""Create deterministic clean and deliberately messy retail CSV fixtures.

The clean file is the analytical reference. The discount field is a decimal
percentage. Net revenue is zero for cancelled and returned orders, reflecting a
cancelled sale or a fully refunded return.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

SEED = 20261120
ORDER_COUNT = 20_000
PRODUCT_COUNT = 500
FIELDNAMES = [
    "order_id", "order_date", "customer_id", "product_id", "product_name",
    "category", "region", "quantity", "unit_price", "cost_price", "discount",
    "returned", "order_status", "gross_revenue", "net_revenue", "gross_profit",
]
CATEGORIES = ["Electronics", "Home & Kitchen", "Office Supplies", "Apparel", "Sports & Outdoors"]
REGIONS = ["North", "South", "East", "West"]
MONTH_WEIGHTS = [0.78, 0.8, 0.9, 0.95, 1.0, 1.02, 0.96, 0.98, 1.05, 1.12, 1.42, 1.7]


def money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def build_products() -> list[dict[str, object]]:
    products: list[dict[str, object]] = []
    for index in range(PRODUCT_COUNT):
        category = CATEGORIES[index % len(CATEGORIES)]
        base_price = Decimal(12 + ((index * 19) % 240)) + Decimal(index % 10) / 10
        products.append({
            "product_id": f"P{index + 1:04d}",
            "product_name": f"{category.split()[0]} Product {index + 1:03d}",
            "category": category,
            "unit_price": base_price,
            "cost_price": (base_price * Decimal("0.58") + Decimal(index % 7)).quantize(Decimal("0.01")),
        })
    return products


def weighted_date(rng: random.Random) -> date:
    month = rng.choices(range(1, 13), weights=MONTH_WEIGHTS, k=1)[0]
    start = date(2025, month, 1)
    next_month = date(2026, 1, 1) if month == 12 else date(2025, month + 1, 1)
    return start + timedelta(days=rng.randrange((next_month - start).days))


def make_clean_rows() -> list[dict[str, str]]:
    rng = random.Random(SEED)
    products = build_products()
    rows: list[dict[str, str]] = []
    for number in range(1, ORDER_COUNT + 1):
        product = rng.choice(products)
        quantity = rng.choices([1, 2, 3, 4, 5, 6], weights=[42, 30, 15, 7, 4, 2], k=1)[0]
        discount = Decimal(str(rng.choices([0, .05, .1, .15, .2, .3], weights=[31, 25, 20, 13, 8, 3], k=1)[0]))
        status = rng.choices(["completed", "returned", "cancelled"], weights=[92, 5, 3], k=1)[0]
        gross = (product["unit_price"] * quantity * (Decimal("1") - discount)).quantize(Decimal("0.01"))
        net = Decimal("0") if status in {"returned", "cancelled"} else gross
        cost = (product["cost_price"] * quantity).quantize(Decimal("0.01"))
        rows.append({
            "order_id": f"ORD-{number:06d}",
            "order_date": weighted_date(rng).isoformat(),
            "customer_id": f"C{rng.randint(1, 6_000):05d}",
            "product_id": str(product["product_id"]),
            "product_name": str(product["product_name"]),
            "category": str(product["category"]),
            "region": rng.choices(REGIONS, weights=[1.05, .93, 1.12, .98], k=1)[0],
            "quantity": str(quantity),
            "unit_price": money(product["unit_price"]),
            "cost_price": money(product["cost_price"]),
            "discount": str(discount),
            "returned": str(status == "returned").lower(),
            "order_status": status,
            "gross_revenue": money(gross),
            "net_revenue": money(net),
            "gross_profit": money(net - cost if status == "completed" else Decimal("0")),
        })
    return rows


def make_messy_rows(clean_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rng = random.Random(SEED + 1)
    rows = [dict(row) for row in clean_rows]
    indexes = list(range(len(rows)))
    rng.shuffle(indexes)
    for index in indexes[:240]:
        rows[index]["discount"] = ""
    for index in indexes[240:490]:
        rows[index]["order_date"] = date.fromisoformat(rows[index]["order_date"]).strftime("%d/%m/%Y")
    for index in indexes[490:690]:
        rows[index]["category"] = rows[index]["category"].lower() if index % 2 else f" {rows[index]['category']} "
    for index in indexes[690:760]:
        rows[index]["quantity"] = "0" if index % 2 else "-1"
    for index in indexes[760:810]:
        rows[index]["unit_price"] = money(Decimal(rows[index]["unit_price"]) * Decimal("40"))
    rows.extend(dict(clean_rows[index]) for index in indexes[810:960])
    return rows


def calculate_ground_truth(rows: list[dict[str, str]]) -> dict[str, object]:
    by_category: defaultdict[str, Decimal] = defaultdict(Decimal)
    by_region: defaultdict[str, Decimal] = defaultdict(Decimal)
    by_month: defaultdict[str, Decimal] = defaultdict(Decimal)
    for row in rows:
        value = Decimal(row["net_revenue"])
        by_category[row["category"]] += value
        by_region[row["region"]] += value
        by_month[row["order_date"][:7]] += value
    return {
        "seed": SEED,
        "clean_row_count": len(rows),
        "completed_order_count": sum(row["order_status"] == "completed" for row in rows),
        "returned_order_count": sum(row["order_status"] == "returned" for row in rows),
        "cancelled_order_count": sum(row["order_status"] == "cancelled" for row in rows),
        "net_revenue": money(sum(Decimal(row["net_revenue"]) for row in rows)),
        "net_revenue_by_category": {key: money(value) for key, value in sorted(by_category.items())},
        "net_revenue_by_region": {key: money(value) for key, value in sorted(by_region.items())},
        "net_revenue_by_month": {key: money(value) for key, value in sorted(by_month.items())},
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def generate(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_rows = make_clean_rows()
    messy_rows = make_messy_rows(clean_rows)
    write_csv(output_dir / "retail_sales_clean.csv", clean_rows)
    write_csv(output_dir / "retail_sales_messy.csv", messy_rows)
    ground_truth = calculate_ground_truth(clean_rows)
    ground_truth["messy_row_count"] = len(messy_rows)
    ground_truth["messy_known_issues"] = {
        "missing_discount": 240, "non_iso_dates": 250, "inconsistent_categories": 200,
        "invalid_quantities": 70, "price_outliers": 50, "duplicate_rows_added": 150,
    }
    (output_dir / "retail_ground_truth.json").write_text(json.dumps(ground_truth, indent=2) + "\n", encoding="utf-8")
    return ground_truth


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate reproducible InsightPilot retail datasets.")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parents[1] / "generated")
    arguments = parser.parse_args()
    result = generate(arguments.output_dir)
    print(f"Generated {result['clean_row_count']} clean rows and {result['messy_row_count']} messy rows.")

