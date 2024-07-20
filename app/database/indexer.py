from pathlib import Path

import duckdb

import app
from app.database import props


def create_index(database_path: str):
    """
    Creates a duckDb index for the database at the save path.
    Args:
        database_path: The database path

    Returns:
        True if the database was indexed, false or ValueError otherwise
    """

    db_path = Path(database_path)
    db_file = db_path / props.DB_INDEX_FILE
    # Create a connection to the db file
    conn = duckdb.connect(str(db_file), read_only=False)
    try:
        insert_stmt = _get_create_statement(db_path)
        conn.execute(insert_stmt)
        conn.commit()
        conn.close()
    except Exception as e:
        app.logger.exception(e)
        return False

    return True


def _get_create_statement(db_path: Path):
    db_data = db_path / "*.json"
    return (f"CREATE OR REPLACE TABLE DATABASE AS "
            f"SELECT * FROM read_json('{db_data}', format='array', records=true, filename=true)")



