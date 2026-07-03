# tabs/tab_agenti.py
"""
Agents tab: per-agent KPIs (incl. primary agent), Agent×Year heatmap with an
Orders/Sales toggle, Top 5 Agents (double bar Orders/Sales), New/Recurring
stacked chart with % variation.
"""

import streamlit as st

import charts
import ui
from data import assegna_agente_primario
from helpers import righe_reali, aggrega_per
from kpi import calcola_variazione, render_kpi, m_fatturato, fmt_euro, fmt_int


def render(ctx):
    df_ordini    = ctx['df_ordini']
    df_ordini_f  = ctx['df_ordini_f']
    df_vendite_f = ctx['df_vendite_f']
    df_agenti    = ctx['df_agenti']
    filters      = ctx['filters']
    anno_primo_ordine = ctx['anno_primo_ordine']

    nomi_agenti = df_agenti.set_index('Cd_Agente')['Descrizione'].to_dict()

    # ── ROW 1 — KPIs ──────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    # 1. Active agents
    var, *_ = calcola_variazione(df_ordini, filters, _n_agenti_attivi, dataset='ordini')
    render_kpi(c1, "Active agents", fmt_int(_n_agenti_attivi(df_ordini_f)), var)

    # 2. Average revenue per agent
    var, *_ = calcola_variazione(df_ordini, filters, _fatturato_medio_agente, dataset='ordini')
    render_kpi(c2, "Avg revenue/agent", fmt_euro(_fatturato_medio_agente(df_ordini_f)), var)

    # 3. Average number of customers per agent (primary agent)
    var, *_ = calcola_variazione(df_ordini, filters, _clienti_medi_agente, dataset='ordini')
    render_kpi(c3, "Avg customers/agent", f"{_clienti_medi_agente(df_ordini_f):.1f}", var)

    # 4. Top agent
    s = aggrega_per(df_ordini_f, 'Cd_Agente', metrica='fatturato')
    if not s.empty:
        cd_top = s.idxmax()
        render_kpi(c4, "Top agent", nomi_agenti.get(cd_top, cd_top),
                   mostra_variazione=False, caption=f"€{s.max():,.0f} in the period")
    else:
        render_kpi(c4, "Top agent", "—", mostra_variazione=False)

    st.divider()

    # ── ROW 2 — Agent × Year heatmap (Orders/Sales toggle) ────────────────────
    st.subheader("Revenue by Agent × Year")
    st.plotly_chart(
        charts.plot_heatmap_agenti(df_ordini_f, df_agenti, df_vendite=df_vendite_f),
        use_container_width=True, key='ag_heatmap',
    )

    st.divider()

    # ── ROW 3 — Top 5 Agents (2/4) + New/Recurring (2/4) ──────────────────────
    col_top, col_disc = st.columns(2)

    with col_top:
        metrica_lbl = st.radio("Metric", ['Fatturato', 'Numero documenti'],
                               horizontal=True, key='ag_top_metrica',
                               label_visibility='collapsed')
        metrica = 'fatturato' if metrica_lbl == 'Fatturato' else 'conteggio'
        fig = charts.plot_barre_vs_totale(
            df_ordini_f, dimensione='Cd_Agente', label_map=nomi_agenti, top_n_righe=5,
            df_secondario=df_vendite_f, nome_primario='Ordini', nome_secondario='Vendite',
            titolo=f'Top 5 Agents — {metrica_lbl}', metrica=metrica,
            barre_raggruppate=True, mostra_sfondo=False,
        )
        ui.chart_or_message(fig, key='ag_top5')

    with col_disc:
        st.markdown("**New vs Recurring**")
        st.plotly_chart(
            charts.plot_nuovi_ricorrenti(df_ordini_f, anno_primo_ordine),
            use_container_width=True, key='ag_nuovi_ric',
        )
        st.caption(
            "For each year, the stacked bars show New customers (very first order "
            "ever in that year) and Recurring ones (already customers before). "
            "The line shows the percentage change in new customers compared to the previous year."
        )


# ── PER-AGENT METRICS (used as metric_fn in the standard variation) ───────────
def _n_agenti_attivi(df):
    return righe_reali(df)['Cd_Agente'].nunique()


def _fatturato_medio_agente(df):
    n = _n_agenti_attivi(df)
    return (m_fatturato(df) / n) if n else 0


def _clienti_medi_agente(df):
    n_ag = _n_agenti_attivi(df)
    if not n_ag:
        return 0
    primario = assegna_agente_primario(df)
    return primario['Cd_Cliente'].nunique() / n_ag
