# tabs/tab_overview.py
"""
Overview tab: orchestrates the layout, does not compute.
Calls kpi.py, charts.py and the shared components in ui.py.
"""

import streamlit as st

import charts
import ui
from helpers import aggrega_per, top_n
from kpi import (
    calcola_variazione, render_kpi, render_lista_box,
    m_fatturato, m_num_documenti, m_num_clienti, fmt_euro, fmt_int,
)


def render(ctx):
    df_ordini    = ctx['df_ordini']
    df_vendite   = ctx['df_vendite']
    df_ordini_f  = ctx['df_ordini_f']
    df_vendite_f = ctx['df_vendite_f']
    df_agenti    = ctx['df_agenti']
    geo          = ctx['geo']
    filters      = ctx['filters']

    # ── ROW 1 — KPIs ──────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    var, *_ = calcola_variazione(df_vendite, filters, m_fatturato, dataset='vendite')
    render_kpi(c1, "Total revenue (across the whole catalog)", fmt_euro(m_fatturato(df_vendite_f)), var)

    var, *_ = calcola_variazione(df_ordini, filters, m_num_documenti, dataset='ordini')
    render_kpi(c2, "Number of orders", fmt_int(m_num_documenti(df_ordini_f)), var)

    var, *_ = calcola_variazione(df_ordini, filters, m_num_clienti, dataset='ordini')
    render_kpi(c3, "Active customers", fmt_int(m_num_clienti(df_ordini_f)), var)

    coll = _collezione_top(df_ordini_f)
    render_kpi(c4, "Most purchased collection", coll, mostra_variazione=False,
               caption="product group with the highest revenue")

    st.divider()

    # ── ROW 2 — Revenue (3/4) + Top Agents (1/4) ──────────────────────────────
    col_rev, col_top = st.columns([3, 1])
    with col_rev:
        st.plotly_chart(charts.plot_revenue(df_ordini_f, df_vendite_f),
                        use_container_width=True, key='ov_revenue')
        if filters['gruppo'] != 'Tutti':
            st.caption("Note: the Product Group filter does not apply to the Sales series "
                       "(the column does not exist in df_vendite).")
    with col_top:
        st.markdown("**Top 5 Agents**")
        if filters['agente']:
            st.info("Agent filter active: remove it to see the full ranking.")
        else:
            _lista_top(df_ordini_f, 'Cd_Agente',
                       label_map=_nomi(df_agenti))

    st.divider()

    # ── ROW 3 — Italy map (1/4) + World map (2/4) + Top collections (1/4) ──────
    col_ita, col_mondo, col_coll = st.columns([1, 2, 1])
    with col_ita:
        st.markdown("**Italy map**")
        if filters['regione'] != 'Tutte':
            # Region filter active: the "Region" view would show a single area,
            # so we go straight to the province detail (no toggle).
            livello = 'provincia'
            st.caption(f"Province detail — {filters['regione']}")
        else:
            livello_lbl, _ = ui.toggle_livello_geo(
                'ov_map_livello', label_visibility='collapsed',
            )
            livello = 'regione' if livello_lbl == 'Regione' else 'provincia'
        ui.chart_or_message(
            charts.plot_mappa_italia(
                df_ordini_f, geo, livello=livello, colore='ordini',
                solo_dati=(filters['regione'] != 'Tutte'),
            ),
            key='ov_mappa_ita',
        )

    with col_mondo:
        if filters['regione'] != 'Tutte':
            st.info("Region filter active: World map not available.")
        else:
            ui.chart_or_message(charts.plot_mappa_mondo(df_vendite_f),
                                key='ov_mappa_mondo',
                                messaggio="No foreign data with the active filters.")
    with col_coll:
        st.markdown("**Top 5 Collections**")
        if 'Gruppo_Articolo' not in df_ordini_f.columns:
            st.caption("—")
        else:
            _lista_top(df_ordini_f, 'Gruppo_Articolo')


# ── LOCAL HELPERS (UI composition only: no heavy computation) ─────────────────
def _nomi(df_agenti):
    return df_agenti.set_index('Cd_Agente')['Descrizione'].to_dict()


def _collezione_top(df):
    if 'Gruppo_Articolo' not in df.columns:
        return "—"
    s = aggrega_per(df, 'Gruppo_Articolo', metrica='fatturato')
    return s.idxmax() if not s.empty else "—"


def _lista_top(df, dimensione, label_map=None, n=5):
    """Renders a Top-N as stacked boxes (KPI style), using the shared
    aggregation helpers (no repeated groupby here)."""
    s = top_n(aggrega_per(df, dimensione, metrica='fatturato'), n)
    items = []
    for i, (chiave, val) in enumerate(s.items(), 1):
        etichetta = label_map.get(chiave, chiave) if label_map else chiave
        items.append((i, etichetta, f"€{val:,.0f}"))
    render_lista_box(items)
