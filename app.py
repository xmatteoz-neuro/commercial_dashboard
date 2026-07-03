# app.py
"""
Streamlit entry point. Loads the data, builds the sidebar, computes the
filtered dataframes ONCE (standard and year-less) and routes the tabs passing a
single context dict. Tabs orchestrate, they don't compute.
"""

import streamlit as st
from pathlib import Path
from data import (
    load_data, load_geodata, applica_filtri, filtri_senza_anno,
    calcola_anno_primo_ordine,
)
from tabs import tab_overview, tab_vendite_ordini, tab_agenti, tab_clienti, tab_data

LOGO_PATH = Path(__file__).resolve().parent / "asset" / "logo.png"

st.set_page_config(
    page_title="Sales Dashboard",
    layout="wide",
    page_icon="🪶",
    initial_sidebar_state="expanded",
)

# CSS: the KPI value turns white in dark mode (the rest uses theme variables).
_KPI_CSS = """
<style>
.kpi-valore { color: #131414; }
@media (prefers-color-scheme: dark) {
    .kpi-valore { color: #FFFFFF; }
}
</style>
"""


# ── SIDEBAR / FILTERS ─────────────────────────────────────────────────────────
def sidebar_controls(df_ordini, df_agenti) -> dict:
    with st.sidebar:
        st.header("Filters")

        anno_min = int(df_ordini['Anno'].min())
        anno_max = int(df_ordini['Anno'].max())
        anno_range = st.slider("Year Range", anno_min, anno_max, (anno_min, anno_max))

        # Agents: shows "code — name", but the selected value is the code.
        agenti_map = (df_agenti.dropna(subset=['Cd_Agente'])
                      .set_index('Cd_Agente')['Descrizione'].to_dict())
        opzioni_agente = [f"{cd} — {nome}" for cd, nome in sorted(agenti_map.items())]
        sel = st.multiselect("Agent", opzioni_agente, help="Empty = all agents")
        agenti = [s.split(' — ')[0] for s in sel]  # list of codes; [] = all

        # ── Region: CASCADING filters (agent drives) ──────────────────────────
        # If agents are selected, Region can only take the values where THOSE
        # agents have worked (derived from the data). Empty = all.
        if agenti:
            regioni_disp = sorted(
                df_ordini[df_ordini['Cd_Agente'].isin(agenti)]['Regione']
                .dropna().unique().tolist()
            )
        else:
            regioni_disp = sorted(df_ordini['Regione'].dropna().unique().tolist())
        opzioni_regione = ['Tutte'] + regioni_disp

        # Sanitize the saved selection BEFORE redrawing the widget: if the
        # region previously chosen is no longer compatible with the current
        # agents, we reset it to 'Tutte'. Avoids the phantom-value and the
        # KeyError known to occur when a selectbox's options change dynamically.
        if st.session_state.get('flt_regione') not in opzioni_regione:
            st.session_state['flt_regione'] = 'Tutte'

        regione = st.selectbox("Region", opzioni_regione, key='flt_regione')
        if agenti and len(regioni_disp) < len(df_ordini['Regione'].dropna().unique()):
            st.caption("Regions limited to the territory of the selected agents.")

        gruppi = ['Tutti'] + sorted(df_ordini['Gruppo_Articolo'].dropna().unique().tolist())
        gruppo = st.selectbox("Product Group", gruppi)

        st.divider()
        st.caption(f"Total orders (rows): {len(df_ordini):,}")

    return dict(anno_range=anno_range, agente=agenti, regione=regione, gruppo=gruppo)


def main():

    st.title("Sales Dashboard")
    st.caption("Orders and Sales analysis, Agents and Customers monitoring.")

    df_agenti, df_clienti, df_ordini, df_vendite = load_data()
    geo = load_geodata()

    filters = sidebar_controls(df_ordini, df_agenti)

    # Standard filtered dataframes (computed ONCE).
    df_ordini_f = applica_filtri(df_ordini, filters, dataset='ordini')
    df_vendite_f = applica_filtri(df_vendite, filters, dataset='vendite')

    # Year-less filtered dataframe (for Retention).
    anno_min_storico = int(df_ordini['Anno'].min())
    anno_max_storico = int(df_ordini['Anno'].max())
    df_ordini_f_no_anno = applica_filtri(
        df_ordini, filtri_senza_anno(filters, anno_min_storico, anno_max_storico),
        dataset='ordini',
    )

    # Shared logic computed once on the full dataset.
    anno_primo_ordine = calcola_anno_primo_ordine(df_ordini)

    if df_ordini_f.empty:
        st.warning("No data is available with selected filtered. Expand filters to see data.")
        st.stop()

    # Single context passed to every tab.
    ctx = dict(
        df_agenti=df_agenti, df_clienti=df_clienti,
        df_ordini=df_ordini, df_vendite=df_vendite,
        df_ordini_f=df_ordini_f, df_vendite_f=df_vendite_f,
        df_ordini_f_no_anno=df_ordini_f_no_anno,
        geo=geo, filters=filters,
        anno_primo_ordine=anno_primo_ordine,
        anno_min_storico=anno_min_storico, anno_max_storico=anno_max_storico,
    )

    tab_ov, tab_vo, tab_ag, tab_cli, tab_dt = st.tabs(
        ["📊 Overview", "📦 Sales / Orders", "🧑‍💼 Agents", "👥 Customers", "🗂️ Data"]
    )
    with tab_ov:
        tab_overview.render(ctx)
    with tab_vo:
        tab_vendite_ordini.render(ctx)
    with tab_ag:
        tab_agenti.render(ctx)
    with tab_cli:
        tab_clienti.render(ctx)
    with tab_dt:
        tab_data.render(ctx)


if __name__ == "__main__":
    main()
