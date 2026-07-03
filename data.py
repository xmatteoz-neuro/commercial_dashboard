# data.py
"""
Data loading, cleaning/enrichment and filtering.

All cleaning happens ONCE in load_data() (cached);
applica_filtri() is the single place where the global filters are applied.
The data logic shared by multiple tabs (first order, primary agent) lives here.
"""

from pathlib import Path

import pandas as pd
import requests
import streamlit as st

from config import GEOJSON_REGIONI_URL, GEOJSON_PROVINCE_URL

DATA_DIR = Path(__file__).resolve().parent / "dati"

# Geographic columns carried from df_clienti into the transactional datasets.
_GEO_COLS = ['Cd_CF', 'Cd_Provincia', 'Cd_Nazione', 'Regione']


# ── GEOGRAPHIC DICTIONARIES ───────────────────────────────────────────────────
provincia_regione = {
    'AG': 'Sicilia', 'CL': 'Sicilia', 'CT': 'Sicilia', 'EN': 'Sicilia',
    'ME': 'Sicilia', 'PA': 'Sicilia', 'RG': 'Sicilia', 'SR': 'Sicilia', 'TP': 'Sicilia',
    'AV': 'Campania', 'BN': 'Campania', 'CE': 'Campania', 'NA': 'Campania', 'SA': 'Campania',
    'BA': 'Puglia', 'BT': 'Puglia', 'BR': 'Puglia', 'FG': 'Puglia', 'LE': 'Puglia', 'TA': 'Puglia',
    'CZ': 'Calabria', 'CS': 'Calabria', 'KR': 'Calabria', 'RC': 'Calabria', 'VV': 'Calabria',
    'MT': 'Basilicata', 'PZ': 'Basilicata',
    'CB': 'Molise', 'IS': 'Molise',
    'CH': 'Abruzzo', 'AQ': 'Abruzzo', 'PE': 'Abruzzo', 'TE': 'Abruzzo',
    'FR': 'Lazio', 'LT': 'Lazio', 'RI': 'Lazio', 'RM': 'Lazio', 'VT': 'Lazio',
    'AN': 'Marche', 'AP': 'Marche', 'FM': 'Marche', 'MC': 'Marche', 'PU': 'Marche',
    'PG': 'Umbria', 'TR': 'Umbria',
    'AR': 'Toscana', 'FI': 'Toscana', 'GR': 'Toscana', 'LI': 'Toscana', 'LU': 'Toscana',
    'MS': 'Toscana', 'PI': 'Toscana', 'PT': 'Toscana', 'PO': 'Toscana', 'SI': 'Toscana',
    'GE': 'Liguria', 'IM': 'Liguria', 'SP': 'Liguria', 'SV': 'Liguria',
    'BO': 'Emilia-Romagna', 'FE': 'Emilia-Romagna', 'FC': 'Emilia-Romagna', 'MO': 'Emilia-Romagna',
    'PR': 'Emilia-Romagna', 'PC': 'Emilia-Romagna', 'RA': 'Emilia-Romagna', 'RE': 'Emilia-Romagna', 'RN': 'Emilia-Romagna',
    'BZ': 'Trentino-Alto Adige/Südtirol', 'TN': 'Trentino-Alto Adige/Südtirol',
    'BL': 'Veneto', 'PD': 'Veneto', 'RO': 'Veneto', 'TV': 'Veneto',
    'VE': 'Veneto', 'VR': 'Veneto', 'VI': 'Veneto',
    'GO': 'Friuli-Venezia Giulia', 'PN': 'Friuli-Venezia Giulia', 'TS': 'Friuli-Venezia Giulia', 'UD': 'Friuli-Venezia Giulia',
    'BG': 'Lombardia', 'BS': 'Lombardia', 'CO': 'Lombardia', 'CR': 'Lombardia',
    'LC': 'Lombardia', 'LO': 'Lombardia', 'MB': 'Lombardia', 'MI': 'Lombardia',
    'MN': 'Lombardia', 'PV': 'Lombardia', 'SO': 'Lombardia', 'VA': 'Lombardia',
    'AL': 'Piemonte', 'AT': 'Piemonte', 'BI': 'Piemonte', 'CN': 'Piemonte',
    'NO': 'Piemonte', 'TO': 'Piemonte', 'VB': 'Piemonte', 'VC': 'Piemonte',
    'AO': "Valle d'Aosta/Vallée d'Aoste",
    'CA': 'Sardegna', 'CI': 'Sardegna', 'NU': 'Sardegna', 'OG': 'Sardegna',
    'OR': 'Sardegna', 'OT': 'Sardegna', 'SS': 'Sardegna', 'VS': 'Sardegna',
}

