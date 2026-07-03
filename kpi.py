# kpi.py
"""
KPI metric computation, standard variation logic (a single function)
and rendering of the KPI box (title + number + colored arrow).
"""

import streamlit as st

from config import VARIAZIONE
from data import applica_filtri
from helpers import somma_fatturato, conta_documenti


# ── STANDARD VARIATION LOGIC ──────────────────────────────────────────────────
def calcola_variazione(df_completo, filters, metric_fn, dataset='ordini'):
    """
    Standard variation used by ALL KPIs with an arrow.

    Compares:
      yearly_avg_period  = metric(selected period) / n_years_period
      yearly_avg_history = metric(entire history)  / n_years_history
    at equal Agent/Region/Group filters (only the Year dimension changes).

    `metric_fn(df_filtrato)` → scalar value of the metric.

    Returns: (variazione_pct: float|None, n_anni_periodo, n_anni_storico).
    variazione_pct = None if not computable (null history).
    """
    anno_min_sel, anno_max_sel = filters['anno_range']
    anni_disponibili = sorted(df_completo['Anno'].dropna().unique())
    if not anni_disponibili:
        return None, 0, 0
    anno_min_storico, anno_max_storico = int(anni_disponibili[0]), int(anni_disponibili[-1])

    # selected period (current filters, already with Year)
    df_periodo = applica_filtri(df_completo, filters, dataset=dataset)
    n_anni_periodo = max(anno_max_sel - anno_min_sel + 1, 1)
    val_periodo = metric_fn(df_periodo)

    # full history, same filters except Year
    filters_storico = {**filters, 'anno_range': (anno_min_storico, anno_max_storico)}
    df_storico = applica_filtri(df_completo, filters_storico, dataset=dataset)
    n_anni_storico = max(anno_max_storico - anno_min_storico + 1, 1)
    val_storico = metric_fn(df_storico)

    media_periodo = val_periodo / n_anni_periodo
    media_storico = val_storico / n_anni_storico

    if media_storico == 0:
        return None, n_anni_periodo, n_anni_storico

    variazione_pct = (media_periodo - media_storico) / media_storico * 100
    return variazione_pct, n_anni_periodo, n_anni_storico


# ── KPI BOX RENDERING ─────────────────────────────────────────────────────────
def _delta_html(variazione_pct, mostra_variazione, caption):
    """Builds the HTML fragment below the value (colored arrow or caption)."""
    if mostra_variazione and variazione_pct is not None:
        if variazione_pct > 0.05:
            colore, freccia = VARIAZIONE['su'], '↑'
        elif variazione_pct < -0.05:
            colore, freccia = VARIAZIONE['giu'], '↓'
        else:
            colore, freccia = VARIAZIONE['invariato'], '→'
        return (
            f"<div style='color:{colore};font-size:0.875rem;font-weight:400;"
            f"margin-top:2px;display:flex;align-items:center;gap:3px'>"
            f"<span style='font-size:0.9rem'>{freccia}</span>"
            f"{variazione_pct:+.1f}% vs historical average</div>"
        )
    if mostra_variazione and variazione_pct is None:
        return (
            f"<div style='color:{VARIAZIONE['invariato']};font-size:0.875rem;"
            f"margin-top:2px'>→ n/a</div>"
        )
    testo = caption or ""
    return (
        f"<div style='color:var(--secondary-text-color, #8B8880);"
        f"font-size:0.78rem;margin-top:2px;font-style:italic'>{testo}</div>"
    )


def render_kpi(col, titolo, valore_str, variazione_pct=None,
               mostra_variazione=True, caption=None):
    """
    Draws a KPI box inside a Streamlit column, with a look consistent with the
    native st.metric but with 3 color states (green/red/gray) and support for a
    caption instead of the arrow.
    """
    delta_html = _delta_html(variazione_pct, mostra_variazione, caption)
    col.markdown(
        f"""
        <div style='padding:1rem 1.1rem;border:1px solid rgba(128,128,128,0.25);
                    border-radius:0.5rem;background:var(--secondary-background-color, transparent);
                    height:100%'>
            <div style='color:var(--secondary-text-color, #8B8880);font-size:0.875rem;
                        font-weight:400;line-height:1.2'>{titolo}</div>
            <div class="kpi-valore" style='font-size:2rem;font-weight:600;
                        margin-top:0.15rem;line-height:1.2'>{valore_str}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_lista_box(items):
    """
    Draws a Top-N list as stacked boxes, consistent with the KPI style:
    big name (visual priority), revenue as a subtitle.
    `items`: list of tuples (rank:int, nome:str, valore_str:str).
    """
    for rank, nome, valore_str in items:
        st.markdown(
            f"""
            <div style='padding:0.7rem 0.9rem;margin-bottom:0.5rem;
                        border:1px solid rgba(128,128,128,0.25);border-radius:0.5rem;
                        background:var(--secondary-background-color, transparent);
                        display:flex;align-items:baseline;gap:0.6rem'>
                <div style='color:var(--secondary-text-color, #8B8880);
                            font-size:1.1rem;font-weight:600;flex-shrink:0'>{rank}</div>
                <div style='min-width:0'>
                    <div class="kpi-valore" style='font-size:1.05rem;font-weight:600;
                                line-height:1.25;word-break:break-word'>{nome}</div>
                    <div style='color:var(--secondary-text-color, #8B8880);
                                font-size:0.85rem;margin-top:2px'>{valore_str}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── ELEMENTARY METRICS (reusable as metric_fn) ────────────────────────────────
# They delegate to the shared helpers: a single source of truth on the definition.
def m_fatturato(df):
    return somma_fatturato(df)


def m_num_documenti(df):
    return conta_documenti(df)


def m_num_clienti(df):
    return df['Cd_Cliente'].nunique()


# ── FORMATTING HELPERS ────────────────────────────────────────────────────────
def fmt_euro(x):
    return f"€ {x:,.0f}"


def fmt_int(x):
    return f"{int(x):,}"
