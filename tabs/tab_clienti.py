# tabs/tab_clienti.py
"""
Customers tab: KPIs (Managed customers, New customers [no arrow], Retention Rate
[no arrow], Avg spend), Customers served/year, Retention per year, geo scatter
(Region/Province + Sales/Orders toggle), Top 5 Customers.
"""

import streamlit as st

import charts
import ui
from kpi import (
    calcola_variazione, render_kpi, m_fatturato, m_num_clienti, fmt_euro, fmt_int,
)


def render(ctx):
    df_ordini    = ctx['df_ordini']
    df_ordini_f  = ctx['df_ordini_f']
    df_ordini_f_no_anno = ctx['df_ordini_f_no_anno']
    df_clienti   = ctx['df_clienti']
    filters      = ctx['filters']
    anno_primo_ordine = ctx['anno_primo_ordine']
    anno_min_storico = ctx['anno_min_storico']
    anno_max_storico = ctx['anno_max_storico']

    anno_min_sel, anno_max_sel = filters['anno_range']
    nomi_clienti = df_clienti.set_index('Cd_CF')['Descrizione'].to_dict()

    # ── ROW 1 — KPIs ──────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    # 1. Managed customers (standard variation)
    var, *_ = calcola_variazione(df_ordini, filters, m_num_clienti, dataset='ordini')
    render_kpi(c1, "Managed customers", fmt_int(m_num_clienti(df_ordini_f)), var)

    # 2. New customers (NO arrow). Very first order within the selected range.
    #    If the range covers the whole history → 0 (by definition).
    n_nuovi = _clienti_nuovi(
        df_ordini_f, anno_primo_ordine, anno_min_sel, anno_max_sel,
        anno_min_storico, anno_max_storico,
    )
    render_kpi(c2, "New customers", fmt_int(n_nuovi), mostra_variazione=False,
               caption="customer's very first order in the period")

    # 3. Retention Rate (NO arrow). Avg retention of consecutive pairs in the range.
    ret = _retention_rate(df_ordini_f_no_anno, anno_min_sel, anno_max_sel)
    ret_str = "—" if ret is None else f"{ret:.1f}%"
    render_kpi(c3, "Retention Rate", ret_str, mostra_variazione=False,
               caption="average of consecutive year pairs")

    # 4. Average spend (standard variation)
    def _m_spend(df):
        n = m_num_clienti(df)
        return (m_fatturato(df) / n) if n else 0
    var, *_ = calcola_variazione(df_ordini, filters, _m_spend, dataset='ordini')
    render_kpi(c4, "Avg spend", fmt_euro(_m_spend(df_ordini_f)), var)

    st.divider()

    # ── ROW 2 — Customers served/year (2/4) + Retention per year (2/4) ────────
    col_serv, col_ret = st.columns(2)
    with col_serv:
        st.markdown("**Customers served per year**")
        ui.chart_or_message(charts.plot_clienti_per_anno(df_ordini_f), key='cl_serviti')
    with col_ret:
        st.markdown("**Retention per year**")
        ui.chart_or_message(
            charts.plot_retention_per_anno(df_ordini_f_no_anno, anno_min_sel, anno_max_sel),
            key='cl_retention',
            messaggio="At least two consecutive years in the range are needed for retention.",
        )

    st.divider()

    # ── ROW 3 — Geo scatter (2/4) + Top 5 Customers (2/4) ─────────────────────
    col_sc, col_top = st.columns(2)
    with col_sc:
        cc1, cc2 = st.columns(2)
        # if a global Region filter is active, default to Province (Region view is not useful)
        provincia_default = filters['regione'] != 'Tutte'
        with cc1:
            _, dimensione = ui.toggle_livello_geo('cl_sc_dim', default_provincia=provincia_default)
        with cc2:
            _, df_src = ui.toggle_dataset(ctx, key='cl_sc_ds')
        ui.chart_or_message(
            charts.plot_scatter_geo(df_src, dimensione=dimensione), key='cl_scatter',
        )
        st.caption(
            "Each bubble is a region (or province): the X axis shows the number of "
            "customers, the Y axis the average revenue per customer, the bubble size "
            "the total revenue. Top right: areas with few but high-value customers; "
            "bottom right: those with many customers but low average spend."
        )

    with col_top:
        ds_lbl, df_src = ui.toggle_dataset(ctx, key='cl_top_ds', label_visibility='collapsed')
        fig = charts.plot_barre_vs_totale(
            df_src, dimensione='Cd_Cliente', label_map=nomi_clienti, top_n_righe=5,
            titolo=f'Top 5 Customers — {ds_lbl}', metrica='fatturato',
            colore_primario=ui.colore_dataset(ds_lbl), nome_primario=ds_lbl,
        )
        ui.chart_or_message(fig, key='cl_top5')


# ── HELPER: new customers in the period ───────────────────────────────────────
def _clienti_nuovi(df_ordini_f, anno_primo_ordine, anno_min_sel, anno_max_sel,
                   anno_min_storico, anno_max_storico):
    """Customers whose VERY FIRST order falls within the selected range.
    If the range covers the whole history, by definition there are no 'new' ones → 0."""
    if anno_min_sel <= anno_min_storico and anno_max_sel >= anno_max_storico:
        return 0
    clienti_nel_periodo = set(df_ordini_f['Cd_Cliente'].unique())
    nuovi = anno_primo_ordine[
        anno_primo_ordine['Anno_Primo_Ordine'].between(anno_min_sel, anno_max_sel)
        & anno_primo_ordine['Cd_Cliente'].isin(clienti_nel_periodo)
    ]
    return nuovi['Cd_Cliente'].nunique()


# ── HELPER: retention rate (avg of consecutive pairs in the range) ────────────
def _retention_rate(df_no_anno, anno_min_sel, anno_max_sel):
    """Average of the retention rates over pairs of consecutive years BOTH
    inside the range. With a single year selected there is no inner pair → None."""
    clienti_per_anno = df_no_anno.groupby('Anno')['Cd_Cliente'].apply(set).to_dict()
    anni = sorted(clienti_per_anno.keys())
    tassi = []
    for i in range(1, len(anni)):
        a_prec, a_corr = anni[i - 1], anni[i]
        if not (anno_min_sel <= a_prec and a_corr <= anno_max_sel):
            continue
        prec = clienti_per_anno[a_prec]
        corr = clienti_per_anno[a_corr]
        if prec:
            tassi.append(len(prec & corr) / len(prec) * 100)
    if not tassi:
        return None
    return sum(tassi) / len(tassi)
