# SafeCycle — A Safety-First Bike GPS and Route Planner

> **"Safety first. Distance and travel time second."**

SafeCycle is a bicycle GPS navigation and route-planning web application built 100% in **Python** using **Python Drafter**. Rather than directing cyclists down high-speed, dangerous multi-lane arterials simply because they are the shortest or fastest, SafeCycle prioritizes dedicated bicycle infrastructure (protected bike lanes, off-street greenway trails, traffic-calmed neighborhood greenways), lower motor vehicle speeds, and verified collision histories.

---

## 1. Non-Negotiable Architecture: 100% Python Drafter

SafeCycle is built purely using **Python Drafter** as the primary web framework:
- **`main.py` / `app.py`**: Drafter application entrypoint, page routing, interactive state management, and Leaflet map integration via Drafter components (`Page`, `Header`, `Div`, `Row`, `Button`, `TextBox`, `SelectBox`, `RawHTML`).
- **`models.py`**: Typed data structures (`Coordinate`, `RoadSegment`, `CrashRecord`, `TurnInstruction`, `RouteOption`, `SavedRouteItem`).
- **`safety.py`**: Transparent 5-factor road safety scoring engine (0-100) with confidence levels (`HIGH`, `MEDIUM`, `LOW`, `INSUFFICIENT`) and positive/negative risk attribution.
- **`routing.py`**: Graph-based multi-objective Dijkstra and heuristic routing engine with configurable safety cost penalties.
- **`geocoding.py`**: OpenStreetMap Nominatim address geocoding with instant benchmark corridor presets.
- **`data_sources.py`**: Municipal Vision Zero collision databases, OpenStreetMap road attributes, and traffic exposure levels.
- **`storage.py`**: JSON-based route persistence and GPX 1.1 XML export.

---

## 2. Road Safety Scoring System

Every road segment is evaluated on a scale from **0 to 100** (higher score = lower estimated cyclist risk).

### Configurable Design Weights:
1. **Bicycle Infrastructure (30%)**:
   - Protected Off-Road Cycle Path: 100 / 100 (+30 pts)
   - Separated Protected Bike Lane (bollards / curb): 85 / 100 (+25.5 pts)
   - Painted Bike Lane: 60 / 100 (+18 pts)
   - Shared Sharrow: 35 / 100 (+10.5 pts)
   - No Infrastructure: 15 / 100 (+4.5 pts)
2. **Vehicle Speed Limit (20%)**:
   - &le; 15 mph: 100 / 100 (+20 pts)
   - 20-25 mph: 70-85 / 100 (+14-17 pts)
   - 30-35 mph: 25-45 / 100 (+5-9 pts)
   - 40+ mph: 0-10 / 100 (0-2 pts)
3. **Traffic Exposure Volume (15%)**:
   - Very Low (cul-de-sac / quiet lane): 95 / 100 (+14.25 pts)
   - Low (local residential): 80 / 100 (+12 pts)
   - Moderate (collector): 50 / 100 (+7.5 pts)
   - Heavy (multi-lane commercial arterial / truck route): 5 / 100 (+0.75 pts)
4. **Historical Crash Records (20%)**:
   - 0 reported crashes (with low/moderate exposure): 82 / 100 baseline
   - Minor collisions: -8 pts each
   - Severe cyclist injuries: -22 pts each
   - Fatalities: -45 pts each
5. **Intersection Risk (15%)**:
   - Low (protected bike signal, mini-roundabout): 90 / 100 (+13.5 pts)
   - Moderate (standard signalized crossing): 60 / 100 (+9 pts)
   - High Conflict (multi-lane turn conflict, highway ramp merge): 20 / 100 (+3 pts)

### Risk Color Coding:
- 🟢 **Green (80-100)**: Lower estimated risk.
- 🟡 **Yellow (60-79)**: Moderate estimated risk.
- 🟠 **Orange (40-59)**: Elevated estimated risk.
- 🔴 **Red (<40)**: High estimated risk.
- ⚪ **Gray**: Unknown / Insufficient Data.

### Uncertainty & Data Limitations:
- Never assume a road is guaranteed safe. Zero recorded crashes does not grant a 100 score if other high-risk factors exist or data confidence is low.
- Missing data is never treated as safe; it is labeled with lower confidence and scored using a documented fallback.

---

## 3. Data Sources

1. **OpenStreetMap & Overpass API**:
   - Coverage: Street network, bicycle infrastructure tags (`cycleway`, `bicycle=yes`), posted speed limits (`maxspeed`), highway classification (`cycleway`, `residential`, `tertiary`, `secondary`, `primary`).
   - Limitations: Crowdsourced; coverage can be uneven outside core metropolitan areas.
2. **Municipal Vision Zero Collision Databases (NYC, SF, Seattle, Portland)**:
   - Coverage: Geocoded police-reported motor vehicle crashes involving bicycles from 2022 to 2025, with injury severity.
   - Limitations: Only police-reported incidents are captured. Near-misses and minor unreported cyclist falls are excluded.
3. **Department of Transportation Traffic Counts**:
   - Coverage: Major arterial and collector street Annual Average Daily Traffic (AADT).
   - Limitations: Residential local streets lack continuous automated vehicle counters; volumes are inferred from functional road classifications.

---

## 4. Running the Application

### Prerequisites:
Python 3.10+ and pip:
```bash
pip install -r requirements.txt
```

### Start the Drafter Server:
```bash
python3 app.py
```
The application will launch on `http://localhost:3000`.

### Run Automated Tests:
```bash
python3 -m unittest discover tests
```

---

## 5. Automated Tests Suite

The test suite validates:
- Protected bike lanes score significantly higher than comparable unprotected high-speed roads.
- High-speed roads with heavy traffic receive worse scores than low-speed roads with bike infrastructure.
- Segments with missing data receive reduced confidence and are not given artificially high scores.
- Safest mode prefers safer routes over Direct mode even with modest detours.
- Balanced mode considers both trip length and safety risk.
- Direct mode identifies dangerous segments and provides warnings rather than hiding them.
- All distances, cycling times, and safety scores use consistent units (km, minutes, 0-100 score).
- Address geocoding and invalid coordinates fail gracefully with clear user guidance.
