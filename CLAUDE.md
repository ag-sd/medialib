# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MediaLib is a PyQt6 desktop application that serves as a graphical frontend to `exiftool` for viewing and managing media file metadata. It supports creating collections of file metadata from multiple directories, with SQL-like searching via MQL (MediaLib Query Language) and multi-format export.

## Development Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Run the application
python app/medialib-app.py

# Run with specific paths
python app/medialib-app.py --paths /path/to/media

# Run all tests with coverage
coverage run --omit=test_*.py -m pytest && coverage html

# Run a single test file
python -m pytest tests/collection/test_mql.py

# Run a specific test method
python -m pytest tests/collection/test_mql.py::TestMQL::test_select

# View coverage report
open htmlcov/index.html
```

## Architecture

### Layer Structure
```
┌─────────────────────────────────────┐
│  Presentation (PyQt6 Views/Models)  │  app/presentation/
├─────────────────────────────────────┤
│  Business Logic (Actions, Tasks)    │  app/actions.py, app/tasks.py
├─────────────────────────────────────┤
│  Collection & Query Engine          │  app/collection/
├─────────────────────────────────────┤
│  External (exiftool, DuckDB)        │
└─────────────────────────────────────┘
```

### Key Modules

- **`app/medialib-app.py`**: Main entry point, `MediaLibApp` extends `QMainWindow`
- **`app/collection/ds.py`**: Core `Collection` class - manages paths, caching (in-memory and on-disk), and metadata
- **`app/collection/mql.py`**: MediaLib Query Language parser using pyparsing, translates to DuckDB SQL
- **`app/collection/exifinfo.py`**: Wrapper around exiftool CLI for metadata extraction
- **`app/presentation/viewmanager.py`**: Orchestrates view switching and context menus
- **`app/presentation/models.py`**: Qt models (`TableModel`, `TreeModel`, `ColumnModel`) with builder classes
- **`app/presentation/views.py`**: View widgets (`TableView`, `ColumnView`, `SpanningTreeview`, `FileSystemTreeView`)
- **`app/tasks.py`**: `TaskManager` for background operations using QThreadPool
- **`app/plugins/framework.py`**: Plugin base classes (`SearchEventHandler`, `FileClickHandler`)

### Data Flow

1. User opens paths/collection → `Collection.create_in_memory()` or `Collection.open_db()`
2. `TaskManager` schedules background metadata fetch → `ExifInfo.extract()` calls exiftool
3. Results cached in `Collection._path_cache` (in-memory) or JSON files (on-disk)
4. `ModelBuilder` transforms data into `ViewItems` → Qt models → Views render

### Collection Types

- **IN_MEMORY**: Temporary, not persisted
- **ON_DISK**: Persistent with JSON cache files and optional DuckDB index for SQL queries

### Concurrency Pattern

- `Collection.data()` and `Collection.query()` use `ThreadPoolExecutor` for parallel path processing
- `_COLLECTION_DATA_LOCK` protects cache updates
- Main app uses `QThreadPool` + `TaskWorker` pattern; signals communicate results back to UI thread

## Dependencies

- **PyQt6**: Desktop GUI framework
- **duckdb**: In-memory/file-based SQL for collection indexing
- **pyparsing**: MQL query language grammar
- **tablib**: Multi-format data export (CSV, JSON, XLSX, ODS, HTML, etc.)

## Testing Notes

- Tests require a `QApplication` instance (initialized in `tests/__init__.py`)
- Test resources in `tests/resources/`
- CI runs pylint on Python 3.8, 3.9, 3.10