iso2_to_iso3 = {
    'IT': 'ITA', 'ES': 'ESP', 'PT': 'PRT', 'BE': 'BEL', 'NL': 'NLD',
    'FR': 'FRA', 'LU': 'LUX', 'RU': 'RUS', 'CH': 'CHE', 'GR': 'GRC',
    'US': 'USA', 'MT': 'MLT', 'SM': 'SMR', 'UA': 'UKR', 'LB': 'LBN',
    'PL': 'POL', 'HU': 'HUN', 'GB': 'GBR', 'DE': 'DEU', 'CN': 'CHN',
    'VN': 'VNM', 'AT': 'AUT', 'HK': 'HKG', 'TR': 'TUR', 'AZ': 'AZE',
    'CY': 'CYP', 'SA': 'SAU', 'SG': 'SGP', 'DO': 'DOM', 'RO': 'ROU',
    'TW': 'TWN', 'KG': 'KGZ', 'KR': 'KOR', 'TH': 'THA', 'EE': 'EST',
    'CA': 'CAN', 'TN': 'TUN', 'NG': 'NGA', 'PE': 'PER', 'VE': 'VEN',
    'LY': 'LBY', 'IN': 'IND', 'GF': 'GUF', 'SK': 'SVK', 'MA': 'MAR',
    'AO': 'AGO', 'JP': 'JPN', 'MQ': 'MTQ', 'PA': 'PAN', 'MC': 'MCO',
}


# ── GEODATA LOADING (cached) ──────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading geodata...")
def load_geodata():
    """
    Downloads the regions and provinces GeoJSON (openpolis).
    On a network error it raises a clear message instead of crashing with a raw
    traceback: useful in an exam environment without connectivity.
    """
    try:
        geojson_regioni = requests.get(GEOJSON_REGIONI_URL, timeout=15).json()
        geojson_province = requests.get(GEOJSON_PROVINCE_URL, timeout=15).json()
    except requests.RequestException as e:
        st.error(
            "Unable to download the geographic data (GeoJSON). "
            "Check your connection or try again. "
            f"Detail: {e}"
        )
        st.stop()

    regioni_tutte = {f['properties']['reg_name'] for f in geojson_regioni['features']}
    province_tutte = {f['properties']['prov_acr'] for f in geojson_province['features']}
    return dict(
        geojson_regioni=geojson_regioni,
        geojson_province=geojson_province,
        regioni_tutte=regioni_tutte,
        province_tutte=province_tutte,
    )


# ── Cd_Agente NORMALIZATION ───────────────────────────────────────────────────
def _normalizza_cd_agente(serie: pd.Series) -> pd.Series:
    """
    Normalizes Cd_Agente, robust to both numeric and alphanumeric codes.
    - NaN/None            → pd.NA
    - '7.0' / 7 / '12'    → '007' / '007' / '012'  (zero-pad to 3 digits if numeric)
    - 'W41'               → 'W41'                    (alphanumeric left unchanged)

    Needed because the Excel export loses the zfill and the purely numeric codes
    must be realigned, so the join keys between orders/sales/agents match.
    """
    def _norm(v):
        if pd.isna(v):
            return pd.NA
        s = str(v).strip()
        # removes a leftover ".0" from the Excel import (e.g. '7.0' → '7')
        if s.endswith('.0') and s[:-2].isdigit():
            s = s[:-2]
        return s.zfill(3) if s.isdigit() else s
    return serie.map(_norm)


def _arricchisci_geografia(df_trans: pd.DataFrame, df_clienti: pd.DataFrame) -> pd.DataFrame:
    """
    Geographic join (Region/Province/Country) from df_clienti + ISO3 code.
    Factored out: previously duplicated identically for orders and sales.
    """
    df = df_trans.merge(
        df_clienti[_GEO_COLS], left_on='Cd_Cliente', right_on='Cd_CF', how='left'
    ).drop(columns=['Cd_CF'])
    df['ISO3'] = df['Cd_Nazione'].map(iso2_to_iso3)
    return df


