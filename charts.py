# charts.py
"""
Reusable plotting functions. Every component that appears in more than one tab
is written ONCE and parameterized.

Color conventions: Orders = bordeaux (#8B2635), Sales = rust (#C4513A).
Each function accepts ALREADY filtered dataframes, returns a `fig` object and
never calls `.show()`. It returns `None` when there is nothing to draw:
it's up to the caller to show a substitute message.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import (
    COLORE_ORDINI, COLORE_VENDITE, PALETTE,
    SCALA_CHOROPLETH, SCALA_CHOROPLETH_VENDITE,
)
from helpers import righe_reali, aggrega_per, top_n

_LAYOUT_BASE = dict(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')

# Display-only labels for the series names. The tabs keep passing the internal
# values ('Ordini'/'Vendite') used as logical keys elsewhere; this map is applied
# only where the series name becomes on-screen text (legend/hover).
_ETICHETTA_SERIE = {'Ordini': 'Orders', 'Vendite': 'Sales'}


def _serie_label(nome):
    """Returns the English display label for a series name, unchanged if unknown."""
    return _ETICHETTA_SERIE.get(nome, nome)


# ── BAR LABEL FORMATTING ──────────────────────────────────────────────────────
def _fmt(v, metrica):
    return f'€{v:,.0f}' if metrica == 'fatturato' else f'{int(v):,}'


# ══════════════════════════════════════════════════════════════════════════════
# 1. MONTHLY REVENUE — 8 traces (2 series × 2 views × 2 metrics), 2 dropdowns
# ══════════════════════════════════════════════════════════════════════════════
def plot_revenue(df_ordini, df_vendite):
    """
    Smoothed line Orders vs Sales, monthly aggregation.

    Two INDEPENDENT and COMBINABLE dropdowns:
      - View:   Normal / Cumulative
      - Metric: Revenue (€) / Count (unique documents)

    8 total traces (2 views × 2 metrics × 2 series), 2 visible at a time.
    The combination is achieved by keeping the state of the two menus in Python
    variables: each button applies its own dimension KEEPING the other one
    current, so "Cumulative + Count" is reachable (it used to be a bug).
    """
    def _serie(df, metrica):
        d = righe_reali(df)
        if metrica == 'fatturato':
            s = d.groupby(['Anno', 'Mese'])['Valore'].sum()
        else:  # count = unique documents
            s = d.groupby(['Anno', 'Mese'])['Numero Documento'].nunique()
        s = s.reset_index(name='y')
        s['Data'] = pd.to_datetime(
            s[['Anno', 'Mese']].rename(columns={'Anno': 'year', 'Mese': 'month'}).assign(day=1)
        )
        return s.sort_values('Data')

    # consistent trace order: for each (view, metric) → (Orders, Sales)
    combos = [
        ('normale',    'fatturato'),
        ('cumulativo', 'fatturato'),
        ('normale',    'conteggio'),
        ('cumulativo', 'conteggio'),
    ]

    fig = go.Figure()
    trace_meta = []  # (view, metric, series_name) — aligned to the trace order
    for vista, metrica in combos:
        for nome, df_src, colore in [
            ('Ordini', df_ordini, COLORE_ORDINI),
            ('Vendite', df_vendite, COLORE_VENDITE),
        ]:
            s = _serie(df_src, metrica)
            y = s['y'].cumsum() if vista == 'cumulativo' else s['y']
            nome_lbl = _serie_label(nome)
            fig.add_trace(go.Scatter(
                x=s['Data'], y=y, name=nome_lbl,
                line=dict(color=colore, width=3, shape='spline', smoothing=0.6),
                mode='lines',
                visible=(vista == 'normale' and metrica == 'fatturato'),
                hovertemplate=f'{nome_lbl}: %{{y:,.0f}}<extra></extra>',
            ))
            trace_meta.append((vista, metrica, nome))

    def _visible(vista, metrica):
        """Boolean visibility array for a (view, metric) combination."""
        return [(v == vista and m == metrica) for (v, m, _) in trace_meta]

    # Initial state of the two menus; each button combines its own choice
    # with the current state of the OTHER menu.
    vista_corr, metrica_corr = 'normale', 'fatturato'

    menu_vista = dict(
        type='dropdown', direction='down', x=1.0, xanchor='right', y=1.18, yanchor='top',
        showactive=True,
        buttons=[
            dict(label='View: Normal', method='update',
                 args=[{'visible': _visible('normale', metrica_corr)}]),
            dict(label='View: Cumulative', method='update',
                 args=[{'visible': _visible('cumulativo', metrica_corr)}]),
        ],
    )
    menu_metrica = dict(
        type='dropdown', direction='down', x=0.62, xanchor='right', y=1.18, yanchor='top',
        showactive=True,
        buttons=[
            dict(label='Metric: Revenue', method='update',
                 args=[{'visible': _visible(vista_corr, 'fatturato')}]),
            dict(label='Metric: Count', method='update',
                 args=[{'visible': _visible(vista_corr, 'conteggio')}]),
        ],
    )

    fig.update_layout(
        title='Monthly Trend — Orders vs Sales',
        updatemenus=[menu_vista, menu_metrica],
        yaxis=dict(tickformat=',.0f'),
        xaxis=dict(type='date', rangeslider=dict(visible=True)),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
        height=460, margin=dict(t=90, b=40),
        **_LAYOUT_BASE,
    )

    # January-March bands for each year (seasonal context)
    for a in sorted(df_ordini['Anno'].dropna().unique()):
        fig.add_vrect(x0=f'{int(a)}-01-01', x1=f'{int(a)}-04-01',
                      fillcolor='grey', opacity=0.08, layer='below', line_width=0)
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# 2. "TOP N vs TOTAL" BARS — generic pattern (transparent background + full bar)
# ══════════════════════════════════════════════════════════════════════════════
def plot_barre_vs_totale(
    df, dimensione, label_map=None, top_n_righe=5,
    df_secondario=None, nome_primario='Ordini', nome_secondario='Vendite',
    colore_primario=COLORE_ORDINI, colore_secondario=COLORE_VENDITE,
    titolo='', metrica='fatturato', altezza=420,
    barre_raggruppate=False, mostra_sfondo=True,
):
    """
    Horizontal bar pattern: transparent background bar = reference total
    (same on every row), full overlaid bar = value of the subset.

    Key parameters:
    - dimensione: column to group by (e.g. 'Regione', 'Cd_Provincia', 'Cd_Agente').
    - label_map: dict {key -> readable label} to show names, not codes.
    - top_n_righe: number of rows (None = all).
    - df_secondario: if provided, draws a SECOND full bar (Orders vs Sales).
    - barre_raggruppate: if True (with df_secondario), the two full bars are side by side.
    - mostra_sfondo: if False, does NOT draw the company-total background bar and
      the X axis adapts to the real values (useful when the total would squash the bars).
    - metrica: 'fatturato' (sum of Value) or 'conteggio' (unique documents).
    """
    serie = aggrega_per(df, dimensione, metrica)
    if serie.empty:
        return None

    # English display labels for the two series (legend/hover), logic unchanged.
    lbl_primario = _serie_label(nome_primario)
    lbl_secondario = _serie_label(nome_secondario)

    totale = serie.sum()
    top = top_n(serie, top_n_righe) if top_n_righe else serie.sort_values(ascending=False)
    chiavi = top.index.tolist()

    def _lbl(k):
        return label_map.get(k, str(k)) if label_map else str(k)
    labels = [_lbl(k) for k in chiavi]

    # ── Grouped bars mode (two full bars side by side per row) ────────────────
    if barre_raggruppate and df_secondario is not None:
        serie2 = aggrega_per(df_secondario, dimensione, metrica)
        vals1 = top.values
        vals2 = [serie2.get(k, 0) for k in chiavi]

        fig = go.Figure()
        if mostra_sfondo:
            fig.add_trace(go.Bar(
                x=[totale] * len(chiavi), y=labels, orientation='h',
                marker=dict(color=colore_primario, opacity=0.10),
                name='Company total', hoverinfo='skip', offsetgroup='bg', width=0.8,
                visible='legendonly',
            ))
        fig.add_trace(go.Bar(
            x=vals1, y=labels, orientation='h',
            marker=dict(color=colore_primario), name=lbl_primario,
            text=[_fmt(v, metrica) for v in vals1], textposition='outside',
            offsetgroup=nome_primario, width=0.35,
            hovertemplate=f'{lbl_primario}: %{{x:,.0f}}<extra></extra>',
        ))
        fig.add_trace(go.Bar(
            x=vals2, y=labels, orientation='h',
            marker=dict(color=colore_secondario), name=lbl_secondario,
            text=[_fmt(v, metrica) for v in vals2], textposition='outside',
            offsetgroup=nome_secondario, width=0.35,
            hovertemplate=f'{lbl_secondario}: %{{x:,.0f}}<extra></extra>',
        ))
        max_val = max(list(vals1) + list(vals2) + [1])
        fig.update_layout(
            title=titolo, barmode='overlay',
            yaxis=dict(autorange='reversed'),
            xaxis=dict(tickformat=',.0f', range=[0, max_val * 1.18]),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            height=max(altezza, 90 * len(chiavi) + 120),
            margin=dict(t=60, b=30, l=10, r=40),
            bargap=0.35, bargroupgap=0.05,
            **_LAYOUT_BASE,
        )
        return fig

    # ── Classic mode (one full bar, optional second one in overlay) ───────────
    fig = go.Figure()
    if mostra_sfondo:
        fig.add_trace(go.Bar(
            x=[totale] * len(chiavi), y=labels, orientation='h',
            marker=dict(color=colore_primario, opacity=0.12),
            name='Company total', hoverinfo='skip', showlegend=True,
            visible='legendonly',
        ))
    fig.add_trace(go.Bar(
        x=top.values, y=labels, orientation='h',
        marker=dict(color=colore_primario), name=lbl_primario,
        text=[_fmt(v, metrica) for v in top.values], textposition='outside',
        hovertemplate=f'{lbl_primario}: %{{x:,.0f}}<extra></extra>',
    ))
    if df_secondario is not None:
        serie2 = aggrega_per(df_secondario, dimensione, metrica)
        vals2 = [serie2.get(k, 0) for k in chiavi]
        fig.add_trace(go.Bar(
            x=vals2, y=labels, orientation='h',
            marker=dict(color=colore_secondario), name=lbl_secondario,
            text=[_fmt(v, metrica) for v in vals2], textposition='outside',
            hovertemplate=f'{lbl_secondario}: %{{x:,.0f}}<extra></extra>',
        ))

    fig.update_layout(
        title=titolo, barmode='overlay',
        yaxis=dict(autorange='reversed'),
        xaxis=dict(tickformat=',.0f'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=altezza, margin=dict(t=60, b=30, l=10, r=60),
        **_LAYOUT_BASE,
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# 3. ITALY MAP — level and dataset passed as parameters (external toggles)
# ══════════════════════════════════════════════════════════════════════════════
def plot_mappa_italia(df, geo, livello='regione', colore='ordini', solo_dati=False):
    """
    Italy choropleth for a single (dataset, level).
    - df: dataframe already chosen upstream (orders or sales, already filtered).
    - livello: 'regione' | 'provincia'.
    - colore: 'ordini' (bordeaux) | 'vendite' (rust) — only for the color scale.
    - solo_dati: if True, does NOT fill the missing areas with zeros. Useful with
      the Region filter active: only the provinces with data remain and fitbounds
      zooms onto them.
    Colorbar removed; the toggles are handled outside (st.radio) for independent state.
    """
    col = 'Regione' if livello == 'regione' else 'Cd_Provincia'
    geojson = geo['geojson_regioni'] if livello == 'regione' else geo['geojson_province']
    key = 'properties.reg_name' if livello == 'regione' else 'properties.prov_acr'
    tutte = geo['regioni_tutte'] if livello == 'regione' else geo['province_tutte']
    scala = SCALA_CHOROPLETH if colore == 'ordini' else SCALA_CHOROPLETH_VENDITE

    d = righe_reali(df)
    d = d[(d['Cd_Nazione'] == 'IT') & d[col].notna()]
    agg = d.groupby(col)['Valore'].sum().reset_index(name='Fatturato')

    # Fill missing areas with 0 (avoids "holes" in the national view).
    # With solo_dati=True we skip it: only the areas with data remain and
    # fitbounds automatically zooms onto them (useful with the Region filter active).
    if not solo_dati:
        mancanti = tutte - set(agg[col])
        agg = pd.concat([agg, pd.DataFrame({col: list(mancanti), 'Fatturato': 0})],
                        ignore_index=True)

    fig = go.Figure(go.Choropleth(
        geojson=geojson, locations=agg[col], featureidkey=key, z=agg['Fatturato'],
        colorscale=scala, zmin=0, zmax=max(agg['Fatturato'].max(), 1),
        marker_line_width=0.4, marker_line_color='white', showscale=False,
        hovertemplate='%{location}<br>€%{z:,.0f}<extra></extra>',
    ))
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
    fig.update_layout(margin={"r": 0, "t": 10, "l": 0, "b": 0}, height=420, **_LAYOUT_BASE)
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# 4. WORLD MAP (logarithmic scale)
# ══════════════════════════════════════════════════════════════════════════════
def plot_mappa_mondo(df_vendite):
    """World choropleth by country (ISO3), logarithmic scale so the scale isn't
    squashed by Italy's weight."""
    d = righe_reali(df_vendite)
    d = d[d['ISO3'].notna()]
    agg = d.groupby('ISO3')['Valore'].sum().reset_index(name='Fatturato')
    if agg.empty:
        return None
    agg['log_fatt'] = np.log10(agg['Fatturato'].clip(lower=1))

    fig = go.Figure(go.Choropleth(
        locations=agg['ISO3'], z=agg['log_fatt'], locationmode='ISO-3',
        colorscale=SCALA_CHOROPLETH, customdata=agg['Fatturato'],
        marker_line_width=0.3, marker_line_color='white', showscale=False,
        hovertemplate='%{location}<br>€%{customdata:,.0f}<extra></extra>',
    ))
    fig.update_geos(visible=True, showcountries=True, projection_type='natural earth')
    fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0}, height=420,
                      title='World Revenue (log scale)', **_LAYOUT_BASE)
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# 5. AGENT x YEAR HEATMAP (Orders/Sales toggle)
# ══════════════════════════════════════════════════════════════════════════════
def plot_heatmap_agenti(df_ordini, df_agenti, df_vendite=None):
    """
    Revenue heatmap Agent (rows) × Year (columns).
    If df_vendite is provided, an Orders/Sales toggle (both have Cd_Agente).
    Palette white→bordeaux for Orders, white→rust for Sales.
    """
    label = df_agenti.set_index('Cd_Agente')['Descrizione'].to_dict()

    def _pivot(df):
        d = righe_reali(df).copy()
        d['Label'] = d['Cd_Agente'].map(lambda c: f"{c} — {label.get(c, '')}")
        return (d.groupby(['Label', 'Anno'])['Valore'].sum()
                  .reset_index()
                  .pivot(index='Label', columns='Anno', values='Valore').fillna(0))

    def _heat(p, visible, colore=COLORE_ORDINI):
        return go.Heatmap(
            z=p.values, x=p.columns.astype(str), y=p.index,
            colorscale=[(0, 'white'), (1, colore)],
            text=[[f'€{v:,.0f}' for v in row] for row in p.values],
            texttemplate='%{text}', textfont=dict(size=9),
            hoverongaps=False, visible=visible, showscale=False,
        )

    p_ord = _pivot(df_ordini)
    fig = go.Figure(_heat(p_ord, True, COLORE_ORDINI))

    if df_vendite is not None:
        p_ven = _pivot(df_vendite)
        fig.add_trace(_heat(p_ven, False, COLORE_VENDITE))
        fig.update_layout(updatemenus=[dict(
            type='buttons', direction='right', x=1.0, xanchor='right', y=1.06, yanchor='bottom',
            buttons=[
                dict(label='Orders', method='update', args=[{'visible': [True, False]}]),
                dict(label='Sales', method='update', args=[{'visible': [False, True]}]),
            ], active=0,
        )])

    n_agenti = max(len(p_ord.index), 1)
    fig.update_layout(
        title='Revenue by Agent × Year',
        xaxis=dict(title='Year', tickmode='linear'),
        yaxis=dict(title='Agent', autorange='reversed'),
        height=max(400, 40 * n_agenti + 120),
        margin=dict(t=70, b=40, l=250, r=40), **_LAYOUT_BASE,
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# 6. STACKED NEW vs RECURRING + % variation line (Agents tab)
# ══════════════════════════════════════════════════════════════════════════════
def plot_nuovi_ricorrenti(df_filtrato, anno_primo_ordine):
    """
    Stacked bars per year: New customers (very first order ever in that year)
    vs Recurring. Line on a secondary axis = year-over-year % change of the New ones.

    `anno_primo_ordine`: DataFrame [Cd_Cliente, Anno_Primo_Ordine] computed on the
    FULL dataset (from data.calcola_anno_primo_ordine).
    """
    d = df_filtrato.merge(anno_primo_ordine, on='Cd_Cliente', how='left')
    d['Tipo'] = np.where(d['Anno'] == d['Anno_Primo_Ordine'], 'Nuovo', 'Ricorrente')

    agg = (d.groupby(['Anno', 'Tipo'])['Cd_Cliente'].nunique()
             .reset_index(name='N')
             .pivot(index='Anno', columns='Tipo', values='N').fillna(0))
    for c in ('Nuovo', 'Ricorrente'):
        if c not in agg.columns:
            agg[c] = 0
    agg = agg.sort_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(x=agg.index, y=agg['Ricorrente'], name='Recurring',
                         marker_color=PALETTE['muted']))
    fig.add_trace(go.Bar(x=agg.index, y=agg['Nuovo'], name='New',
                         marker_color=COLORE_ORDINI))

    var = (agg['Nuovo'].pct_change() * 100).round(1)
    fig.add_trace(go.Scatter(
        x=agg.index, y=var, name='New % change', mode='lines+markers',
        line=dict(color=COLORE_VENDITE, width=2),
        marker=dict(size=8, color=COLORE_VENDITE, line=dict(color='white', width=1.5)),
        yaxis='y2', hovertemplate='%{y:+.1f}%<extra></extra>',
    ))

    fig.update_layout(
        title='New vs Recurring Customers by Year', barmode='stack',
        xaxis=dict(title='Year', dtick=1),
        yaxis=dict(title='Number of Customers'),
        yaxis2=dict(title='New % change', overlaying='y', side='right',
                    showgrid=False, ticksuffix='%',
                    tickformat='.1f', hoverformat='.1f'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=450, margin=dict(t=60, b=40), **_LAYOUT_BASE,
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# 7. CUSTOMERS SERVED PER YEAR (Normal/Cumulative toggle) — Customers tab
# ══════════════════════════════════════════════════════════════════════════════
def plot_clienti_per_anno(df_filtrato):
    """Bars: number of unique customers served per year. 2 traces (Normal/Cumulative)
    with a toggle via updatemenus."""
    serie = (df_filtrato.groupby('Anno')['Cd_Cliente'].nunique()
             .reset_index(name='N').sort_values('Anno'))
    if serie.empty:
        return None

    cum = serie['N'].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=serie['Anno'], y=serie['N'], name='Customers',
                         marker_color=COLORE_ORDINI, visible=True,
                         text=serie['N'], textposition='outside'))
    fig.add_trace(go.Bar(x=serie['Anno'], y=cum, name='Customers (cum.)',
                         marker_color=COLORE_ORDINI, visible=False,
                         text=cum, textposition='outside'))

    fig.update_layout(
        title='Customers Served per Year',
        updatemenus=[dict(type='buttons', direction='right',
                          x=1.0, xanchor='right', y=1.12, yanchor='top', active=0,
                          buttons=[
                              dict(label='Normal', method='update', args=[{'visible': [True, False]}]),
                              dict(label='Cumulative', method='update', args=[{'visible': [False, True]}]),
                          ])],
        xaxis=dict(title='Year', dtick=1), yaxis=dict(title='Number of Customers'),
        height=420, margin=dict(t=70, b=40), showlegend=False, **_LAYOUT_BASE,
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# 8. RETENTION PER YEAR (horizontal bars: background = prev year, full = retained)
# ══════════════════════════════════════════════════════════════════════════════
def plot_retention_per_anno(df_filtrato_no_anno, anno_min_sel, anno_max_sel):
    """
    One row per year in the selected range (excluding the first, which has no reference).
    Transparent background = customers of the previous year; full bar = how many
    repurchased in the current year. Counts only the "retained" ones (intersection).
    """
    clienti_per_anno = df_filtrato_no_anno.groupby('Anno')['Cd_Cliente'].apply(set).to_dict()
    anni = sorted(clienti_per_anno.keys())

    righe = []
    for i in range(1, len(anni)):
        a_prec, a_corr = anni[i - 1], anni[i]
        if not (anno_min_sel <= a_corr <= anno_max_sel):
            continue
        prec = clienti_per_anno[a_prec]
        corr = clienti_per_anno[a_corr]
        righe.append(dict(
            Anno=str(int(a_corr)),
            Base=len(prec),
            Mantenuti=len(prec & corr),
            Pct=(len(prec & corr) / len(prec) * 100) if prec else 0,
        ))

    if not righe:
        return None
    d = pd.DataFrame(righe)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=d['Base'], y=d['Anno'], orientation='h',
        marker=dict(color=COLORE_ORDINI, opacity=0.12),
        name='Previous year customers', hoverinfo='skip',
    ))
    fig.add_trace(go.Bar(
        x=d['Mantenuti'], y=d['Anno'], orientation='h',
        marker=dict(color=COLORE_ORDINI), name='Retained customers',
        text=[f"{m:,} ({p:.0f}%)" for m, p in zip(d['Mantenuti'], d['Pct'])],
        textposition='outside',
        hovertemplate='%{y}: %{x:,} retained<extra></extra>',
    ))
    fig.update_layout(
        title='Retention per Year', barmode='overlay',
        yaxis=dict(autorange='reversed', title='Year'),
        xaxis=dict(title='Number of Customers'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=420, margin=dict(t=60, b=40, l=10, r=60), **_LAYOUT_BASE,
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# 9. CUSTOMERS vs AVERAGE REVENUE SCATTER (Region/Province toggle)
# ══════════════════════════════════════════════════════════════════════════════
def plot_scatter_geo(df_filtrato, dimensione='Regione'):
    """
    Bubbles: X = number of customers in the aggregate, Y = average revenue per
    customer, size/color = total revenue of the aggregate.
    `dimensione` = 'Regione' or 'Cd_Provincia'.
    """
    col = dimensione  # already the correct column name ('Regione' | 'Cd_Provincia')
    d = righe_reali(df_filtrato)
    d = d[d[col].notna()]
    if d.empty:
        return None

    agg = d.groupby(col).agg(
        Num_Clienti=('Cd_Cliente', 'nunique'),
        Fatturato_Totale=('Valore', 'sum'),
    ).reset_index()
    if agg.empty:
        return None
    agg['Fatturato_Medio_Cliente'] = agg['Fatturato_Totale'] / agg['Num_Clienti']

    etichetta_dim = 'Region' if col == 'Regione' else 'Province'
    fig = px.scatter(
        agg, x='Num_Clienti', y='Fatturato_Medio_Cliente',
        size='Fatturato_Totale', color='Fatturato_Totale',
        color_continuous_scale=SCALA_CHOROPLETH, text=col, size_max=55,
        labels={
            'Num_Clienti': 'Number of Customers',
            'Fatturato_Medio_Cliente': 'Average Revenue per Customer (€)',
            'Fatturato_Totale': 'Total Revenue (€)',
        },
    )
    fig.update_traces(textposition='top center')
    fig.update_layout(
        title=f'Customers vs Average Revenue — {etichetta_dim}',
        height=460, yaxis=dict(tickprefix='€', tickformat=',.0f'),
        coloraxis_colorbar=dict(title='Total<br>Revenue (€)'),
        **_LAYOUT_BASE,
    )
    return fig
