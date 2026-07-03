# ui.py
"""
Reusable UI components (Streamlit).

Isolates the interface patterns repeated in every tab:
- Orders/Sales toggle that already returns the right dataframe
- Region/Province toggle
- wrapper that draws a chart or shows a substitute message if `fig is None`

This way the tabs stay pure orchestration: no `st.radio(...); df_src = ... if ...`
copy-pasted, no repeated `if fig is not None: ... else: st.info(...)`.
"""

import streamlit as st

import charts


# ── STANDARD "no data" MESSAGE ────────────────────────────────────────────────
MSG_NO_DATA = "No data with the active filters."


def toggle_dataset(ctx, key, label_visibility='visible'):
    """
    Orders/Sales radio. Returns (label, chosen_filtered_df).
    Centralizes the pattern repeated in every tab.
    """
    scelta = st.radio(
        "Dataset", ['Ordini', 'Vendite'],
        horizontal=True, key=key, label_visibility=label_visibility,
    )
    df_src = ctx['df_ordini_f'] if scelta == 'Ordini' else ctx['df_vendite_f']
    return scelta, df_src


def toggle_livello_geo(key, default_provincia=False, label_visibility='visible'):
    """
    Region/Province radio. Returns (label, column_name).
    `default_provincia=True` preselects 'Provincia' (useful when a global Region
    filter is active and the Region view would lose meaning).
    """
    scelta = st.radio(
        "Level", ['Regione', 'Provincia'],
        index=1 if default_provincia else 0,
        horizontal=True, key=key, label_visibility=label_visibility,
    )
    colonna = 'Regione' if scelta == 'Regione' else 'Cd_Provincia'
    return scelta, colonna


def chart_or_message(fig, key, messaggio=MSG_NO_DATA):
    """
    Draws `fig` if it exists, otherwise shows a substitute message.
    Replaces the `if fig is not None: st.plotly_chart(...) else: st.info(...)`
    block repeated everywhere.
    """
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, key=key)
    else:
        st.info(messaggio)


def colore_dataset(scelta):
    """Conventional color for the chosen dataset ('Ordini'/'Vendite')."""
    return charts.COLORE_ORDINI if scelta == 'Ordini' else charts.COLORE_VENDITE
