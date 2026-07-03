# helpers.py
"""
PURE, reusable data logic (no dependency on Streamlit or Plotly).

Collects the micro-patterns that used to be copy-pasted across every module:
- "real rows" filter (Value >= threshold)
- revenue / document count aggregations by dimension
- Top-N on a series

Keeping this logic in one place removes dozens of repetitions and makes it
trivial to change the threshold or the definition of "document" in the future.
"""

import pandas as pd

from config import VALORE_MINIMO, COL_VALORE, COL_DOC


def righe_reali(df: pd.DataFrame) -> pd.DataFrame:
    """Subset of rows with Value >= threshold (discards adjustments/zeros).
    Replaces the repeated pattern `df[df['Valore'] >= 1]`."""
    return df[df[COL_VALORE] >= VALORE_MINIMO]


def somma_fatturato(df: pd.DataFrame) -> float:
    """Total revenue over the real rows."""
    return righe_reali(df)[COL_VALORE].sum()


def conta_documenti(df: pd.DataFrame) -> int:
    """Number of unique documents (Numero Documento). Does not filter by Value:
    a document exists regardless of its amount."""
    return df[COL_DOC].nunique()


def aggrega_per(df: pd.DataFrame, dimensione: str, metrica: str = 'fatturato') -> pd.Series:
    """
    Aggregates the real rows by `dimensione`.
    - metrica='fatturato' → sum of Value
    - metrica='conteggio' → unique documents
    Returns a Series indexed on the dimension.
    """
    d = righe_reali(df)
    if metrica == 'conteggio':
        return d.groupby(dimensione)[COL_DOC].nunique()
    return d.groupby(dimensione)[COL_VALORE].sum()


def top_n(serie: pd.Series, n: int = 5) -> pd.Series:
    """First `n` entries of a Series sorted by descending value."""
    return serie.sort_values(ascending=False).head(n)
