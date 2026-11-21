# SafeCycle — Safety-First Bike Route Planner (Python + Drafter)

> **"Safety first. Distance and travel time second."**

SafeCycle is a safety-first bicycle route planner built in **Python** with the **Drafter** web framework (`drafter>=2.3.2`). It generates real street-following OpenStreetMap cycling routes and transparently scores every road segment from **0 to 100** using cycling infrastructure, posted speed limits, traffic exposure, crash history, and intersection conflict so riders can compare **Safest**, **Balanced**, and **Direct** corridors.

## Pages & Features

1. **Planner (`index`)** — Start and End location inputs with instant curated + live OpenStreetMap Photon autofill dropdowns, compact `⇅` swap icon button, route/risk/detour/speed/time preferences, and a live Trip Overview Map with **S** (Start) and **E** (End) pins that update as locations change.
2. **Route Results (`route_results_page`)** — Interactive Leaflet map displaying smooth continuous routes (up to the top 3 distinct corridors) with clickable route lines and compact abbreviated badges (`Saf`, `Bal`, `Dir`) that expand on hover or selection. Right-hand panel features integrated underline tabs, prominent **Distance**, **Est. Time**, and **Elevation** statistics, a highlighted **Bike Infrastructure** progress card, a compact safety risk bar under the safety score, GPX 1.1 export, and an **Advanced Details** toggle revealing Safety Cautions, Segment Safety Spectrum SVG, Road Segment Breakdown table, and Corridor Diagnostics.
3. **Segment Safety Details (`segment_details_page`)** — Detailed single-segment street map and evidence breakdown covering cycling infrastructure, posted speed limit, traffic exposure, collision history, positive/risk factors, and safer alternative recommendations.
4. **Settings (`settings_page`)** — Default planned speed, departure time, preferred route mode, `mi`/`km` units, Advanced Detail View default, and Light/Dark theme (plus a top-bar Moon/Sun quick toggle).
5. **About & Credits (`about_page`)** — Transparent 5-factor safety scoring weights, honest data source limitations, and open-source credits/attributions (OpenStreetMap ODbL, Leaflet, FOSSGIS/OSRM, Photon, Nominatim, Drafter, Google Fonts, and public Vision Zero/DOT datasets).

## Project Structure

- `main.py` — Drafter entrypoint, `State` dataclass, 5 pages, 12 `@route` handlers, `set_site_information(...)`, and built-in `bakery.assert_equal` unit tests.
- `models.py` — Core typed dataclasses (`Coordinate`, `RouteSummary`, `CrashRecord`, `RoadSegment`, `RouteOption`).
- `safety.py` — Objective 5-factor 0–100 cycling safety scoring engine and confidence rating model.
- `routing.py` — Live OpenStreetMap OSRM bicycle/street routing with objective road classification, backtrack-spur filtering, route deduplication, and deterministic local fallback graph.
- `geocoding.py` — Curated cycling location catalog, coordinate parsing, and live Photon/Nominatim geocoding.
- `visuals.py` — Continuous Leaflet polyline + route badge JSON serialization and pure-Python SVG safety charts.
- `storage.py` — GPX 1.1 XML route exporter.
- `styles.py` — Editorial light/dark CSS theme, GPU-composited bicycle loading screen, autofill dropdown controller, and Leaflet map overlay enhancements.
- `tests/` — Automated unit test suite (`test_bakery_all.py`, `test_drafter_routes.py`, `test_routing.py`, `test_safety.py`).
- `chat_log.md` & `AI USE (chatgpt).txt` — Complete AI development conversation logs.

## Running Locally

```bash
pip install -r requirements.txt
python3 main.py
```

Then open `http://localhost:3000`.

## Running Automated Tests

```bash
python3 -m unittest discover -s tests -v
```
