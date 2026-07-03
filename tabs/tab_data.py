# tabs/tab_data.py
"""
Data tab: Orders and Sales tables ALREADY filtered by the global filters
(inherits df_ordini_f / df_vendite_f from ctx), with a selection of the columns
to display, PAGINATION and CSV export.

Why pagination: the datasets have ~800k rows. Passing the whole dataframe to
st.dataframe forces Streamlit to serialize all of it to the browser on every
rerun, slowing down the entire dashboard. Here st.dataframe receives only the
current page (a few hundred rows), so it stays instant regardless of the total
volume. The CSV export, instead, works on the FULL filtered set.
"""

import pandas as pd
import streamlit as st


# Columns shown by default (the "business" ones); the geographic ones stay
# available in the multiselect but are not preselected, to avoid crowding the view.
_DEFAULT_ORDINI = [
    'Data', 'Anno', 'Mese', 'Numero Documento', 'Tipo_Documento',
    'Cd_Cliente', 'Cd_Agente', 'Cd_Articolo', 'Descrizione_Articolo',
    'Collezione', 'Gruppo_Articolo', 'Qta Doc', 'Prezzo unitario', 'Valore',
]
_DEFAULT_VENDITE = [
    'Data', 'Anno', 'Mese', 'Numero Documento', 'Tipo_Documento',
    'Cd_Cliente', 'Cd_Agente', 'Cd_Articolo', 'Descrizione_Articolo',
    'Qta Doc', 'Valore',
]

# Options for the number of rows per page.
_PAGE_SIZES = [50, 100, 250, 500]


@st.cache_data(show_spinner=False)
def _to_csv_bytes(_df: pd.DataFrame, cache_key: tuple) -> bytes:
    """Serializes the FULL filtered set to CSV (utf-8-sig for accents in Excel).
    `_df` with an underscore: Streamlit doesn't hash it (expensive on 800k rows);
    the cache keys off `cache_key` = (name, columns, n_rows), light and stable.
    This way the CSV is rebuilt only when data/columns change, not on every rerun."""
    return _df.to_csv(index=False).encode('utf-8-sig')


def _sezione_tabella(df, nome, colonne_default, key_prefix):
    """
    Renders a section: column selection, pagination, table (current page only),
    full CSV export. `df` is already filtered by the global filters.
    """
    st.subheader(nome)

    if df.empty:
        st.info("No data with the active filters. Expand the filters in the sidebar.")
        return

    # ── Column selection (default = "business" columns present) ───────────────
    colonne_disponibili = list(df.columns)
    default_presenti = [c for c in colonne_default if c in colonne_disponibili]
    colonne_scelte = st.multiselect(
        "Columns to display", colonne_disponibili, default=default_presenti,
        key=f'{key_prefix}_cols',
        help="The selection also applies to the export.",
    )
    if not colonne_scelte:
        st.warning("Select at least one column.")
        return

    df_view = df[colonne_scelte]
    n_righe = len(df_view)

    # ── Pagination controls ────────────────────────────────────────────────────
    cc1, cc2 = st.columns([1, 3])
    with cc1:
        page_size = st.selectbox(
            "Rows per page", _PAGE_SIZES, index=1, key=f'{key_prefix}_psize',
        )
    n_pagine = max((n_righe - 1) // page_size + 1, 1)
    with cc2:
        # Slider only if more than one page is needed (avoids a useless widget).
        if n_pagine > 1:
            pagina = st.slider(
                "Page", 1, n_pagine, 1, key=f'{key_prefix}_page',
            )
        else:
            pagina = 1

    inizio = (pagina - 1) * page_size
    fine = min(inizio + page_size, n_righe)

    st.caption(
        f"{n_righe:,} total rows × {len(colonne_scelte)} columns — "
        f"page {pagina}/{n_pagine} (rows {inizio + 1:,}–{fine:,})"
    )

    # Only the current slice reaches st.dataframe: cost independent of the volume.
    st.dataframe(
        df_view.iloc[inizio:fine],
        use_container_width=True, hide_index=True, height=430,
    )

    # ── CSV export (FULL filtered set, not just the page) ─────────────────────
    st.download_button(
        "⬇️ Download CSV (all filtered rows)",
        data=_to_csv_bytes(df_view, (nome, tuple(colonne_scelte), n_righe)),
        file_name=f'{nome.lower()}_filtrati.csv',
        mime='text/csv',
        use_container_width=True,
        key=f'{key_prefix}_csv',
    )


def render(ctx):
    df_ordini_f  = ctx['df_ordini_f']
    df_vendite_f = ctx['df_vendite_f']

    st.markdown(
        "Tables of the data **already filtered** by the controls in the sidebar. "
        "Choose the columns, browse the pages and export the full view to CSV."
    )

    sub_ord, sub_ven = st.tabs(["📦 Orders", "🧾 Sales"])
    with sub_ord:
        _sezione_tabella(df_ordini_f, 'Ordini', _DEFAULT_ORDINI, 'data_ord')
    with sub_ven:
        _sezione_tabella(df_vendite_f, 'Vendite', _DEFAULT_VENDITE, 'data_ven')
