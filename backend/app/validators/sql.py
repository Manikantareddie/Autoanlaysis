from sqlglot import exp, parse
from fastapi import HTTPException, status

ALLOWED_FUNCTIONS = {
    # Aggregates
    "SUM", "AVG", "MIN", "MAX", "COUNT", "MEDIAN", "STDDEV", "STDDEV_SAMP", "VARIANCE", "VAR_SAMP",
    "APPROX_COUNT_DISTINCT", "QUANTILE_CONT", "PERCENTILE_CONT", "PERCENTILE_DISC", "MODE",
    # Math & Numbers
    "ROUND", "ABS", "CEIL", "CEILING", "FLOOR", "POWER", "POW", "SQRT", "LOG", "LN", "EXP", "SIGN",
    "MOD", "GREATEST", "LEAST", "DIV",
    # Conditionals
    "COALESCE", "NULLIF", "IFNULL", "NVL", "CASE", "IFF", "IF",
    # Strings
    "LOWER", "UPPER", "TRIM", "LTRIM", "RTRIM", "SUBSTRING", "SUBSTR", "CONCAT", "CONCAT_WS",
    "REPLACE", "LENGTH", "LEN", "LEFT", "RIGHT", "SPLIT", "SPLIT_PART", "POSITION", "STRPOS", "INSTR", "LIKE", "ILIKE",
    # Dates & Times
    "DATE_TRUNC", "DATE_PART", "EXTRACT", "STRFTIME", "STRPTIME", "TIME_TO_STR", "STR_TO_TIME",
    "YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND", "DATEDIFF", "DATE_DIFF", "DATEADD", "DATE_ADD",
    "DATESUB", "DATE_SUB", "TIMESTAMP_TRUNC", "TIMESTAMPTRUNC", "CURRENT_DATE", "CURRENT_TIME",
    "CURRENT_TIMESTAMP", "NOW", "TODAY", "DATE", "TIME", "TIMESTAMP", "INTERVAL", "PARSE_DATE", "TO_DATE", "TO_TIMESTAMP",
    # Types & Casts
    "CAST", "TRY_CAST", "TYPEOF",
    # Window & Ranking
    "ROW_NUMBER", "ROWNUMBER", "RANK", "DENSE_RANK", "DENSERANK", "NTILE", "LAG", "LEAD", "FIRST_VALUE",
    "FIRSTVALUE", "LAST_VALUE", "LASTVALUE", "NTH_VALUE", "OVER"
}
FORBIDDEN = (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Alter, exp.Command, exp.Attach, exp.Pragma, exp.Copy)

def validate_sql(sql: str, max_rows: int = 1000) -> str:
    try:
        statements = parse(sql, read="duckdb")
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Generated SQL violates the read-only policy.") from error
    if len(statements) != 1 or not isinstance(statements[0], exp.Query):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only a single read-only SELECT query is allowed.")
    query = statements[0]
    if any(isinstance(node, FORBIDDEN) for node in query.walk()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="SQL contains a prohibited operation.")

    # Allow local CTE alias names within the query while forbidding external tables/databases
    cte_names = {cte.alias_or_name.lower() for cte in query.find_all(exp.CTE) if cte.alias_or_name}

    for table in query.find_all(exp.Table):
        tbl_name = table.name.lower()
        if (tbl_name != "dataset" and tbl_name not in cte_names) or table.db or table.catalog:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"SQL may query only the controlled dataset view (found unauthorized table: '{table.name}')."
            )

    for function in query.find_all(exp.Func):
        func_name = (
            getattr(function, "name", "")
            or (function.this.name if hasattr(function, "this") and hasattr(function.this, "name") else "")
            or function.sql_name()
        ).upper()
        type_name = type(function).__name__.upper()
        sql_name = function.sql_name().upper()

        if (
            func_name not in ALLOWED_FUNCTIONS
            and sql_name not in ALLOWED_FUNCTIONS
            and type_name not in ALLOWED_FUNCTIONS
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"SQL uses a function outside the analytical allowlist: {func_name or sql_name}"
            )

    if query.args.get("limit") is None:
        query = query.limit(max_rows)
    return query.sql(dialect="duckdb")

