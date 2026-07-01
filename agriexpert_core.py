"""
AgriExpert-PK :: Core Engine
============================
Shared, headless-safe logic used by BOTH the GUI (agriexpert_gui.py) and the
CLI (agriexpert_cli.py). This module has NO tkinter dependency, so it can be
imported in scripts, servers, notebooks, or CI without a display.

Contents:
  - Domain data (crops, symptoms, weather, soil, prices, yields, costs)
  - PureLinearRegression — dependency-free OLS regression (no numpy/sklearn)
  - PrologBridge         — talks to SWI-Prolog via subprocess
  - Live weather lookup  — Open-Meteo (no API key required)
  - i18n                 — English / Urdu string table
  - Export helpers       — CSV and PDF report writers
"""

import os
import json
import subprocess
import urllib.request
import urllib.parse
import csv as csv_module

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(BASE_DIR, "agriexpert_kb.pl").replace("\\", "/")

# ══════════════════════════════════════════════════════════════
#  DOMAIN DATA
# ══════════════════════════════════════════════════════════════

CROPS = ["wheat", "rice", "cotton", "maize", "sugarcane", "potato", "tomato", "mango", "citrus"]

SYMPTOMS = {
    "wheat":     ["yellow_pustules", "orange_pustules", "black_smutted_ears", "white_powdery_coating"],
    "rice":      ["diamond_shaped_lesions", "yellow_leaf_spots", "water_soaked_leaf_margins",
                  "yellowing_wilting", "oval_lesions_on_sheath", "brown_circular_spots",
                  "yellow_orange_discolouration"],
    "cotton":    ["leaf_curling_upward", "mosaic_pattern", "rotting_bolls", "sudden_wilting",
                  "dark_brown_spots_on_leaves"],
    "maize":     ["large_black_galls", "chlorotic_stripes_on_leaves", "stalk_softening_collapse",
                  "long_tan_lesions_on_leaves"],
    "sugarcane": ["red_internal_discolouration", "black_whip_from_growing_point", "stunted_ratoon_growth"],
    "potato":    ["water_soaked_dark_lesions", "dark_concentric_ring_spots", "black_rotting_at_stem_base"],
    "tomato":    ["dark_concentric_ring_spots", "sudden_wilting", "water_soaked_leaf_spots"],
    "mango":     ["dark_sunken_spots_on_fruit", "bunchy_top_malformed_panicles"],
    "citrus":    ["raised_corky_lesions_on_leaves", "blotchy_yellow_mottling", "asymmetric_yellowing"],
}

WEATHERS = ["warm_humid", "cool_wet", "hot_dry", "cool_moist", "moderate", "cool_dry"]
SOILS    = ["normal_moisture", "waterlogged", "dry_cracked", "loamy", "sandy", "clay"]
SEASONS  = ["kharif", "rabi"]

DEFAULT_PRICES = {
    "wheat": 4000, "rice": 6000, "cotton": 10000, "maize": 3000,
    "sugarcane": 500, "potato": 2500, "tomato": 3500, "mango": 8000, "citrus": 5000,
}

DEFAULT_YIELD_PER_HECTARE = {
    "wheat": 62, "rice": 60, "cotton": 25, "maize": 75,
    "sugarcane": 1500, "potato": 200, "tomato": 250, "mango": 100, "citrus": 150,
}

TREATMENT_COSTS = {
    "wheat":     {"fungicide": 3500, "pesticide": 2500, "biocontrol": 1500},
    "rice":      {"fungicide": 5000, "pesticide": 4000, "biocontrol": 2000},
    "cotton":    {"fungicide": 4000, "pesticide": 6000, "biocontrol": 2500},
    "maize":     {"fungicide": 3000, "pesticide": 2000, "biocontrol": 1200},
    "sugarcane": {"fungicide": 4500, "pesticide": 3500, "biocontrol": 1800},
    "potato":    {"fungicide": 6000, "pesticide": 3000, "biocontrol": 2200},
    "tomato":    {"fungicide": 5500, "pesticide": 4500, "biocontrol": 2000},
    "mango":     {"fungicide": 4000, "pesticide": 3000, "biocontrol": 1500},
    "citrus":    {"fungicide": 4500, "pesticide": 3500, "biocontrol": 1800},
}

