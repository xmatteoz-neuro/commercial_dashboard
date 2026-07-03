# config.py
"""
Shared constants for the whole dashboard.
Centralized here to avoid tab-by-tab redefinitions.
"""

# ── PROJECT PALETTE ───────────────────────────────────────────────────────────
PALETTE = {
    'background': '#FAFAF8',
    'sidebar':    '#131414',
    'bordeaux':   '#8B2635',   # primary accent    → ORDERS
    'rust':       '#C4513A',   # secondary accent  → SALES
    'muted':      '#8B8880',
}

# Standard Orders/Sales color convention (used wherever they are compared).
COLORE_ORDINI  = PALETTE['bordeaux']
COLORE_VENDITE = PALETTE['rust']

# ── KPI VARIATION COLORS (consistent with palette, not "stock" green/red) ─────
# Desaturated "forest" green and brick red so they don't clash with bordeaux/rust.
VARIAZIONE = {
    'su':        '#3C7A57',   # increase → forest green
    'giu':       '#A6332E',   # decrease → brick red
    'invariato': '#8B8880',   # 0% / N/A → muted
}

# ── DEFAULTS / THRESHOLDS ─────────────────────────────────────────────────────
TOP_N_DEFAULT = 5

# Minimum Value threshold to consider a row "real" (discards adjustments/zeros).
# Centralized: previously repeated as `df['Valore'] >= 1` in dozens of places.
VALORE_MINIMO = 1

# ── KEY COLUMNS (real dataset names, confirmed by the user) ───────────────────
COL_DOC    = 'Numero Documento'   # unique document — present in orders AND sales
COL_VALORE = 'Valore'
COL_ANNO   = 'Anno'
COL_MESE   = 'Mese'
COL_CLIENTE = 'Cd_Cliente'
COL_AGENTE  = 'Cd_Agente'

# ── CHOROPLETH SCALES (0 = light background → full accent) ────────────────────
SCALA_CHOROPLETH         = [(0, PALETTE['background']), (1, PALETTE['bordeaux'])]
SCALA_CHOROPLETH_VENDITE = [(0, PALETTE['background']), (1, PALETTE['rust'])]

# ── GEODATA (openpolis source URLs) ───────────────────────────────────────────
GEOJSON_REGIONI_URL = (
    "https://raw.githubusercontent.com/openpolis/geojson-italy/master/"
    "geojson/limits_IT_regions.geojson"
)
GEOJSON_PROVINCE_URL = (
    "https://raw.githubusercontent.com/openpolis/geojson-italy/master/"
    "geojson/limits_IT_provinces.geojson"
)
