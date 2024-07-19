from pathlib import Path

import duckdb

import app
from app.database import props
from app.database.exifinfo import ExifInfoFormat


def create_index(database_path: str, data_format: ExifInfoFormat):
    """
    Creates a duckDb index for the database at the save path.
    Args:
        database_path: The database path
        data_format: The format of the data stored in the database

    Returns:
        True if the database was indexed, false or ValueError otherwise
    """
    # Only JSON and CSV are supported
    if not {ExifInfoFormat.JSON, ExifInfoFormat.CSV}.__contains__(data_format):
        raise ValueError(f"{data_format} is not supported for indexing")

    db_path = Path(database_path)
    db_file = db_path / props.DB_INDEX_FILE
    # Create a connection to the db file
    conn = duckdb.connect(str(db_file), read_only=False)
    try:
        insert_stmt = _get_create_statement(db_path, data_format)
        conn.execute(insert_stmt)
        conn.commit()
        conn.close()
    except Exception as e:
        app.logger.exception(e)
        return False

    return True


def _get_create_statement(db_path: Path, data_format: ExifInfoFormat):
    db_data = db_path / f"*.{data_format.name.lower()}"
    match data_format:
        case data_format.JSON:
            return (f"CREATE OR REPLACE TABLE DATABASE AS "
                    f"SELECT * FROM read_json('{db_data}', format='array', records=true, filename=true)")
        case data_format.CSV:

            return (f"CREATE OR REPLACE TABLE DATABASE AS "
                    f"SELECT * FROM read_csv('{db_data}', header=true, filename=true, "
                    f"delim='{props.EXIFTOOL_CSV_DELIMITER}')")
        case _:
            raise ValueError(f"{data_format} is not supported for indexing")




