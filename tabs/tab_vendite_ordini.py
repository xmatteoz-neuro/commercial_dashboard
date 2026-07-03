# tabs/tab_vendite_ordini.py
"""
Sales/Orders tab (Italy): broken-down KPIs, shared revenue, Italy map with a
dataset toggle, Top 5 Regions/Provinces with a Sales/Orders toggle.
"""

import streamlit as st

import charts
import ui
from kpi import (
    calcola_variazione, render_kpi,
    m_fatturato, m_num_documenti, fmt_euro, fmt_int,
)


def render(ctx):
    df_ordini    = ctx['df_ordini']
    df_vendite   = ctx['df_vendite']
    df_ordini_f  = ctx['df_ordini_f']
    df_vendite_f = ctx['df_vendite_f']
    geo          = ctx['geo']
    filters      = ctx['filters']

    # ── ROW 1 — KPIs (Orders vs Sales) ────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    var, *_ = calcola_variazione(df_ordini, filters, m_fatturato, dataset='ordini')
    render_kpi(c1, "Orders revenue", fmt_euro(m_fatturato(df_ordini_f)), var)

    var, *_ = calcola_variazione(df_vendite, filters, m_fatturato, dataset='vendite')
    render_kpi(c2, "Sales revenue (across the whole catalog)", fmt_euro(m_fatturato(df_vendite_f)), var)

    var, *_ = calcola_variazione(df_ordini, filters, m_num_documenti, dataset='ordini')
    render_kpi(c3, "Number of Orders", fmt_int(m_num_documenti(df_ordini_f)), var)

    var, *_ = calcola_variazione(df_vendite, filters, m_num_documenti, dataset='vendite')
    render_kpi(c4, "Number of Sales (across the whole catalog)", fmt_int(m_num_documenti(df_vendite_f)), var)

    st.divider()

    # ── ROW 2 — Revenue (3/4) + Italy map with toggle (1/4) ───────────────────
    col_rev, col_map = st.columns([3, 1])
    with col_rev:
        st.plotly_chart(charts.plot_revenue(df_ordini_f, df_vendite_f),
                        use_container_width=True, key='vo_revenue')
        if filters['gruppo'] != 'Tutti':
            st.caption("Note: the Product Group filter does not apply to the Sales series.")
    with col_map:
        st.markdown("**Italy map**")
        if filters['regione'] != 'Tutte':
            # Region filter active: we only show the Dataset toggle and force the
            # province detail (the Region view would have a single area).
            ds_lbl, df_map = ui.toggle_dataset(ctx, key='vo_map_ds')
            livello = 'provincia'
            st.caption(f"Province detail — {filters['regione']}")
        else:
            mc1, mc2 = st.columns(2)
            with mc1:
                livello_lbl, _ = ui.toggle_livello_geo('vo_map_livello')
            with mc2:
                ds_lbl, df_map = ui.toggle_dataset(ctx, key='vo_map_ds')
            livello = 'regione' if livello_lbl == 'Regione' else 'provincia'

        colore = 'ordini' if ds_lbl == 'Ordini' else 'vendite'
        ui.chart_or_message(
            charts.plot_mappa_italia(
                df_map, geo, livello=livello, colore=colore,
                solo_dati=(filters['regione'] != 'Tutte'),
            ),
            key='vo_mappa',
        )

    st.divider()

    # ── ROW 3 — Top 5 Regions (2/4) + Top 5 Provinces (2/4) ───────────────────
    col_reg, col_prov = st.columns(2)
    with col_reg:
        ds, df_src = ui.toggle_dataset(ctx, key='top_reg_ds', label_visibility='collapsed')
        fig = charts.plot_barre_vs_totale(
            df_src, dimensione='Regione', top_n_righe=5,
            titolo=f'Top 5 Regions — {ds}', metrica='fatturato',
            colore_primario=ui.colore_dataset(ds), nome_primario=ds,
        )
        ui.chart_or_message(fig, key='vo_top_reg')

    with col_prov:
        ds, df_src = ui.toggle_dataset(ctx, key='top_prov_ds', label_visibility='collapsed')
        fig = charts.plot_barre_vs_totale(
            df_src, dimensione='Cd_Provincia', top_n_righe=5,
            titolo=f'Top 5 Provinces — {ds}', metrica='fatturato',
            colore_primario=ui.colore_dataset(ds), nome_primario=ds,
        )
        ui.chart_or_message(fig, key='vo_top_prov')