# (crop, cf_score, weather_idx, soil_idx, yield_loss_percent)
REGRESSION_TRAINING_DATA = [
    ("wheat", 92, 1, 0, 38), ("wheat", 85, 1, 0, 32), ("wheat", 70, 1, 1, 28),
    ("wheat", 60, 5, 2, 12), ("wheat", 45, 4, 3, 8), ("wheat", 95, 1, 1, 50),
    ("wheat", 55, 5, 0, 14),
    ("rice", 90, 0, 1, 48), ("rice", 82, 0, 0, 38), ("rice", 75, 0, 0, 30),
    ("rice", 65, 4, 0, 22), ("rice", 55, 4, 3, 15), ("rice", 92, 0, 1, 55),
    ("rice", 48, 3, 3, 10),
    ("cotton", 88, 2, 2, 45), ("cotton", 75, 0, 0, 35), ("cotton", 65, 0, 0, 25),
    ("cotton", 55, 2, 4, 18), ("cotton", 80, 2, 2, 40),
    ("maize", 72, 0, 3, 26), ("maize", 60, 4, 4, 18), ("maize", 50, 4, 4, 12),
    ("maize", 85, 0, 1, 38),
    ("sugarcane", 78, 0, 1, 32), ("sugarcane", 65, 0, 0, 22), ("sugarcane", 55, 4, 3, 15),
    ("potato", 90, 1, 5, 50), ("potato", 78, 3, 0, 32), ("potato", 62, 3, 0, 20),
    ("potato", 88, 1, 1, 46),
    ("tomato", 74, 0, 3, 30), ("tomato", 58, 4, 4, 18), ("tomato", 82, 0, 1, 40),
    ("mango", 68, 2, 2, 22), ("mango", 55, 4, 3, 14),
    ("citrus", 80, 0, 0, 36), ("citrus", 65, 0, 0, 24), ("citrus", 52, 4, 3, 12),
]


# ══════════════════════════════════════════════════════════════
#  PURE-PYTHON LINEAR REGRESSION  (no numpy / sklearn)
# ══════════════════════════════════════════════════════════════

