"""
Dataset file loader.

Converts uploaded files into pandas DataFrames.
Supports: CSV, Excel (.xlsx/.xls), JSON, Parquet, PDF (tabular extraction).

Design principles:
- All functions are synchronous (run in threadpool via asyncio.to_thread)
- No side effects — pure input → output
- Raises typed exceptions so the service layer can handle them cleanly
- Memory-efficient for large files (chunked reading where possible)
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.exceptions import DataProcessingError, UnsupportedFileTypeError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Max rows to load for safety (override in config if needed)
MAX_ROWS = 1_000_000


def load_from_bytes(data: bytes, filename: str) -> pd.DataFrame:
    """
    Load a file from raw bytes into a pandas DataFrame.

    Args:
        data:     Raw file bytes
        filename: Original filename (used to detect format)

    Returns:
        Loaded DataFrame with cleaned column names

    Raises:
        UnsupportedFileTypeError: Extension not supported
        DataProcessingError:      File could not be parsed
    """
    ext = Path(filename).suffix.lower().lstrip(".")

    loaders = {
        "csv":     _load_csv,
        "tsv":     _load_tsv,
        "xlsx":    _load_excel,
        "xls":     _load_excel,
        "json":    _load_json,
        "parquet": _load_parquet,
        "pdf":     _load_pdf,
    }

    if ext not in loaders:
        raise UnsupportedFileTypeError(
            filename=filename,
            allowed=list(loaders.keys()),
        )

    try:
        df = loaders[ext](data)
    except (UnsupportedFileTypeError, DataProcessingError):
        raise
    except Exception as exc:
        raise DataProcessingError(
            message=f"Failed to parse '{filename}': {exc}"
        ) from exc

    df = _sanitize_dataframe(df)

    logger.info(
        "dataset_loaded",
        filename=filename,
        rows=len(df),
        columns=len(df.columns),
    )

    if len(df) > MAX_ROWS:
        logger.warning(
            "dataset_truncated",
            original_rows=len(df),
            truncated_to=MAX_ROWS,
        )
        df = df.head(MAX_ROWS)

    return df


def _load_csv(data: bytes) -> pd.DataFrame:
    """Load CSV with encoding detection fallback."""
    buf = io.BytesIO(data)
    # Try UTF-8 first, fall back to latin-1 for legacy files
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            buf.seek(0)
            return pd.read_csv(
                buf,
                encoding=encoding,
                low_memory=False,
                on_bad_lines="warn",
            )
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    raise DataProcessingError(message="Could not decode CSV with any supported encoding.")


def _load_tsv(data: bytes) -> pd.DataFrame:
    buf = io.BytesIO(data)
    return pd.read_csv(buf, sep="\t", low_memory=False, on_bad_lines="warn")


def _load_excel(data: bytes) -> pd.DataFrame:
    buf = io.BytesIO(data)
    # Read the first sheet by default
    excel = pd.ExcelFile(buf, engine="openpyxl")
    sheet = excel.sheet_names[0]
    if len(excel.sheet_names) > 1:
        logger.info(
            "excel_multiple_sheets",
            sheets=excel.sheet_names,
            using=sheet,
        )
    return pd.read_excel(buf, sheet_name=sheet, engine="openpyxl")


def _load_json(data: bytes) -> pd.DataFrame:
    buf = io.BytesIO(data)
    try:
        # Try records orientation first (most common)
        return pd.read_json(buf, orient="records")
    except ValueError:
        buf.seek(0)
        # Fall back to pandas default JSON parsing
        return pd.read_json(buf)


def _load_parquet(data: bytes) -> pd.DataFrame:
    buf = io.BytesIO(data)
    return pd.read_parquet(buf, engine="pyarrow")


def _load_pdf(data: bytes) -> pd.DataFrame:
    """
    Extract tabular data from a PDF.
    Requires: pdfplumber (pip install pdfplumber)
    Falls back gracefully if no tables are found.
    """
    try:
        import pdfplumber
    except ImportError:
        raise DataProcessingError(
            message="PDF parsing requires 'pdfplumber'. Install it via pip."
        )

    buf = io.BytesIO(data)
    all_tables: list[pd.DataFrame] = []

    with pdfplumber.open(buf) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                headers = table[0]
                rows = table[1:]
                if headers and rows:
                    df = pd.DataFrame(rows, columns=headers)
                    all_tables.append(df)

    if not all_tables:
        raise DataProcessingError(
            message="No tabular data found in PDF. "
                    "Only PDFs with formatted tables are supported."
        )

    return pd.concat(all_tables, ignore_index=True)


def _sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply consistent cleanup to any loaded DataFrame:
    - Strip whitespace from column names
    - Remove fully empty rows/columns
    - Reset index
    """
    # Clean column names
    df.columns = [
        str(col).strip().replace("\n", " ").replace("\r", "")
        for col in df.columns
    ]

    # Deduplicate column names (append _2, _3 etc.)
    seen: dict[str, int] = {}
    new_cols = []
    for col in df.columns:
        if col in seen:
            seen[col] += 1
            new_cols.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 1
            new_cols.append(col)
    df.columns = new_cols

    # Drop completely empty rows and columns
    df = df.dropna(how="all").dropna(axis=1, how="all")

    return df.reset_index(drop=True)


def get_dataframe_memory_mb(df: pd.DataFrame) -> float:
    """Return approximate memory usage of a DataFrame in MB."""
    return df.memory_usage(deep=True).sum() / (1024 * 1024)
