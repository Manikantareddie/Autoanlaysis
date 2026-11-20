from __future__ import annotations

from pathlib import Path
import duckdb


def compute_dataset_dashboard(duckdb_path: Path) -> dict:
    conn = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        desc = conn.execute("DESCRIBE dataset").fetchall()
        cols = {row[0]: row[1].upper() for row in desc}

        num_cols = [
            c for c, t in cols.items()
            if any(n in t for n in ["INT", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC", "REAL"])
            and not c.lower().endswith("_id") and c.lower() != "id"
        ]
        cat_cols = [
            c for c, t in cols.items()
            if ("VARCHAR" in t or "TEXT" in t or "STRING" in t)
            and not c.lower().endswith("_id") and c.lower() != "id"
        ]
        date_cols = [
            c for c, t in cols.items()
            if any(d in t for d in ["DATE", "TIMESTAMP", "TIME"]) or "date" in c.lower()
        ]
        id_cols = [
            c for c in cols
            if any(k in c.lower() for k in ["order_id", "transaction_id", "invoice", "id", "customer_id", "user_id"])
        ]

        # Non-additive column names that should NEVER be summed as "Total X"
        non_additive_patterns = ["unit_price", "price", "rate", "cost_per_unit", "pct", "percent", "discount", "lat", "lon", "age", "year", "score", "index"]

        # 1. Search for genuine additive monetary/revenue columns
        revenue_prio = [
            "net_revenue", "gross_revenue", "revenue", "sales", "total_sales",
            "total_amount", "amount", "profit", "net_sales", "spend"
        ]
        revenue_col = next(
            (c for p in revenue_prio for c in num_cols if p == c.lower()),
            next((c for p in revenue_prio for c in num_cols if p in c.lower()), None)
        )

        # 2. Search for volume/quantity columns
        qty_col = next(
            (c for c in num_cols if any(k in c.lower() for k in ["quantity", "units", "items_sold", "volume"])),
            None
        )

        # 3. Search for unit price
        price_col = next(
            (c for c in num_cols if any(k in c.lower() for k in ["unit_price", "price"])),
            None
        )

        # 4. Search for discount
        discount_col = next(
            (c for c in num_cols if any(k in c.lower() for k in ["discount_pct", "discount"])),
            None
        )

        cat_prio = [
            "category", "department", "segment", "region", "product_name",
            "order_status", "status", "type", "country"
        ]
        cat_col = next(
            (c for p in cat_prio for c in cat_cols if p == c.lower()),
            next((c for p in cat_prio for c in cat_cols if p in c.lower()), cat_cols[0] if cat_cols else None)
        )

        status_col = next(
            (c for c in cat_cols if any(k in c.lower() for k in ["status", "returned", "cancelled", "state"])),
            None
        )

        total_rows = conn.execute("SELECT COUNT(*) FROM dataset").fetchone()[0]

        kpis = [
            {
                "label": "Total Records",
                "value": total_rows,
                "format": "number",
                "description": "Total records ingested and verified in DuckDB",
            }
        ]

        if id_cols:
            primary_id = id_cols[0]
            unique_ids = conn.execute(f"SELECT COUNT(DISTINCT {primary_id}) FROM dataset").fetchone()[0]
            label = primary_id.replace("_", " ").title()
            kpis.append({
                "label": f"Unique {label}",
                "value": unique_ids,
                "format": "number",
                "description": f"Distinct count of {label} (identifies multi-line or repeat entries)",
            })

        # Add primary commercial / analytical metrics
        chart_val_col = None
        chart_val_label = None

        if revenue_col:
            rev_sum, rev_avg = conn.execute(
                f"SELECT ROUND(SUM({revenue_col}), 2), ROUND(AVG({revenue_col}), 2) FROM dataset WHERE {revenue_col} IS NOT NULL"
            ).fetchone()
            rev_label = revenue_col.replace("_", " ").title()
            kpis.append({
                "label": f"Total {rev_label}",
                "value": rev_sum or 0,
                "format": "number",
                "description": f"Aggregate sum across all records",
            })
            if id_cols and primary_id:
                # Average order value if distinct orders
                aov = conn.execute(
                    f"SELECT ROUND(SUM({revenue_col}) / NULLIF(COUNT(DISTINCT {primary_id}), 0), 2) FROM dataset WHERE {revenue_col} IS NOT NULL"
                ).fetchone()[0]
                if aov:
                    kpis.append({
                        "label": f"Average {rev_label} per Order",
                        "value": aov,
                        "format": "number",
                        "description": f"Mean {rev_label} per unique {primary_id.replace('_', ' ').title()}",
                    })
            else:
                kpis.append({
                    "label": f"Average {rev_label}",
                    "value": rev_avg or 0,
                    "format": "number",
                    "description": f"Mean value per record",
                })
            chart_val_col = revenue_col
            chart_val_label = rev_label

        elif qty_col and price_col:
            # Derived revenue: calculate from quantity and unit price, factoring in discount if available
            calc_expr = f"{qty_col} * {price_col}"
            if discount_col:
                calc_expr = f"{qty_col} * {price_col} * (1.0 - COALESCE({discount_col}, 0) / 100.0)"
            calc_sum = conn.execute(f"SELECT ROUND(SUM({calc_expr}), 2) FROM dataset").fetchone()[0]
            kpis.append({
                "label": "Total Estimated Sales",
                "value": calc_sum or 0,
                "format": "number",
                "description": f"Derived from {qty_col} × {price_col}" + (f" with {discount_col}" if discount_col else ""),
            })
            chart_val_col = calc_expr
            chart_val_label = "Sales Revenue"

        if qty_col and len(kpis) < 5:
            qty_sum = conn.execute(f"SELECT SUM({qty_col}) FROM dataset WHERE {qty_col} IS NOT NULL").fetchone()[0]
            kpis.append({
                "label": f"Total {qty_col.replace('_', ' ').title()}",
                "value": qty_sum or 0,
                "format": "number",
                "description": f"Cumulative units / volume across all records",
            })
            if not chart_val_col:
                chart_val_col = qty_col
                chart_val_label = qty_col.replace("_", " ").title()

        if price_col and len(kpis) < 5:
            avg_price = conn.execute(f"SELECT ROUND(AVG({price_col}), 2) FROM dataset WHERE {price_col} IS NOT NULL").fetchone()[0]
            kpis.append({
                "label": f"Average {price_col.replace('_', ' ').title()}",
                "value": avg_price or 0,
                "format": "number",
                "description": f"Mean unit pricing across catalog/orders",
            })

        # Generic numeric columns fallback if no specific commercial columns found
        if not chart_val_col:
            # Pick first numeric column that is not strictly non-additive
            additive_candidate = next((c for c in num_cols if not any(p in c.lower() for p in non_additive_patterns)), None)
            if additive_candidate:
                val_sum = conn.execute(f"SELECT ROUND(SUM({additive_candidate}), 2) FROM dataset WHERE {additive_candidate} IS NOT NULL").fetchone()[0]
                kpis.append({
                    "label": f"Total {additive_candidate.replace('_', ' ').title()}",
                    "value": val_sum or 0,
                    "format": "number",
                    "description": f"Aggregate sum",
                })
                chart_val_col = additive_candidate
                chart_val_label = additive_candidate.replace("_", " ").title()
            elif num_cols:
                fallback_col = num_cols[0]
                val_avg = conn.execute(f"SELECT ROUND(AVG({fallback_col}), 2) FROM dataset WHERE {fallback_col} IS NOT NULL").fetchone()[0]
                kpis.append({
                    "label": f"Average {fallback_col.replace('_', ' ').title()}",
                    "value": val_avg or 0,
                    "format": "number",
                    "description": f"Mean value across records",
                })
                chart_val_col = fallback_col
                chart_val_label = fallback_col.replace("_", " ").title()

        if status_col:
            ret_rate = conn.execute(
                f"SELECT ROUND(COUNT(CASE WHEN LOWER({status_col}) IN ('returned', 'cancelled', 'refunded', 'failed') THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) FROM dataset"
            ).fetchone()[0]
            if ret_rate is not None and ret_rate > 0 and len(kpis) < 5:
                kpis.append({
                    "label": "Exception / Return Rate",
                    "value": ret_rate,
                    "format": "percentage",
                    "description": f"Percentage of {status_col} marked as returned or cancelled",
                })

        # Date Coverage
        date_range_str = None
        if date_cols:
            primary_date = date_cols[0]
            try:
                min_d, max_d = conn.execute(f"SELECT MIN(CAST({primary_date} AS VARCHAR)), MAX(CAST({primary_date} AS VARCHAR)) FROM dataset WHERE {primary_date} IS NOT NULL").fetchone()
                if min_d and max_d:
                    date_range_str = f"{min_d[:10]} to {max_d[:10]}"
            except Exception:
                pass

        charts = []

        if date_cols and chart_val_col:
            primary_date = date_cols[0]
            try:
                trend_data = conn.execute(f"""
                    SELECT strftime(CAST({primary_date} AS DATE), '%b %Y') as period, ROUND(SUM({chart_val_col}), 2) as val
                    FROM dataset
                    WHERE {primary_date} IS NOT NULL AND ({chart_val_col}) IS NOT NULL
                    GROUP BY strftime(CAST({primary_date} AS DATE), '%Y-%m'), period
                    ORDER BY strftime(CAST({primary_date} AS DATE), '%Y-%m')
                    LIMIT 12
                """).fetchall()
                if trend_data:
                    charts.append({
                        "title": f"Monthly Trend: {chart_val_label}",
                        "type": "trend",
                        "x_label": "Month",
                        "y_label": chart_val_label,
                        "items": [{"label": row[0], "value": float(row[1])} for row in trend_data],
                    })
            except Exception:
                pass

        if cat_col and chart_val_col:
            try:
                cat_data = conn.execute(f"""
                    SELECT {cat_col}, ROUND(SUM({chart_val_col}), 2) as val
                    FROM dataset
                    WHERE {cat_col} IS NOT NULL AND ({chart_val_col}) IS NOT NULL
                    GROUP BY {cat_col}
                    ORDER BY val DESC
                    LIMIT 6
                """).fetchall()
                if cat_data:
                    charts.append({
                        "title": f"Top {cat_col.replace('_', ' ').title()} by {chart_val_label}",
                        "type": "category",
                        "x_label": cat_col.replace("_", " ").title(),
                        "y_label": chart_val_label,
                        "items": [{"label": str(row[0]), "value": float(row[1])} for row in cat_data],
                    })
            except Exception:
                pass

        secondary_cat = next((c for c in cat_cols if c != cat_col and any(k in c.lower() for k in ["region", "status", "country", "type", "segment"])), None)
        if secondary_cat and chart_val_col:
            try:
                sec_data = conn.execute(f"""
                    SELECT {secondary_cat}, ROUND(SUM({chart_val_col}), 2) as val
                    FROM dataset
                    WHERE {secondary_cat} IS NOT NULL AND ({chart_val_col}) IS NOT NULL
                    GROUP BY {secondary_cat}
                    ORDER BY val DESC
                    LIMIT 6
                """).fetchall()
                if sec_data:
                    charts.append({
                        "title": f"{secondary_cat.replace('_', ' ').title()} Distribution ({chart_val_label})",
                        "type": "distribution",
                        "x_label": secondary_cat.replace("_", " ").title(),
                        "y_label": chart_val_label,
                        "items": [{"label": str(row[0]), "value": float(row[1])} for row in sec_data],
                    })
            except Exception:
                pass

        suggested_questions = []
        if cat_col and chart_val_col:
            suggested_questions.append({
                "question": f"What are the top 5 {cat_col.replace('_', ' ')}s by {chart_val_label.lower()}?",
                "category": "Rankings",
            })
        if date_cols and chart_val_col:
            suggested_questions.append({
                "question": f"How did {chart_val_label.lower()} change month-over-month?",
                "category": "Trends",
            })
        if secondary_cat and chart_val_col:
            suggested_questions.append({
                "question": f"Compare {chart_val_label.lower()} across different {secondary_cat.replace('_', ' ')}s.",
                "category": "Comparisons",
            })
        product_col = next((c for c in cat_cols if "product" in c.lower()), None)
        if product_col and chart_val_col:
            suggested_questions.append({
                "question": f"Which {product_col.replace('_', ' ')}s generated the highest revenue?",
                "category": "Performance",
            })
        if discount_col:
            suggested_questions.append({
                "question": f"What is the average discount percentage and how does it correlate with volume?",
                "category": "Pricing",
            })
        if status_col:
            suggested_questions.append({
                "question": f"What is the total loss or volume associated with {status_col.replace('_', ' ')} exceptions?",
                "category": "Operations",
            })

        if not suggested_questions:
            suggested_questions = [
                {"question": "Summarize the key metrics and distribution of this dataset.", "category": "Overview"},
                {"question": "What are the most significant trends or patterns?", "category": "Trends"},
            ]

        return {
            "kpis": kpis[:5],
            "charts": charts[:3],
            "suggested_questions": suggested_questions[:6],
            "date_range": date_range_str,
        }
    finally:
        conn.close()
