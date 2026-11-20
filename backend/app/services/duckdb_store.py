from pathlib import Path

import duckdb


def create_dataset_database(csv_path: Path, output_path: Path) -> None:
    """Register the controlled CSV as a view for later restricted SQL execution with strict memory bounding."""
    connection = duckdb.connect(str(output_path), config={"threads": "1", "memory_limit": "128MB"})
    try:
        escaped_path = str(csv_path).replace("'", "''")
        connection.execute("CREATE VIEW dataset AS SELECT * FROM read_csv_auto('" + escaped_path + "', header=true)")
    finally:
        connection.close()

