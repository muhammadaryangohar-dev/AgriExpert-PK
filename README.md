# 🌾 AgriExpert-PK — Intelligent Agricultural Expert System

An AI expert system for diagnosing crop diseases and predicting economic
damage in Pakistani agriculture, combining **symbolic AI (SWI-Prolog)** with
**statistical AI (a dependency-free linear regression engine in pure
Python)**.

Built for 9 major crops (wheat, rice, cotton, maize, sugarcane, potato,
tomato, mango, citrus) grown across Pakistan's Kharif/Rabi seasons.

## AI techniques implemented

| Technique | Where |
|---|---|
| Backward chaining | `diagnose_with_cf/4` — goal-driven proof search over the KB |
| Forward chaining | `derive_all/1` — data-driven inference from asserted facts |
| Unification | native Prolog pattern matching, demoed in the Unification tab |
| Certainty factors | 0–100% confidence scoring on each candidate diagnosis |
| Heuristic search | `best_treatment/4` — scores treatments by cost/effectiveness |
| Linear regression | pure-Python OLS (`β = (XᵀXᵀ)⁻¹Xᵀy`, no numpy/sklearn) predicting yield loss %, which feeds an economic-damage + treatment-ROI model |

## Features

- **Desktop GUI** (tkinter) — 9 tabs: Diagnose, Forward Chain, Backward
  Chain, Unification, CF Analysis, Heuristic Search, KB Explorer,
  Prevention/Seasonal advice, and Economic Damage prediction with a live
  regression scatter plot.
- **Headless CLI** (`agriexpert_cli.py`) — run diagnosis, forward-chaining,
  and economic-damage regression from scripts, cron jobs, or CI, with
  `--json` output for automation.
- **Live weather auto-fill** — type a city and the app fetches current
  temperature/humidity/precipitation from [Open-Meteo](https://open-meteo.com/)
  (no API key required) and maps it onto the KB's weather/soil categories.
- **English / Urdu toggle** — switch the interface language from the header
  button; i18n strings live in `agriexpert_core.TRANSLATIONS` and are easy
  to extend.
- **Export reports** — save any diagnosis or economic-damage result as CSV
  or PDF, from both the GUI and the CLI.

## Project structure

```
agriexpert_core.py   # headless-safe engine: domain data, regression model,
                      # Prolog bridge, live weather, i18n, CSV/PDF export
agriexpert_gui.py     # tkinter desktop app (imports agriexpert_core)
agriexpert_cli.py     # headless CLI (imports agriexpert_core)
agriexpert_kb.pl      # SWI-Prolog knowledge base (facts + rules)
requirements.txt      # optional deps (reportlab, for nicer PDF export)
```

`agriexpert_core.py` has **no tkinter dependency**, so it can be imported in
scripts, servers, or CI without a display — that's what makes the CLI
possible without duplicating any logic.

## Requirements

- Python 3.8+
- [SWI-Prolog](https://www.swi-prolog.org/) installed and on your `PATH`
  (`swipl` must be runnable from a terminal)
- Optional: `pip install -r requirements.txt` for nicer PDF exports
  (falls back to a built-in minimal PDF writer if `reportlab` isn't
  installed)
- Internet connection, only for the live-weather feature

## Usage

### GUI

```bash
python agriexpert_gui.py
```

### CLI

```bash
# Diagnose wheat with observed symptoms
python agriexpert_cli.py diagnose --crop wheat \
    --symptoms yellow_pustules orange_pustules \
    --weather warm_humid --soil normal_moisture

# Auto-fill weather from a real city and export a PDF
python agriexpert_cli.py diagnose --crop rice --symptoms diamond_shaped_lesions \
    --city Lahore --export-pdf report.pdf

# Predict economic loss + treatment ROI, machine-readable
python agriexpert_cli.py regression --crop rice --cf 82 --weather cool_wet \
    --soil waterlogged --hectares 5 --price 6000 --treatment fungicide --json

python agriexpert_cli.py --help
```

## Screenshots

<!-- Add your own screenshots here — see the step-by-step GitHub guide for how. -->
![Diagnose tab](screenshots/diagnose.png)
![Economic Damage tab](screenshots/econ_damage.png)

## Extending

- **Add a crop/disease**: add facts/rules to `agriexpert_kb.pl`, then add
  the crop to `CROPS`/`SYMPTOMS`/price & yield tables in
  `agriexpert_core.py`.
- **Add a language**: add a new key to `TRANSLATIONS` in
  `agriexpert_core.py` and wire up `self._i18n(widget, "key")` in the GUI
  for any label you want translated.
- **Retrain the regression model**: extend
  `REGRESSION_TRAINING_DATA` in `agriexpert_core.py` with more
  `(crop, cf_score, weather_idx, soil_idx, yield_loss_pct)` rows.

## Known limitations / roadmap

- The regression model is trained on a small, hand-curated dataset (~37
  rows) — good for demonstrating the technique, not agronomic ground truth.
- Live weather → soil-moisture mapping is a heuristic (precipitation/
  humidity proxy), not a real soil-moisture sensor reading.
- Urdu translation currently covers the header, tab names, and diagnose
  panel; extending full-app coverage is straightforward (see *Extending*
  above) but not yet complete for every tab.
- No automated test suite yet — see `tests/` as a suggested next addition.

## License

MIT — see [LICENSE](LICENSE).