# ── DATA LOADING AND ENRICHMENT (cached, only once) ───────────────────────────
@st.cache_data(show_spinner="Loading data...")
def load_data():
    df_agenti  = pd.read_excel(DATA_DIR / "df_agenti_clean.xlsx")
    df_clienti = pd.read_excel(DATA_DIR / "df_clienti_clean.xlsx")
    df_ordini  = pd.read_excel(DATA_DIR / "df_ordini_clean.xlsx")
    df_vendite = pd.read_excel(DATA_DIR / "df_vendite_clean.xlsx")

    df_ordini['Data']  = pd.to_datetime(df_ordini['Data'])
    df_vendite['Data'] = pd.to_datetime(df_vendite['Data'])
    df_agenti['Descrizione']  = df_agenti['Descrizione'].str.strip()
    df_clienti['Descrizione'] = df_clienti['Descrizione'].str.strip()

    # Consistent Cd_Agente realignment across the three datasets.
    for _df in (df_ordini, df_vendite, df_agenti):
        _df['Cd_Agente'] = _normalizza_cd_agente(_df['Cd_Agente'])

    # Identical geographic enrichment for both transactional datasets.
    df_ordini  = _arricchisci_geografia(df_ordini, df_clienti)
    df_vendite = _arricchisci_geografia(df_vendite, df_clienti)

    return df_agenti, df_clienti, df_ordini, df_vendite


# ── GLOBAL FILTER APPLICATION (single function) ───────────────────────────────
def applica_filtri(df: pd.DataFrame, filters: dict, dataset: str = 'ordini') -> pd.DataFrame:
    """
    Applies the global filters (Year, Agent, Region, Product Group) to a dataframe.

    The Product Group filter is silently ignored if the column does not exist
    (df_vendite case). Agent and Region apply to both datasets.
    The `dataset` parameter is kept for compatibility and clarity at call sites.
    """
    df_f = df

    rng = filters.get('anno_range')
    if rng:
        anno_min, anno_max = rng
        df_f = df_f[df_f['Anno'].between(anno_min, anno_max)]

    agenti = filters.get('agente')
    if agenti:  # non-empty list
        df_f = df_f[df_f['Cd_Agente'].isin(agenti)]

    regione = filters.get('regione')
    if regione and regione != 'Tutte':
        df_f = df_f[df_f['Regione'] == regione]

    gruppo = filters.get('gruppo')
    if gruppo and gruppo != 'Tutti' and 'Gruppo_Articolo' in df_f.columns:
        df_f = df_f[df_f['Gruppo_Articolo'] == gruppo]

    # A single defensive copy at the end (instead of always .copy() upfront).
    return df_f.copy()


def filtri_senza_anno(filters: dict, anno_min: int, anno_max: int) -> dict:
    """Copy of the filters with the Year range extended to the whole history.
    Needed by components (e.g. Retention) that require the full series."""
    return {**filters, 'anno_range': (anno_min, anno_max)}


def agente_filtrato(filters: dict) -> bool:
    """True if a filter on one or more agents is active (non-empty list)."""
    return bool(filters.get('agente'))


def n_agenti_selezionati(filters: dict) -> int:
    """How many agents are selected (0 = all)."""
    return len(filters.get('agente') or [])


# ── SHARED DATA LOGIC (single place, reused by multiple tabs) ─────────────────
def calcola_anno_primo_ordine(df_ordini_completo: pd.DataFrame) -> pd.DataFrame:
    """
    Year of the very first order for each customer, computed on the FULL
    (unfiltered) DataFrame: it's an intrinsic customer trait and must not
    depend on the active filters. Used by the "New customers" KPI and by the
    New/Recurring stacked chart.

    Returns: DataFrame [Cd_Cliente, Anno_Primo_Ordine].
    """
    return (
        df_ordini_completo
        .groupby('Cd_Cliente')['Anno'].min()
        .reset_index(name='Anno_Primo_Ordine')
    )


def assegna_agente_primario(df_ordini: pd.DataFrame) -> pd.DataFrame:
    """
    Assigns each customer to the agent with whom they have the highest number of
    ORDERS (unique documents). Tie-breaker fallback: agent with the highest
    revenue, then the one with the most recent order. Used by the
    "Avg customers/agent" KPI.

    Returns: DataFrame [Cd_Cliente, Cd_Agente] (one agent per customer).
    """
    grp = (
        df_ordini
        .groupby(['Cd_Cliente', 'Cd_Agente'])
        .agg(
            n_ordini=('Numero Documento', 'nunique'),
            fatturato=('Valore', 'sum'),
            ultima_data=('Data', 'max'),
        )
        .reset_index()
    )
    grp = grp.sort_values(
        ['Cd_Cliente', 'n_ordini', 'fatturato', 'ultima_data'],
        ascending=[True, False, False, False],
    )
    return grp.drop_duplicates('Cd_Cliente')[['Cd_Cliente', 'Cd_Agente']]