class PureLinearRegression:
    """Ordinary Least Squares via the Normal Equation: beta = (X^T X)^-1 X^T y"""

    def __init__(self):
        self.coef_ = []
        self.intercept_ = 0.0
        self._n_features = 0

    @staticmethod
    def _transpose(M):
        rows, cols = len(M), len(M[0])
        return [[M[r][c] for r in range(rows)] for c in range(cols)]

    @staticmethod
    def _matmul(A, B):
        ra, ca = len(A), len(A[0])
        rb, cb = len(B), len(B[0])
        assert ca == rb, "matmul dimension mismatch"
        R = [[0.0] * cb for _ in range(ra)]
        for i in range(ra):
            for k in range(ca):
                if A[i][k] == 0:
                    continue
                for j in range(cb):
                    R[i][j] += A[i][k] * B[k][j]
        return R

    @staticmethod
    def _inverse(M):
        n = len(M)
        aug = [M[i][:] + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        for col in range(n):
            pivot = None
            for row in range(col, n):
                if abs(aug[row][col]) > 1e-12:
                    pivot = row
                    break
            if pivot is None:
                raise ValueError("Matrix is singular — cannot invert.")
            aug[col], aug[pivot] = aug[pivot], aug[col]
            scale = aug[col][col]
            aug[col] = [v / scale for v in aug[col]]
            for row in range(n):
                if row == col:
                    continue
                factor = aug[row][col]
                aug[row] = [aug[row][j] - factor * aug[col][j] for j in range(2 * n)]
        return [aug[i][n:] for i in range(n)]

    def fit(self, X, y):
        n = len(X)
        Xb = [[1.0] + [float(v) for v in row] for row in X]
        Xt = self._transpose(Xb)
        XtX = self._matmul(Xt, Xb)
        Xty = self._matmul(Xt, [[float(v)] for v in y])
        try:
            beta = self._matmul(self._inverse(XtX), Xty)
        except ValueError:
            lam = 1e-6
            for i in range(len(XtX)):
                XtX[i][i] += lam
            beta = self._matmul(self._inverse(XtX), Xty)
        self.intercept_ = beta[0][0]
        self.coef_ = [beta[i + 1][0] for i in range(len(X[0]))]
        self._n_features = len(X[0])
        return self

    def predict(self, X):
        results = []
        for row in X:
            val = self.intercept_ + sum(self.coef_[i] * float(row[i]) for i in range(self._n_features))
            results.append(val)
        return results

    def score(self, X, y):
        preds = self.predict(X)
        y_mean = sum(y) / len(y)
        ss_res = sum((y[i] - preds[i]) ** 2 for i in range(len(y)))
        ss_tot = sum((y[i] - y_mean) ** 2 for i in range(len(y)))
        return 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0


def _clip(value, lo, hi):
    return max(lo, min(hi, value))


def build_regression_model():
    """Train and return a PureLinearRegression + its category encoders."""
    enc_wth = {w: i for i, w in enumerate(WEATHERS)}
    enc_soil = {s: i for i, s in enumerate(SOILS)}
    enc_crop = {c: i for i, c in enumerate(CROPS)}
    X, y = [], []
    for crop_, cf_, w_idx, s_idx, loss_ in REGRESSION_TRAINING_DATA:
        X.append([enc_crop.get(crop_, 0), float(cf_), float(w_idx), float(s_idx)])
        y.append(float(loss_))
    model = PureLinearRegression().fit(X, y)
    return model, enc_crop, enc_wth, enc_soil


# ══════════════════════════════════════════════════════════════
#  PROLOG BRIDGE
# ══════════════════════════════════════════════════════════════

class PrologBridge:
    def __init__(self, kb_path=KB_PATH):
        self.kb_path = kb_path

    def diagnose(self, crop, symptoms, weather, soil) -> str:
        asserts = [f"crop({crop})"] + [f"symptom({s})" for s in symptoms]
        asserts += [f"weather({weather})"]
        if soil:
            asserts.append(f"soil({soil})")
        query = (
            "findall(r(D,T,CF,Tr), diagnose_with_cf(D,T,CF,Tr), Rs), "
            "sort(3, @>=, Rs, Sorted), "
            "forall(member(r(D,T,CF,Tr), Sorted), "
            "   (nl, write('DISEASE: '), write(D), nl,"
            "    write('CLASS:   '), write(T), nl,"
            "    write('CF:      '), write(CF), nl,"
            "    write('TREAT:'), nl,"
            "    forall(member(X,Tr), (write('  - '), write(X), nl))))"
        )
        return self._run(asserts, query, "No matching disease rules found for the selected combination.")

    def forward_chain(self, crop, symptoms, weather, soil) -> str:
        asserts = [f"crop({crop})"] + [f"symptom({s})" for s in symptoms]
        asserts += [f"weather({weather})"]
        if soil:
            asserts.append(f"soil({soil})")
        query = (
            "derive_all([]), "
            "findall(D, derived(D), Ds), "
            "list_to_set(Ds, Set), "
            "forall(member(X, Set), (write('  >> '), write(X), nl))"
        )
        return self._run(asserts, query, "No forward-chained conclusions derived.")

    def best_treatment(self, disease) -> str:
        script = (
            f"consult('{self.kb_path}'), "
            f"best_treatment({disease}, Idx, Score, Exp), "
            f"write('Best Treatment Index: '), write(Idx), nl, "
            f"write('Heuristic Score: '), write(Score), nl, "
            f"write('Explanation: '), write(Exp), nl, halt."
        )
        return self._run_script(script, "No heuristic data available for this disease.")

    def prevention_advice(self, disease_class) -> str:
        script = (
            f"consult('{self.kb_path}'), "
            f"prevention_advice({disease_class}, Advice), "
            f"forall(member(X, Advice), (write('  * '), write(X), nl)), halt."
        )
        return self._run_script(script, "No prevention advice found.")

    def seasonal_advice(self, season) -> str:
        script = (
            f"consult('{self.kb_path}'), "
            f"seasonal_advice({season}, Advice), "
            f"forall(member(X, Advice), (write('  * '), write(X), nl)), halt."
        )
        return self._run_script(script, "No seasonal advice found.")

    def kb_query(self, crop, disease) -> str:
        d = disease.replace(" ", "_").lower()
        script = (
            f"consult('{self.kb_path}'), "
            f"(pathogen({d}, P) -> write('Pathogen: '), write(P), nl ; true), "
            f"(disease_class({d}, C) -> write('Class: '), write(C), nl ; true), "
            f"(spread({d}, S) -> write('Spread: '), write(S), nl ; true), "
            f"(yield_loss_range({d}, Lo, Hi) -> "
            f"  (write('Yield Loss: '), write(Lo), write('% - '), write(Hi), write('%'), nl) ; true), "
            f"(resistant_variety({d}, V) -> write('Resistant Varieties: '), write(V), nl ; true), "
            f"halt."
        )
        return self._run_script(script, "No KB data found for this disease.")

    def unification_demo(self, crop, symptom, weather) -> str:
        script = (
            f"consult('{self.kb_path}'), "
            f"assert(crop({crop})), assert(symptom({symptom})), assert(weather({weather})), "
            f"write('=== Unification Demo ==='), nl, "
            f"write('Input crop    : {crop}'), nl, "
            f"write('Input symptom : {symptom}'), nl, "
            f"write('Input weather : {weather}'), nl, nl, "
            f"(unify_diagnosis({crop}, {symptom}, Disease) -> "
            f"  (write('Unification SUCCEEDED'), nl, "
            f"   write('Unified Disease : '), write(Disease), nl) ; "
            f"  write('No direct unification — no rule matches this combination')), nl, "
            f"write('--- Term Unification Test ---'), nl, "
            f"demonstrate_unification({crop}, {crop}), "
            f"halt."
        )
        return self._run_script(script, "Unification produced no output.")

    # ── internals ────────────────────────────────────────────
    def _run(self, asserts, query, empty_msg):
        asserts_str = ", ".join(f"assert({a})" for a in asserts)
        script = f"consult('{self.kb_path}'), {asserts_str}, {query}, halt."
        return self._run_script(script, empty_msg)

    def _run_script(self, script, empty_msg, timeout=15):
        cmd = ["swipl", "-g", script, "-t", "halt"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return r.stdout.strip() or empty_msg
        except FileNotFoundError:
            return "ERROR: swipl not found. Please install SWI-Prolog and add it to PATH."
        except subprocess.TimeoutExpired:
            return "ERROR: Prolog query timed out."
        except Exception as e:
            return f"ERROR: {e}"


# ══════════════════════════════════════════════════════════════
#  LIVE WEATHER  (Open-Meteo — free, no API key required)
# ══════════════════════════════════════════════════════════════

class WeatherLookupError(Exception):
    pass


def _http_get_json(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": "AgriExpert-PK/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def geocode_city(city: str):
    """Resolve a city name to (lat, lon, resolved_name, country) via Open-Meteo geocoding."""
    url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode(
        {"name": city, "count": 1, "language": "en", "format": "json"}
    )
    try:
        data = _http_get_json(url)
    except Exception as e:
        raise WeatherLookupError(f"Could not reach geocoding service: {e}")
    results = data.get("results") or []
    if not results:
        raise WeatherLookupError(f"No location found for '{city}'.")
    r = results[0]
    return r["latitude"], r["longitude"], r.get("name", city), r.get("country", "")


def map_to_kb_weather(temp_c: float, humidity_pct: float, precip_mm: float) -> str:
    """Map raw meteorological readings onto the KB's qualitative weather categories."""
    wet = precip_mm is not None and precip_mm > 0.5
    humid = humidity_pct is not None and humidity_pct >= 65
    if temp_c is None:
        return "moderate"
    if temp_c >= 30:
        return "hot_dry" if not humid else "warm_humid"
    if temp_c >= 22:
        return "warm_humid" if humid else "moderate"
    if temp_c >= 14:
        return "cool_wet" if (wet or humid) else "cool_moist"
    return "cool_dry"


def map_to_kb_soil(precip_mm: float, humidity_pct: float) -> str:
    """Rough soil-moisture hint derived from recent precipitation/humidity (best-effort)."""
    if precip_mm is not None and precip_mm > 8:
        return "waterlogged"
    if precip_mm is not None and precip_mm > 1:
        return "normal_moisture"
    if humidity_pct is not None and humidity_pct < 30:
        return "dry_cracked"
    return "normal_moisture"


def fetch_live_weather(city: str) -> dict:
    """
    Fetch current weather for `city` and map it onto AgriExpert-PK's
    qualitative weather/soil categories. Uses Open-Meteo (no API key).

    Returns:
        {
          "city": str, "country": str, "latitude": float, "longitude": float,
          "temperature_c": float, "humidity_pct": float, "precipitation_mm": float,
          "mapped_weather": str, "mapped_soil_hint": str,
        }
    Raises WeatherLookupError on any failure (offline, bad city name, etc.)
    """
    lat, lon, resolved_name, country = geocode_city(city)
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation",
        "timezone": "auto",
    })
    try:
        data = _http_get_json(url)
    except Exception as e:
        raise WeatherLookupError(f"Could not reach weather service: {e}")

    current = data.get("current") or {}
    temp_c = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    precip = current.get("precipitation")

    return {
        "city": resolved_name,
        "country": country,
        "latitude": lat,
        "longitude": lon,
        "temperature_c": temp_c,
        "humidity_pct": humidity,
        "precipitation_mm": precip,
        "mapped_weather": map_to_kb_weather(temp_c, humidity, precip),
        "mapped_soil_hint": map_to_kb_soil(precip, humidity),
    }


# ══════════════════════════════════════════════════════════════
#  i18n  —  English / Urdu
# ══════════════════════════════════════════════════════════════
# Extend TRANSLATIONS["ur"] with more keys as you localize additional
# screens; any key missing from a language falls back to English.

TRANSLATIONS = {
    "en": {
        "app_title": "AGRI EXPERT — PK",
        "app_subtitle": "Intelligent Agricultural Expert System  ::  SWI-Prolog + Python",
        "tab_diagnose": "  DIAGNOSE  ",
        "tab_forward": "  FORWARD CHAIN  ",
        "tab_backward": "  BACKWARD CHAIN ",
        "tab_unification": "  UNIFICATION   ",
        "tab_cf": "  CF ANALYSIS   ",
        "tab_heuristic": "  HEURISTIC     ",
        "tab_kb": "  KB EXPLORER   ",
        "tab_prevention": "  PREVENTION    ",
        "tab_regression": "  ECON DAMAGE   ",
        "input_parameters": " INPUT PARAMETERS",
        "crop": "CROP",
        "symptoms": "SYMPTOMS",
        "weather": "WEATHER",
        "soil": "SOIL CONDITION",
        "run_diagnosis": "▶  RUN DIAGNOSIS",
        "clear": "⟳  CLEAR",
        "city": "CITY (live weather)",
        "fetch_weather": "☁  FETCH LIVE WEATHER",
        "export_csv": "⬇  EXPORT CSV",
        "export_pdf": "⬇  EXPORT PDF",
        "language": "اردو",  # button shows the *other* language
        "ready": "Ready.",
        "diagnosis_results": " DIAGNOSIS RESULTS  —  Backward Chaining + Certainty Factors",
    },
    "ur": {
        "app_title": "ایگری ایکسپرٹ — پاکستان",
        "app_subtitle": "ذہین زرعی ماہر نظام  ::  SWI-Prolog + Python",
        "tab_diagnose": "  تشخیص  ",
        "tab_forward": "  فارورڈ چین  ",
        "tab_backward": "  بیک ورڈ چین ",
        "tab_unification": "  یونیفیکیشن   ",
        "tab_cf": "  یقین کا تجزیہ   ",
        "tab_heuristic": "  ہیورسٹک     ",
        "tab_kb": "  نالج بیس     ",
        "tab_prevention": "  بچاؤ    ",
        "tab_regression": "  معاشی نقصان   ",
        "input_parameters": " ان پٹ",
        "crop": "فصل",
        "symptoms": "علامات",
        "weather": "موسم",
        "soil": "مٹی کی حالت",
        "run_diagnosis": "▶  تشخیص چلائیں",
        "clear": "⟳  صاف کریں",
        "city": "شہر (لائیو موسم)",
        "fetch_weather": "☁  لائیو موسم حاصل کریں",
        "export_csv": "⬇  CSV ایکسپورٹ",
        "export_pdf": "⬇  PDF ایکسپورٹ",
        "language": "English",
        "ready": "تیار۔",
        "diagnosis_results": " تشخیصی نتائج  —  بیک ورڈ چیننگ + یقین کے عوامل",
    },
}


def t(key: str, lang: str = "en") -> str:
    """Translate `key` into `lang`, falling back to English then the raw key."""
    return TRANSLATIONS.get(lang, {}).get(key) or TRANSLATIONS["en"].get(key, key)


# ══════════════════════════════════════════════════════════════
#  EXPORT HELPERS  (CSV / PDF)
# ══════════════════════════════════════════════════════════════

def export_text_report_csv(filepath: str, title: str, rows: list, headers: list = None):
    """
    Write a simple CSV report. `rows` is a list of tuples/lists.
    If `headers` is given it's written as the first row.
    """
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv_module.writer(f)
        writer.writerow([title])
        writer.writerow([])
        if headers:
            writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
    return filepath


def export_text_report_pdf(filepath: str, title: str, body_lines: list):
    """
    Write a simple one-column PDF report from plain text lines.
    Tries reportlab first (best typography); falls back to a hand-rolled
    minimal single-page-per-N-lines PDF writer if reportlab isn't installed,
    so PDF export works even with zero extra dependencies.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(filepath, pagesize=A4)
        width, height = A4
        margin = 18 * mm
        y = height - margin

        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, y, title)
        y -= 10 * mm

        c.setFont("Courier", 9)
        line_height = 4.6 * mm
        for line in body_lines:
            if y < margin:
                c.showPage()
                c.setFont("Courier", 9)
                y = height - margin
            c.drawString(margin, y, line[:110])  # keep within page width
            y -= line_height
        c.save()
        return filepath
    except ImportError:
        return _export_pdf_minimal(filepath, title, body_lines)


def _export_pdf_minimal(filepath: str, title: str, body_lines: list):
    """
    Dependency-free fallback PDF writer (no reportlab). Produces a valid,
    if plain, single/multi-page PDF using raw PDF syntax. Good enough for
    a text report when reportlab isn't installed.
    """
    def esc(s):
        return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")

    lines = [title, ""] + list(body_lines)
    page_lines = 60
    pages = [lines[i:i + page_lines] for i in range(0, len(lines), page_lines)] or [[""]]

    objects = []
    page_obj_ids = []
    content_obj_ids = []

    for page in pages:
        content = "BT /F1 9 Tf 40 800 Td 12 TL\n"
        for ln in page:
            content += f"({esc(ln)}) Tj T*\n"
        content += "ET"
        content_obj_ids.append(content)

    obj_num = 1
    pdf_objs = {}

    font_obj = obj_num; obj_num += 1
    pdf_objs[font_obj] = "<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>"

    content_ids = []
    for content in content_obj_ids:
        cid = obj_num; obj_num += 1
        pdf_objs[cid] = f"<< /Length {len(content)} >>\nstream\n{content}\nendstream"
        content_ids.append(cid)

    page_ids = []
    for cid in content_ids:
        pid = obj_num; obj_num += 1
        pdf_objs[pid] = (
            f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 612 842] "
            f"/Resources << /Font << /F1 {font_obj} 0 R >> >> /Contents {cid} 0 R >>"
        )
        page_ids.append(pid)

    pages_obj = obj_num; obj_num += 1
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    pdf_objs[pages_obj] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>"
    # patch /Parent references
    for pid in page_ids:
        pdf_objs[pid] = pdf_objs[pid].replace("/Parent 0 0 R", f"/Parent {pages_obj} 0 R")

    catalog_obj = obj_num; obj_num += 1
    pdf_objs[catalog_obj] = f"<< /Type /Catalog /Pages {pages_obj} 0 R >>"

    buf = ["%PDF-1.4"]
    offsets = {}
    body = ""
    for num in sorted(pdf_objs.keys()):
        offsets[num] = len("%PDF-1.4\n") + len(body)
        body += f"{num} 0 obj\n{pdf_objs[num]}\nendobj\n"

    xref_start = len("%PDF-1.4\n") + len(body)
    xref = f"xref\n0 {obj_num}\n0000000000 65535 f \n"
    for num in range(1, obj_num):
        xref += f"{offsets.get(num, 0):010d} 00000 n \n"
    trailer = f"trailer\n<< /Size {obj_num} /Root {catalog_obj} 0 R >>\nstartxref\n{xref_start}\n%%EOF"

    with open(filepath, "wb") as f:
        f.write(("%PDF-1.4\n" + body + xref + trailer).encode("latin-1", errors="replace"))
    return filepath
