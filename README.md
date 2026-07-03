# Sales Dashboard

An interactive commercial analytics dashboard for an Italian home décor brand,
built with **Streamlit** and **Plotly**. It turns raw orders and sales data into
a set of business views: revenue trends, agent performance, customer retention
and geographic distribution across Italy and abroad.

> **Live demo:** _<!-- add your Streamlit Cloud URL here after deploying, e.g. https://commercial-dashboard.streamlit.app -->_

---

## Data disclaimer

The dataset shipped with this repository is **fully synthetic and anonymized**.
It reproduces the *structure* of real commercial data (same columns, types and
referential integrity between orders, sales, agents and customers) without
containing any real business figures or personal information. All customer and
agent names are randomly generated and do not refer to real people or companies.

---

## Features

The dashboard is organized into five tabs:

- **Overview** — headline KPIs (total revenue, number of orders, active
  customers, top collection), monthly revenue trend, top agents, Italy and World
  maps, top product collections.
- **Sales / Orders** — Orders vs Sales KPIs side by side, shared revenue chart,
  Italy choropleth with dataset toggle, Top 5 regions and provinces.
- **Agents** — per-agent KPIs (including a primary-agent assignment), an
  Agent × Year revenue heatmap, Top 5 agents, and a New vs Recurring customers
  breakdown with year-over-year variation.
- **Customers** — managed customers, new customers, retention rate and average
  spend, customers served per year, retention per year, a geographic scatter
  (customers vs average revenue) and Top 5 customers.
- **Data** — the filtered orders and sales tables with column selection,
  pagination and CSV export.

A global sidebar drives every tab with cascading filters (Year, Agent, Region,
Product Group).

## Tech stack

- **Python**
- **Streamlit** — app framework and UI
- **Plotly** — interactive charts and choropleth maps
- **pandas** — data loading, cleaning and aggregation
- **GeoJSON** (regions and provinces of Italy) from
  [openpolis/geojson-italy](https://github.com/openpolis/geojson-italy)

## Architecture

The project is organized in a modular way, so each concern lives in one place:

```
app.py                 # entry point: loads data, builds the sidebar, routes the tabs
config.py              # shared constants (palette, thresholds, key column names)
data.py                # data loading, cleaning, geographic enrichment, filtering
helpers.py             # pure reusable data logic (aggregations, Top-N)
kpi.py                 # KPI computation and rendering
charts.py              # all reusable Plotly chart functions
ui.py                  # reusable UI components (toggles, chart-or-message wrapper)
tabs/                  # one file per tab — layout orchestration only, no heavy logic
  tab_overview.py
  tab_vendite_ordini.py
  tab_agenti.py
  tab_clienti.py
  tab_data.py
dati/                  # synthetic Excel datasets
```

Design principle: **tabs only orchestrate the layout**; all calculations live in
the shared modules (`data.py`, `helpers.py`, `kpi.py`, `charts.py`). This avoids
duplication and keeps each tab short and readable.

## Run locally

Requires Python 3.10+.

```bash
# 1. clone the repository
git clone https://github.com/xmatteoz-neuro/commercial_dashboard.git
cd commercial_dashboard

# 2. (recommended) create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate

# 3. install the dependencies
pip install -r requirements.txt

# 4. run the app
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

> The Italy and World maps download GeoJSON boundaries from openpolis at runtime,
> so an internet connection is needed on first load.

## License

This project is released for educational and portfolio purposes.
