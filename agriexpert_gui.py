"""

AgriExpert-PK :: Intelligent Agricultural Expert System
GUI Frontend — Python (tkinter + ttk)
Updated: Pure-Python Linear Regression — no sklearn or numpy required.
         Works on any Python version (3.8+, 3.12, 3.14, etc.)

Domain data, the regression engine, and the Prolog bridge now live in
agriexpert_core.py so they can be shared with the headless CLI
(agriexpert_cli.py) without pulling in tkinter.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading, time

import agriexpert_core as core
from agriexpert_core import (
    BASE_DIR, KB_PATH, CROPS, SYMPTOMS, WEATHERS, SOILS, SEASONS,
    DEFAULT_PRICES, DEFAULT_YIELD_PER_HECTARE, TREATMENT_COSTS,
    REGRESSION_TRAINING_DATA, PureLinearRegression, PrologBridge,
    _clip, build_regression_model, fetch_live_weather, WeatherLookupError,
    t, export_text_report_csv, export_text_report_pdf,
)

# ── sklearn / numpy completely removed ──────────────────────────────────────
SKLEARN = True   # always True now; regression is pure Python

C = {
    "bg":          "#0a0802",
    "bg2":         "#141005",
    "bg3":         "#1e1808",
    "border":      "#4a3a10",
    "accent":      "#c8921a",
    "accent2":     "#a8c840",
    "accent3":     "#e8c040",
    "accent4":     "#c03018",
    "accent5":     "#48a8c8",
    "text":        "#f0e8c8",
    "text2":       "#c8a860",
    "text3":       "#c8921a",
    "text_dim":    "#4a3a18",
    "header_bg":   "#070601",
    "sel":         "#2e2408",
    "sel_text":    "#f8f0d8",
}

FONT_MONO  = ("Courier New", 11)
FONT_MONO_S= ("Courier New", 10)
FONT_MONO_L= ("Courier New", 14, "bold")
FONT_HEAD  = ("Courier New", 20, "bold")
FONT_SUB   = ("Courier New", 12, "bold")
FONT_BODY  = ("Courier New", 11)
FONT_TINY  = ("Courier New", 9)
FONT_URDU  = ("Jameel Noori Nastaleeq", 12)   # falls back to default if not installed



# ══════════════════════════════════════════════════════════════
#  STYLED WIDGETS
# ══════════════════════════════════════════════════════════════

def styled_frame(parent, **kw):
    return tk.Frame(parent, bg=C["bg2"], **kw)

def card(parent, **kw):
    return tk.Frame(parent, bg=C["bg2"],
                    highlightbackground=C["border"],
                    highlightthickness=1, **kw)

def label(parent, text, size=10, bold=False, color=None, **kw):
    font = ("Courier New", size, "bold" if bold else "normal")
    return tk.Label(parent, text=text, font=font,
                    fg=color or C["text"], bg=C["bg2"], **kw)

def sep(parent, orient="h"):
    if orient == "h":
        return tk.Frame(parent, bg=C["border"], height=1)
    return tk.Frame(parent, bg=C["border"], width=1)

def accent_button(parent, text, command, color=None, **kw):
    col = color or C["accent"]
    btn = tk.Button(parent, text=text, command=command,
                    font=("Courier New", 10, "bold"),
                    fg=C["bg"], bg=col,
                    activeforeground=C["bg"], activebackground=C["accent2"],
                    relief="flat", cursor="hand2",
                    padx=14, pady=6, **kw)
    btn.bind("<Enter>", lambda e: btn.config(bg=C["accent2"]))
    btn.bind("<Leave>", lambda e: btn.config(bg=col))
    return btn

def output_box(parent, height=12):
    frame = tk.Frame(parent, bg=C["bg"],
                     highlightbackground=C["border"],
                     highlightthickness=1)
    txt = scrolledtext.ScrolledText(frame,
        font=FONT_MONO, bg=C["bg"], fg=C["accent"],
        insertbackground=C["accent"], relief="flat",
        padx=10, pady=8, height=height,
        selectbackground=C["sel"], selectforeground=C["sel_text"],
        wrap=tk.WORD, state="disabled")
    txt.pack(fill="both", expand=True)
    txt.tag_config("disease",  foreground="gold")
    txt.tag_config("label",    foreground="lightblue")
    txt.tag_config("treat",    foreground=C["text"])
    txt.tag_config("cf_high",  foreground="lightgreen")
    txt.tag_config("cf_med",   foreground="gold")
    txt.tag_config("cf_low",   foreground="salmon")
    txt.tag_config("section",  foreground="lightgreen")
    txt.tag_config("err",      foreground="red")
    txt.tag_config("ok",       foreground="lightgreen")
    txt.tag_config("info",     foreground="lightblue")
    txt.tag_config("dim",      foreground=C["text_dim"])
    txt.tag_config("money",    foreground="#f0c040")
    txt.tag_config("warning",  foreground="#ff8040")
    txt.tag_configure("disease", font=("Courier New", 10, "bold"))
    txt.tag_configure("label",   font=("Courier New", 10, "bold"))
    txt.tag_configure("section", font=("Courier New", 10, "bold"))
    txt.tag_configure("cf_high", font=("Courier New", 10, "bold"))
    txt.tag_configure("money",   font=("Courier New", 11, "bold"))
    return frame, txt

def write_out(txt, text, tag="treat"):
    txt.config(state="normal")
    txt.insert("end", text, tag)
    txt.config(state="disabled")
    txt.see("end")

def clear_out(txt):
    txt.config(state="normal")
    txt.delete("1.0", "end")
    txt.config(state="disabled")


# ══════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════

class AgriExpertApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AgriExpert-PK  ::  Intelligent Agricultural Expert System")
        self.geometry("1280x820")
        self.minsize(1100, 700)
        self.configure(bg=C["bg"])
        self.bridge = PrologBridge(KB_PATH)

        self.crop_var    = tk.StringVar(value="wheat")
        self.weather_var = tk.StringVar(value="warm_humid")
        self.soil_var    = tk.StringVar(value="normal_moisture")
        self.season_var  = tk.StringVar(value="kharif")
        self.sym_vars    = {}
        self.disease_var = tk.StringVar(value="rice_blast")
        self.dc_var      = tk.StringVar(value="fungal")
        self.uni_crop_var= tk.StringVar(value="wheat")
        self.uni_sym_var = tk.StringVar(value="yellow_pustules")

        # ── Live weather (city auto-fill) ──
        self.city_var        = tk.StringVar(value="")
        self.weather_src_var = tk.StringVar(value="")   # e.g. "live: Lahore, PK — 31°C"

        # ── Language / i18n ──
        self.lang = "en"
        self._i18n_widgets = []   # (widget, key) pairs refreshed on language toggle

        # ── Last-run outputs cached for CSV/PDF export ──
        self._last_diag_raw   = ""
        self._last_diag_meta  = {}
        self._last_reg_result = {}

        # ── Pure-Python regression model cache ──
        self._reg_model, self._reg_enc_crop, self._reg_enc_wth, self._reg_enc_soil = (
            None, None, None, None
        )

        self._build_ui()
        self._pulse_status()
        self._pretrain_regression()

    # ─────────────────────────────────────────────────────────
    #  PRE-TRAIN REGRESSION AT STARTUP  (pure Python)
    # ─────────────────────────────────────────────────────────

    def _pretrain_regression(self):
        """Train the pure-Python linear regression model at startup (shared core engine)."""
        self._reg_model, self._reg_enc_crop, self._reg_enc_wth, self._reg_enc_soil = (
            build_regression_model()
        )

    # ─────────────────────────────────────────────────────────
    #  UI BUILD
    # ─────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_notebook()
        self._build_statusbar()

    def _build_header(self):
        hdr = tk.Frame(self, bg=C["header_bg"], height=70)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        text_frame = tk.Frame(hdr, bg=C["header_bg"])
        text_frame.pack(side="left", padx=(10,0), pady=8)

        self.hdr_title = tk.Label(text_frame, text=t("app_title", self.lang),
                 font=("Courier New", 20, "bold"),
                 fg=C["accent"], bg=C["header_bg"])
        self.hdr_title.pack(anchor="w")
        self.hdr_subtitle = tk.Label(text_frame,
                 text=t("app_subtitle", self.lang),
                 font=("Courier New", 8),
                 fg=C["text_dim"], bg=C["header_bg"])
        self.hdr_subtitle.pack(anchor="w")

        # ── Language toggle (EN <-> UR) ──
        self.lang_btn = accent_button(hdr, t("language", self.lang),
                                       self._toggle_language, color=C["accent5"])
        self.lang_btn.pack(side="right", padx=(0, 10), pady=20)

        self.status_canvas = tk.Canvas(hdr, width=80, height=70,
                                       bg=C["header_bg"], highlightthickness=0)
        self.status_canvas.pack(side="right", padx=5)
        self.status_dot = self.status_canvas.create_oval(25,25,41,41,
                                                         fill=C["accent"], outline="")
        self.status_canvas.create_text(33, 50, text="KB",
                                       font=FONT_TINY, fill=C["text_dim"])

        badges = ["Backward Chaining","Forward Chaining","Unification",
                  "Certainty Factors","Heuristic Search","Linear Regression"]
        badge_f = tk.Frame(hdr, bg=C["header_bg"])
        badge_f.pack(side="right", padx=5)
        for b in badges:
            tk.Label(badge_f, text=b, font=("Courier New", 7, "bold"),
                     fg=C["bg"], bg=C["accent2"],
                     padx=8, pady=2, relief="flat", width=18).pack(
                         side="left", padx=20, pady=28)

    def _toggle_language(self):
        """Switch the UI between English and Urdu (extensible i18n layer, see agriexpert_core.TRANSLATIONS)."""
        self.lang = "ur" if self.lang == "en" else "en"
        self.hdr_title.config(text=t("app_title", self.lang))
        self.hdr_subtitle.config(text=t("app_subtitle", self.lang))
        self.lang_btn.config(text=t("language", self.lang))
        self.sb_var.set(t("ready", self.lang))
        # Refresh notebook tab labels
        tab_keys = ["tab_diagnose", "tab_forward", "tab_backward", "tab_unification",
                    "tab_cf", "tab_heuristic", "tab_kb", "tab_prevention", "tab_regression"]
        for i, key in enumerate(tab_keys):
            self.nb.tab(i, text=t(key, self.lang))
        # Refresh any widgets registered for i18n (labels/buttons added via _i18n)
        for widget, key, prop in self._i18n_widgets:
            try:
                widget.config(**{prop: t(key, self.lang)})
            except tk.TclError:
                pass

    def _i18n(self, widget, key, prop="text"):
        """Register a widget so its `prop` gets updated on every language toggle."""
        self._i18n_widgets.append((widget, key, prop))
        widget.config(**{prop: t(key, self.lang)})
        return widget

    def _build_notebook(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background=C["bg"], borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=C["bg3"], foreground=C["text_dim"],
                        font=("Courier New", 10, "bold"),
                        padding=[16, 8])
        style.map("TNotebook.Tab",
                  background=[("selected", C["bg2"])],
                  foreground=[("selected", C["accent"])])

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=6, pady=(0,4))

        tabs = [
            ("  DIAGNOSE  ",      self._tab_diagnose),
            ("  FORWARD CHAIN  ", self._tab_forward),
            ("  BACKWARD CHAIN ", self._tab_backward),
            ("  UNIFICATION   ",  self._tab_unification),
            ("  CF ANALYSIS   ",  self._tab_cf),
            ("  HEURISTIC     ",  self._tab_heuristic),
            ("  KB EXPLORER   ",  self._tab_kb),
            ("  PREVENTION    ",  self._tab_prevention),
            ("  ECON DAMAGE   ",  self._tab_regression),
        ]
        for name, builder in tabs:
            frame = tk.Frame(self.nb, bg=C["bg2"])
            self.nb.add(frame, text=name)
            builder(frame)

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=C["bg3"], height=24)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        tk.Label(bar, text=f"KB: {KB_PATH}", font=FONT_TINY,
                 fg=C["text_dim"], bg=C["bg3"]).pack(side="left", padx=10)
        # Always green — pure Python needs no external libs
        tk.Label(bar, text="regression: pure-Python (no sklearn needed)",
                 font=FONT_TINY, fg=C["accent2"], bg=C["bg3"]).pack(
                     side="left", padx=20)
        self.sb_var = tk.StringVar(value="Ready.")
        tk.Label(bar, textvariable=self.sb_var, font=FONT_TINY,
                 fg=C["accent2"], bg=C["bg3"]).pack(side="right", padx=10)

    def _pulse_status(self):
        colors = [C["accent"], C["accent2"], "#2e7d32", C["accent2"]]
        idx = int(time.time()*2) % len(colors)
        self.status_canvas.itemconfig(self.status_dot, fill=colors[idx])
        self.after(500, self._pulse_status)

    # ─────────────────────────────────────────────────────────
    #  SHARED INPUT PANEL
    # ─────────────────────────────────────────────────────────

    def _build_input_panel(self, parent):
        panel = card(parent, width=290)
        panel.pack(side="left", fill="y", padx=(8,4), pady=8)
        panel.pack_propagate(False)

        label(panel, " INPUT PARAMETERS", 11, True, C["accent2"]).pack(
            anchor="w", padx=10, pady=(10,4))
        sep(panel).pack(fill="x", padx=8, pady=4)

        label(panel, "CROP", 9, True, C["accent5"]).pack(anchor="w", padx=12, pady=(6,2))
        crop_dd = ttk.Combobox(panel, textvariable=self.crop_var,
                                values=CROPS, state="readonly",
                                font=FONT_MONO, width=22)
        crop_dd.pack(padx=12, pady=2)
        crop_dd.bind("<<ComboboxSelected>>", self._on_crop_change)
        self._style_combo(crop_dd)

        label(panel, "SYMPTOMS", 9, True, C["accent5"]).pack(anchor="w", padx=12, pady=(10,2))
        self.sym_frame = tk.Frame(panel, bg=C["bg2"])
        self.sym_frame.pack(fill="x", padx=10)
        self._refresh_symptoms()

        sep(panel).pack(fill="x", padx=8, pady=6)

        label(panel, "WEATHER", 9, True, C["accent5"]).pack(anchor="w", padx=12, pady=(2,2))
        w_dd = ttk.Combobox(panel, textvariable=self.weather_var,
                             values=WEATHERS, state="readonly",
                             font=FONT_MONO, width=22)
        w_dd.pack(padx=12, pady=2)
        self._style_combo(w_dd)

        label(panel, "SOIL CONDITION", 9, True, C["accent5"]).pack(anchor="w", padx=12, pady=(8,2))
        s_dd = ttk.Combobox(panel, textvariable=self.soil_var,
                             values=SOILS, state="readonly",
                             font=FONT_MONO, width=22)
        s_dd.pack(padx=12, pady=2)
        self._style_combo(s_dd)

        sep(panel).pack(fill="x", padx=8, pady=6)

        label(panel, "CITY (live weather)", 9, True, C["accent3"]).pack(
            anchor="w", padx=12, pady=(2,2))
        city_entry = tk.Entry(panel, textvariable=self.city_var, font=FONT_MONO,
                               width=22, bg=C["bg3"], fg=C["text"],
                               insertbackground=C["text"], relief="flat")
        city_entry.pack(padx=12, pady=2)
        city_entry.bind("<Return>", lambda e: self._fetch_live_weather())

        accent_button(panel, "☁  FETCH LIVE WEATHER", self._fetch_live_weather,
                      color=C["accent5"]).pack(padx=12, pady=(4,2), fill="x")
        tk.Label(panel, textvariable=self.weather_src_var, font=("Courier New", 8),
                 fg=C["accent2"], bg=C["bg2"], wraplength=250, justify="left").pack(
                     anchor="w", padx=12, pady=(0,4))

        sep(panel).pack(fill="x", padx=8, pady=8)
        return panel

    def _fetch_live_weather(self):
        """Geocode the CITY field and auto-fill WEATHER/SOIL from real current conditions."""
        city = self.city_var.get().strip()
        if not city:
            messagebox.showinfo("Live Weather", "Type a city name first, e.g. Lahore, Multan, Karachi.")
            return
        self.weather_src_var.set("Fetching live weather…")
        self.sb_var.set(f"Looking up weather for {city}...")
        self.update()

        def run():
            try:
                info = fetch_live_weather(city)
                self.after(0, lambda: self._apply_live_weather(info))
            except WeatherLookupError as e:
                self.after(0, lambda: self._weather_fetch_failed(str(e)))

        threading.Thread(target=run, daemon=True).start()

    def _apply_live_weather(self, info):
        self.weather_var.set(info["mapped_weather"])
        self.soil_var.set(info["mapped_soil_hint"])
        self.weather_src_var.set(
            f"live: {info['city']}, {info['country']} — "
            f"{info['temperature_c']}°C, {info['humidity_pct']}% humidity"
        )
        self.sb_var.set("Ready.")

    def _weather_fetch_failed(self, msg):
        self.weather_src_var.set("")
        self.sb_var.set("Ready.")
        messagebox.showerror("Live Weather", f"Could not fetch live weather:\n{msg}")

    def _style_combo(self, combo):
        style = ttk.Style()
        uid = f"G{id(combo)}.TCombobox"
        style.configure(uid,
            fieldbackground=C["bg3"], background=C["bg3"],
            foreground="white", selectbackground="#4caf50",
            selectforeground="black", arrowcolor=C["accent"])
        style.map(uid,
            foreground=[('!focus','white'),('focus','white'),
                        ('readonly','white'),('disabled','#888888')],
            fieldbackground=[('!focus',C["bg3"]),('focus',C["sel"]),
                             ('readonly',C["bg3"])],
            selectbackground=[('!focus','#2e7d32'),('focus','#4caf50')])
        combo.configure(style=uid)

    def _on_crop_change(self, event=None):
        self._refresh_symptoms()

    def _refresh_symptoms(self):
        for w in self.sym_frame.winfo_children():
            w.destroy()
        self.sym_vars.clear()
        crop = self.crop_var.get()
        syms = SYMPTOMS.get(crop, [])
        for s in syms:
            v = tk.BooleanVar()
            self.sym_vars[s] = v
            cb = tk.Checkbutton(self.sym_frame, text=s.replace("_"," "),
                                variable=v, font=FONT_TINY, fg=C["text2"],
                                bg=C["bg2"], selectcolor=C["bg3"],
                                activebackground=C["bg2"],
                                activeforeground=C["accent2"], anchor="w")
            cb.pack(fill="x", pady=1)

    def _get_selected_symptoms(self):
        return [s for s, v in self.sym_vars.items() if v.get()]

    # ─────────────────────────────────────────────────────────
    #  TAB 1 — DIAGNOSE
    # ─────────────────────────────────────────────────────────

    def _tab_diagnose(self, parent):
        panel = self._build_input_panel(parent)

        btn = accent_button(panel, "▶  RUN DIAGNOSIS", self._run_diagnose)
        btn.pack(padx=12, pady=4, fill="x")
        accent_button(panel, "⟳  CLEAR", lambda: clear_out(self.diag_out),
                      color="#37474f").pack(padx=12, pady=2, fill="x")

        exp_f = tk.Frame(panel, bg=C["bg2"])
        exp_f.pack(padx=12, pady=(6,2), fill="x")
        accent_button(exp_f, "⬇ CSV", lambda: self._export_diagnosis("csv"),
                      color=C["accent3"]).pack(side="left", expand=True, fill="x", padx=(0,2))
        accent_button(exp_f, "⬇ PDF", lambda: self._export_diagnosis("pdf"),
                      color=C["accent3"]).pack(side="left", expand=True, fill="x", padx=(2,0))

        right = styled_frame(parent)
        right.pack(side="left", fill="both", expand=True, padx=(4,8), pady=8)

        label(right, " DIAGNOSIS RESULTS  —  Backward Chaining + Certainty Factors",
              10, True, C["accent2"]).pack(anchor="w", padx=10, pady=(8,4))
        sep(right).pack(fill="x", padx=8, pady=2)

        oframe, self.diag_out = output_box(right, height=30)
        oframe.pack(fill="both", expand=True, padx=8, pady=8)
        self._diag_welcome()

    def _diag_welcome(self):
        write_out(self.diag_out,
            "╔══════════════════════════════════════════════════════╗\n"
            "║      AgriExpert-PK  ::  Disease Diagnosis Engine     ║\n"
            "╠══════════════════════════════════════════════════════╣\n"
            "║  1. Select crop from the left panel                  ║\n"
            "║  2. Check one or more observed symptoms              ║\n"
            "║  3. Set weather & soil conditions                    ║\n"
            "║  4. Press  ▶ RUN DIAGNOSIS                           ║\n"
            "╚══════════════════════════════════════════════════════╝\n\n",
            "section")
        write_out(self.diag_out,
            "AI Techniques active:\n"
            "  • Backward Chaining  — goal-driven proof search\n"
            "  • Certainty Factors  — confidence 0–99%\n"
            "  • Unification        — pattern matching facts↔rules\n\n",
            "info")

    def _run_diagnose(self):
        crop    = self.crop_var.get()
        syms    = list(SYMPTOMS.get(crop, []))
        weather = self.weather_var.get()
        soil    = self.soil_var.get()

        self._last_diag_meta = {"crop": crop, "symptoms": syms, "weather": weather, "soil": soil}

        clear_out(self.diag_out)
        write_out(self.diag_out,
            f"▶ Querying Prolog KB...\n"
            f"  crop({crop})\n"
            f"  weather({weather})  soil({soil})\n\n", "dim")
        self.sb_var.set("Running backward-chaining diagnosis...")
        self.update()

        def run():
            result = self.bridge.diagnose(crop, syms, weather, soil)
            self.after(0, lambda: self._display_diag(result))
        threading.Thread(target=run, daemon=True).start()

    def _export_diagnosis(self, fmt):
        if not self._last_diag_raw:
            messagebox.showinfo("Export", "Run a diagnosis first, then export.")
            return
        meta = self._last_diag_meta
        default_name = f"agriexpert_diagnosis_{meta.get('crop','report')}.{fmt}"
        filetypes = [("CSV file", "*.csv")] if fmt == "csv" else [("PDF file", "*.pdf")]
        path = filedialog.asksaveasfilename(defaultextension=f".{fmt}",
                                             initialfile=default_name, filetypes=filetypes)
        if not path:
            return
        try:
            if fmt == "csv":
                rows, cur = [], None
                for line in self._last_diag_raw.splitlines():
                    if line.startswith("DISEASE:"):
                        if cur: rows.append(cur)
                        cur = [line.split("DISEASE:")[-1].strip(), "", "", ""]
                    elif cur and line.startswith("CLASS:"):
                        cur[1] = line.split("CLASS:")[-1].strip()
                    elif cur and line.startswith("CF:"):
                        cur[2] = line.split("CF:")[-1].strip()
                    elif cur and line.startswith("  - "):
                        cur[3] = (cur[3] + "; " if cur[3] else "") + line[4:].strip()
                if cur: rows.append(cur)
                export_text_report_csv(path, f"AgriExpert-PK Diagnosis — {meta.get('crop','')}",
                                        rows, headers=["Disease", "Class", "CF%", "Treatments"])
            else:
                body = [f"Crop: {meta.get('crop','')}",
                        f"Weather: {meta.get('weather','')}   Soil: {meta.get('soil','')}",
                        f"Symptoms: {', '.join(meta.get('symptoms', []))}", ""]
                body += self._last_diag_raw.splitlines()
                export_text_report_pdf(path, "AgriExpert-PK Diagnosis Report", body)
            messagebox.showinfo("Export", f"Report saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    def _display_diag(self, raw):
        self.sb_var.set("Ready.")
        self._last_diag_raw = raw
        txt = self.diag_out
        txt.config(state="normal")

        if raw.startswith("ERROR") or "not found" in raw:
            write_out(txt, raw + "\n", "err")
            return

        diseases = []
        lines = raw.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("DISEASE:"):
                disease_block = {"name": "", "class": "", "cf": 0, "treats": []}
                disease_block["name"] = line.split("DISEASE:")[-1].strip()
                i += 1
                while i < len(lines) and not lines[i].startswith("DISEASE:"):
                    if lines[i].startswith("CLASS:"):
                        disease_block["class"] = lines[i]
                    elif lines[i].startswith("CF:"):
                        try:
                            disease_block["cf"] = int(lines[i].split()[-1])
                        except:
                            pass
                    elif lines[i].startswith("  - "):
                        disease_block["treats"].append(lines[i][4:])
                    i += 1
                diseases.append(disease_block)
            else:
                i += 1

        if not diseases:
            write_out(txt, "No matching disease found.\n", "err")
            txt.config(state="disabled")
            return

        diseases.sort(key=lambda x: x["cf"], reverse=True)
        best = diseases[0]

        write_out(txt, "\n" + "━"*54 + "\n", "dim")
        write_out(txt, f"DISEASE: {best['name']}\n", "disease")
        write_out(txt, f"{best['class']}\n", "label")

        cf = best["cf"]
        tag = "cf_high" if cf >= 80 else ("cf_med" if cf >= 60 else "cf_low")
        bar_len = cf // 5
        bar = "█" * bar_len + "░" * (20 - bar_len)
        write_out(txt, f"CF:      {cf}%\n  [{bar}] {cf}%\n", tag)

        write_out(txt, "\nRecommended Treatments:\n", "section")
        for t in best["treats"]:
            write_out(txt, f"  ✓ {t}\n", "treat")

        write_out(txt, "\n" + "━"*54 + "\n", "dim")
        write_out(txt, "✔ Diagnosis complete — highest confidence disease shown.\n", "ok")
        txt.config(state="disabled")

    # ─────────────────────────────────────────────────────────
    #  TAB 2 — FORWARD CHAINING
    # ─────────────────────────────────────────────────────────

    def _tab_forward(self, parent):
        top = styled_frame(parent)
        top.pack(fill="x", padx=8, pady=(8,4))
        label(top, " FORWARD CHAINING  —  Data-Driven Inference Engine",
              11, True, C["accent2"]).pack(side="left", padx=10)

        sep(parent).pack(fill="x", padx=8)

        expl = card(parent)
        expl.pack(fill="x", padx=8, pady=6)
        label(expl,
              "  Forward chaining starts from FACTS and fires rules to derive new conclusions.\n"
              "  Uses: derive_all/1  →  assert(derived(X))  — iterates until fixed-point.\n"
              "  Example: crop(rice) + weather(warm_humid)  →  blast_favorable, high_fungal_risk",
              9, False, C["text_dim"]).pack(anchor="w", padx=10, pady=6)

        ctrl = styled_frame(parent)
        ctrl.pack(fill="x", padx=8, pady=4)

        def dd(label_txt, var, values, w=18):
            f = tk.Frame(ctrl, bg=C["bg2"])
            f.pack(side="left", padx=10)
            tk.Label(f, text=label_txt, font=FONT_TINY, fg=C["accent5"], bg=C["bg2"]).pack(anchor="w")
            cb = ttk.Combobox(f, textvariable=var, values=values,
                              state="readonly", font=FONT_MONO, width=w)
            cb.pack()
            self._style_combo(cb)
            return cb

        self.fc_crop_var    = tk.StringVar(value="rice")
        self.fc_weather_var = tk.StringVar(value="warm_humid")
        self.fc_soil_var    = tk.StringVar(value="waterlogged")
        self.fc_sym_var     = tk.StringVar(value="yellow_leaf_spots")

        dd("CROP",    self.fc_crop_var,    CROPS)
        dd("WEATHER", self.fc_weather_var, WEATHERS)
        dd("SOIL",    self.fc_soil_var,    SOILS)

        f2 = tk.Frame(ctrl, bg=C["bg2"])
        f2.pack(side="left", padx=10)
        tk.Label(f2, text="SYMPTOM (optional)", font=FONT_TINY,
                 fg=C["accent5"], bg=C["bg2"]).pack(anchor="w")
        self.fc_sym_entry = tk.Entry(f2, textvariable=self.fc_sym_var,
                                     font=FONT_MONO, bg=C["bg3"],
                                     fg=C["text"], insertbackground=C["accent"],
                                     relief="flat", width=24)
        self.fc_sym_entry.pack()

        accent_button(ctrl, "▶ FIRE RULES", self._run_forward).pack(
            side="left", padx=20, pady=4)

        oframe, self.fc_out = output_box(parent, height=22)
        oframe.pack(fill="both", expand=True, padx=8, pady=6)

        write_out(self.fc_out,
            "Select facts above and press ▶ FIRE RULES to run forward chaining.\n"
            "The engine will assert all derivable conclusions step by step.\n", "info")

    def _run_forward(self):
        crop    = self.fc_crop_var.get()
        weather = self.fc_weather_var.get()
        soil    = self.fc_soil_var.get()
        sym     = self.fc_sym_var.get().strip()
        syms    = [sym] if sym else []

        clear_out(self.fc_out)
        write_out(self.fc_out, "⚙ Running forward chaining...\n\n", "dim")
        write_out(self.fc_out, f"  Initial facts: crop({crop}), weather({weather}), soil({soil})\n", "info")
        if syms:
            write_out(self.fc_out, f"  Extra symptom: {syms[0]}\n", "info")
        write_out(self.fc_out, "\n  Derived Conclusions:\n", "section")
        self.sb_var.set("Forward chaining in progress...")
        self.update()

        def run():
            r = self.bridge.forward_chain(crop, syms, weather, soil)
            self.after(0, lambda: self._show_fc(r))
        threading.Thread(target=run, daemon=True).start()

    def _show_fc(self, raw):
        self.sb_var.set("Ready.")
        if not raw or "No forward" in raw:
            write_out(self.fc_out, "  (no conclusions derived)\n", "dim")
            return
        icons = {
            "high_fungal_risk":        "🍄",
            "vector_borne_risk":       "🦟",
            "soil_borne_risk":         "🌱",
            "drought_stress":          "☀",
            "blast_favorable":         "⚠",
            "rust_favorable":          "⚠",
            "whitefly_alert":          "🪲",
            "late_blight_alert":       "🥔",
            "blight_alert":            "🌾",
            "seed_treatment_needed":   "🌿",
            "immediate_action_needed": "🚨",
            "vector_control_urgent":   "⚡",
            "field_drainage_needed":   "💧",
        }
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            key = line.replace(">> ", "").strip()
            icon = icons.get(key, "→")
            write_out(self.fc_out, f"  {icon}  {key}\n", "cf_high")
        write_out(self.fc_out, "\n✔ Forward chaining complete — fixed point reached.\n", "ok")

    # ─────────────────────────────────────────────────────────
    #  TAB 3 — BACKWARD CHAINING
    # ─────────────────────────────────────────────────────────

    def _tab_backward(self, parent):
        label(parent, " BACKWARD CHAINING  —  Goal-Driven Proof Search",
              11, True, C["accent2"]).pack(anchor="w", padx=10, pady=(8,4))
        sep(parent).pack(fill="x", padx=8)

        expl = card(parent)
        expl.pack(fill="x", padx=8, pady=6)
        label(expl,
              "  Backward chaining works GOAL-FIRST: starts with a disease hypothesis and\n"
              "  proves it by matching rule conditions against asserted facts.\n"
              "  Uses: diagnose/3 — Prolog's native depth-first resolution with unification.",
              9, False, C["text_dim"]).pack(anchor="w", padx=10, pady=6)

        tree_frame = card(parent)
        tree_frame.pack(fill="x", padx=8, pady=4)
        label(tree_frame, "  Proof Tree Structure:", 9, True, C["accent5"]).pack(anchor="w", padx=10, pady=(6,2))
        self.tree_canvas = tk.Canvas(tree_frame, bg=C["bg2"], height=120, highlightthickness=0)
        self.tree_canvas.pack(fill="x", padx=10, pady=6)
        self._draw_tree()

        ctrl = styled_frame(parent)
        ctrl.pack(fill="x", padx=8, pady=6)

        self.bc_crop_var = tk.StringVar(value="wheat")
        self.bc_sym_var  = tk.StringVar(value="yellow_pustules")
        self.bc_wth_var  = tk.StringVar(value="cool_wet")
        self.bc_soil_var = tk.StringVar(value="normal_moisture")

        for label_txt, var, values, w in [
            ("CROP",    self.bc_crop_var, CROPS,    14),
            ("WEATHER", self.bc_wth_var,  WEATHERS, 16),
            ("SOIL",    self.bc_soil_var, SOILS,    16),
        ]:
            f = tk.Frame(ctrl, bg=C["bg2"])
            f.pack(side="left", padx=10)
            tk.Label(f, text=label_txt, font=FONT_TINY, fg=C["accent5"], bg=C["bg2"]).pack(anchor="w")
            dd = ttk.Combobox(f, textvariable=var, values=values,
                              state="readonly", font=FONT_MONO, width=w)
            dd.pack()
            self._style_combo(dd)

        f = tk.Frame(ctrl, bg=C["bg2"])
        f.pack(side="left", padx=10)
        tk.Label(f, text="SYMPTOM", font=FONT_TINY, fg=C["accent5"], bg=C["bg2"]).pack(anchor="w")
        tk.Entry(f, textvariable=self.bc_sym_var, font=FONT_MONO,
                 bg=C["bg3"], fg=C["text"], insertbackground=C["accent"],
                 relief="flat", width=26).pack()

        accent_button(ctrl, "▶ PROVE GOAL", self._run_backward).pack(side="left", padx=20)

        oframe, self.bc_out = output_box(parent, height=16)
        oframe.pack(fill="both", expand=True, padx=8, pady=6)

    def _draw_tree(self):
        c = self.tree_canvas
        c.delete("all")
        c.create_rectangle(20, 10, 400, 35, fill=C["bg3"], outline=C["accent3"])
        c.create_text(210, 23, text="GOAL: diagnose(Disease, Type, Tr)",
                      fill=C["accent3"], font=("Courier New", 9, "bold"))
        c.create_text(210, 50, text="↓ match rule head", fill=C["text_dim"], font=("Courier New", 8))
        nodes = [
            (40,  70, 220, 95, "crop(Crop) ?",   C["accent5"]),
            (230, 70, 410, 95, "symptom(S) ?",   C["accent5"]),
            (420, 70, 600, 95, "weather(W) ?",   C["accent5"]),
            (610, 70, 790, 95, "soil(Soil) ?",   C["accent5"]),
        ]
        for x1,y1,x2,y2,txt,col in nodes:
            c.create_rectangle(x1,y1,x2,y2, fill=C["bg3"], outline=col)
            c.create_text((x1+x2)//2, (y1+y2)//2, text=txt, fill=col, font=("Courier New", 8))
            c.create_line(210, 35, (x1+x2)//2, y1, fill=C["border"], dash=(3,3))
        c.create_text(210, 110, text="✔ All conditions unified → rule fires → Disease concluded",
                      fill=C["accent"], font=("Courier New", 8, "bold"))

    def _run_backward(self):
        crop  = self.bc_crop_var.get()
        sym   = self.bc_sym_var.get().strip()
        wth   = self.bc_wth_var.get()
        soil  = self.bc_soil_var.get()
        syms  = [sym] if sym else []

        clear_out(self.bc_out)
        write_out(self.bc_out,
            "  Backward Chaining Trace\n"
            "  ════════════════════════════════════════════════\n", "section")
        write_out(self.bc_out,
            f"  Goal: diagnose(?Disease, ?Type, ?Treatments)\n"
            f"  Given: crop={crop}, symptom={sym}, weather={wth}, soil={soil}\n\n", "info")
        write_out(self.bc_out, "  Attempting goal proof...\n\n", "dim")
        self.sb_var.set("Backward chaining...")

        def run():
            r = self.bridge.diagnose(crop, syms, wth, soil)
            self.after(0, lambda: self._show_bc(r))
        threading.Thread(target=run, daemon=True).start()

    def _show_bc(self, raw):
        self.sb_var.set("Ready.")
        if not raw or raw.startswith("ERROR") or "DISEASE:" not in raw:
            write_out(self.bc_out,
                "  PROOF FAILED — no rule unifies with given facts.\n"
                "  Prolog returns: false.\n", "err")
            return
        lines = raw.split("\n")
        for line in lines:
            if "DISEASE:" in line:
                write_out(self.bc_out,
                    f"  ┌─ RULE MATCHED ─────────────────────────────┐\n"
                    f"  │ {line}\n", "disease")
            elif "CLASS:" in line:
                write_out(self.bc_out, f"  │ {line}\n", "label")
            elif "CF:" in line:
                write_out(self.bc_out, f"  │ {line}%\n", "cf_high")
            elif "TREAT:" in line:
                write_out(self.bc_out, f"  └─ TREATMENTS ─────────────────────────────┘\n", "disease")
            elif line.startswith("  - "):
                write_out(self.bc_out, f"       ✓ {line[4:]}\n", "treat")
        write_out(self.bc_out, "\n  ✔ Backward proof succeeded.\n", "ok")

    # ─────────────────────────────────────────────────────────
    #  TAB 4 — UNIFICATION
    # ─────────────────────────────────────────────────────────

    def _tab_unification(self, parent):
        label(parent, " UNIFICATION  —  Pattern Matching Demonstration",
              11, True, C["accent2"]).pack(anchor="w", padx=10, pady=(8,4))
        sep(parent).pack(fill="x", padx=8)

        expl = card(parent)
        expl.pack(fill="x", padx=8, pady=6)
        label(expl,
              "  Unification is Prolog's core mechanism: binding variables to values so that\n"
              "  two terms become identical. Every rule application uses unification.\n"
              "  Example: crop(X) = crop(wheat)  →  X = wheat  (success)",
              9, False, C["text_dim"]).pack(anchor="w", padx=10, pady=6)

        vis = card(parent)
        vis.pack(fill="x", padx=8, pady=4)
        vc = tk.Canvas(vis, bg=C["bg2"], height=110, highlightthickness=0)
        vc.pack(fill="x", padx=10, pady=6)
        self._draw_unification(vc)

        ctrl = styled_frame(parent)
        ctrl.pack(fill="x", padx=8, pady=6)

        f = tk.Frame(ctrl, bg=C["bg2"])
        f.pack(side="left", padx=10)
        tk.Label(f, text="CROP ATOM", font=FONT_TINY, fg=C["accent5"], bg=C["bg2"]).pack(anchor="w")
        dd = ttk.Combobox(f, textvariable=self.uni_crop_var, values=CROPS,
                          state="readonly", font=FONT_MONO, width=14)
        dd.pack()
        self._style_combo(dd)

        f2 = tk.Frame(ctrl, bg=C["bg2"])
        f2.pack(side="left", padx=10)
        tk.Label(f2, text="SYMPTOM ATOM", font=FONT_TINY, fg=C["accent5"], bg=C["bg2"]).pack(anchor="w")
        tk.Entry(f2, textvariable=self.uni_sym_var, font=FONT_MONO,
                 bg=C["bg3"], fg=C["text"], insertbackground=C["accent"],
                 relief="flat", width=24).pack()

        self.uni_weather_var = tk.StringVar(value="cool_wet")
        f3 = tk.Frame(ctrl, bg=C["bg2"])
        f3.pack(side="left", padx=10)
        tk.Label(f3, text="WEATHER", font=FONT_TINY, fg=C["accent5"], bg=C["bg2"]).pack(anchor="w")
        dd2 = ttk.Combobox(f3, textvariable=self.uni_weather_var, values=WEATHERS,
                           state="readonly", font=FONT_MONO, width=16)
        dd2.pack()
        self._style_combo(dd2)

        accent_button(ctrl, "▶ DEMONSTRATE UNIFICATION", self._run_unification).pack(
            side="left", padx=20)

        oframe, self.uni_out = output_box(parent, height=14)
        oframe.pack(fill="both", expand=True, padx=8, pady=6)

    def _draw_unification(self, c):
        c.delete("all")
        c.create_rectangle(20, 20, 350, 55, fill=C["bg3"], outline=C["accent5"])
        c.create_text(185, 37, text="disease_rule(D, wheat, CF, Tr)",
                      fill=C["accent5"], font=("Courier New", 9))
        c.create_line(350, 37, 430, 37, fill=C["accent3"], arrow="last", width=2)
        c.create_text(390, 27, text="unify", fill=C["accent3"], font=("Courier New", 8))
        c.create_rectangle(430, 20, 780, 55, fill=C["bg3"], outline=C["accent2"])
        c.create_text(605, 37, text="crop(wheat), symptom(S), weather(W), soil(Soil)",
                      fill=C["accent2"], font=("Courier New", 9))
        c.create_text(185, 80, text="D binds → wheat_yellow_rust",
                      fill=C["accent"], font=("Courier New", 9, "bold"))
        c.create_text(605, 80, text="CF binds → 90",
                      fill=C["accent"], font=("Courier New", 9, "bold"))
        c.create_text(400, 105, text="Unification SUCCESS — all variables bound",
                      fill=C["accent3"], font=("Courier New", 9, "bold"))

    def _run_unification(self):
        crop    = self.uni_crop_var.get()
        sym     = self.uni_sym_var.get().strip()
        weather = self.uni_weather_var.get()
        clear_out(self.uni_out)
        self.sb_var.set("Running unification demo...")

        def run():
            r = self.bridge.unification_demo(crop, sym, weather)
            self.after(0, lambda: self._show_uni(r))
        threading.Thread(target=run, daemon=True).start()

    def _show_uni(self, raw):
        self.sb_var.set("Ready.")
        for line in raw.split("\n"):
            if "SUCCEEDED" in line:
                write_out(self.uni_out, line + "\n", "ok")
            elif "FAILED" in line:
                write_out(self.uni_out, line + "\n", "err")
            elif "Unif" in line:
                write_out(self.uni_out, line + "\n", "label")
            else:
                write_out(self.uni_out, line + "\n", "treat")

    # ─────────────────────────────────────────────────────────
    #  TAB 5 — CF ANALYSIS
    # ─────────────────────────────────────────────────────────

    def _tab_cf(self, parent):
        label(parent, " CERTAINTY FACTORS  —  Confidence Scoring System",
              11, True, C["accent2"]).pack(anchor="w", padx=10, pady=(8,4))
        sep(parent).pack(fill="x", padx=8)

        expl = card(parent)
        expl.pack(fill="x", padx=8, pady=6)
        label(expl,
              "  CF ANALYSIS shows ALL diseases for the selected crop ranked by confidence.\n"
              "  The highest CF here always matches the disease shown in the DIAGNOSE tab.\n"
              "  Each rule carries a base CF (0-100) + Weather/Soil/Symptom bonuses.\n"
              "  Final CF = min(99, BaseCF + WeatherBonus + SoilBonus + SymptomBonus)",
              9, False, C["text_dim"]).pack(anchor="w", padx=10, pady=6)

        fc = card(parent)
        fc.pack(fill="x", padx=8, pady=4)
        fcan = tk.Canvas(fc, bg=C["bg2"], height=80, highlightthickness=0)
        fcan.pack(fill="x", padx=10, pady=6)
        self._draw_cf_formula(fcan)

        ctrl = styled_frame(parent)
        ctrl.pack(fill="x", padx=8, pady=6)

        self.cf_crop_var = tk.StringVar(value="rice")
        self.cf_wth_var  = tk.StringVar(value="warm_humid")
        self.cf_soil_var = tk.StringVar(value="waterlogged")

        for lbl, var, values, w in [
            ("CROP",    self.cf_crop_var, CROPS,    14),
            ("WEATHER", self.cf_wth_var,  WEATHERS, 16),
            ("SOIL",    self.cf_soil_var, SOILS,    16),
        ]:
            f = tk.Frame(ctrl, bg=C["bg2"])
            f.pack(side="left", padx=10)
            tk.Label(f, text=lbl, font=FONT_TINY, fg=C["accent5"], bg=C["bg2"]).pack(anchor="w")
            dd = ttk.Combobox(f, textvariable=var, values=values,
                              state="readonly", font=FONT_MONO, width=w)
            dd.pack()
            self._style_combo(dd)

        accent_button(ctrl, "▶ COMPUTE CF", self._run_cf).pack(side="left", padx=20)

        self.cf_bar_frame = card(parent)
        self.cf_bar_frame.pack(fill="x", padx=8, pady=4)
        self.cf_canvas = tk.Canvas(self.cf_bar_frame, bg=C["bg2"],
                                   height=60, highlightthickness=0)
        self.cf_canvas.pack(fill="x", padx=10, pady=6)

        oframe, self.cf_out = output_box(parent, height=12)
        oframe.pack(fill="both", expand=True, padx=8, pady=6)

    def _draw_cf_formula(self, c):
        c.delete("all")
        parts = [
            ("Base CF",       C["accent5"], 20),
            ("+",              C["text_dim"], 110),
            ("Weather Bonus", C["accent3"],  130),
            ("+",              C["text_dim"], 280),
            ("Soil Bonus",    C["accent2"],  300),
            ("+",              C["text_dim"], 420),
            ("Symptom Bonus", C["accent"],   440),
            ("=",              C["text_dim"], 600),
            ("Final CF ≤ 99", C["accent4"],  620),
        ]
        for text, col, x in parts:
            c.create_text(x+60, 35, text=text, fill=col,
                          font=("Courier New", 9, "bold"), anchor="w")
        c.create_text(20, 65,
                      text="  Confidence zones:  0-59 = LOW (red)   60-79 = MEDIUM (amber)   80-99 = HIGH (green)",
                      fill=C["text_dim"], font=("Courier New", 8), anchor="w")

    def _run_cf(self):
        crop = self.cf_crop_var.get()
        wth  = self.cf_wth_var.get()
        soil = self.cf_soil_var.get()
        all_crop_syms = list(SYMPTOMS.get(crop, []))

        clear_out(self.cf_out)
        self.cf_canvas.delete("all")
        write_out(self.cf_out, f"Showing ALL {crop} diseases ranked by confidence...\n\n", "dim")
        self.sb_var.set("Computing CF...")

        def run():
            r = self.bridge.diagnose(crop, all_crop_syms, wth, soil)
            self.after(0, lambda: self._show_cf(r))
        threading.Thread(target=run, daemon=True).start()

    def _show_cf(self, raw):
        self.sb_var.set("Ready.")
        results = []
        current_disease = None
        for line in raw.split("\n"):
            if "DISEASE:" in line:
                current_disease = line.split("DISEASE:")[-1].strip()
            elif "CF:" in line:
                try:
                    cf = int(line.split()[-1])
                    results.append((current_disease, cf))
                except:
                    pass

        seen = {}
        for d, cf in results:
            if d not in seen or cf > seen[d]:
                seen[d] = cf
        results = sorted(seen.items(), key=lambda x: -x[1])

        c = self.cf_canvas
        c.config(height=max(60, 35 * len(results) + 20))
        c.delete("all")
        for i, (d, cf_val) in enumerate(results[:8]):
            y = 10 + i * 32
            col = C["accent2"] if cf_val >= 80 else (C["accent3"] if cf_val >= 60 else C["accent4"])
            bar_w = int((cf_val / 99) * 600)
            c.create_rectangle(200, y, 200+bar_w, y+20, fill=col, outline="")
            c.create_text(195, y+10, text=d, fill=C["text2"],
                          font=("Courier New", 8), anchor="e")
            c.create_text(205+bar_w, y+10, text=f" {cf_val}%", fill=col,
                          font=("Courier New", 8, "bold"), anchor="w")

        write_out(self.cf_out, "Certainty Factor Results (sorted high→low):\n\n", "section")
        for d, cf_val in results:
            tag = "cf_high" if cf_val >= 80 else ("cf_med" if cf_val >= 60 else "cf_low")
            bar = "█" * (cf_val // 5) + "░" * (20 - cf_val // 5)
            level = "HIGH" if cf_val >= 80 else ("MEDIUM" if cf_val >= 60 else "LOW")
            write_out(self.cf_out, f"  {d}\n", "disease")
            write_out(self.cf_out, f"  [{bar}] {cf_val}%  [{level}]\n\n", tag)

        if not results:
            write_out(self.cf_out, "No diseases matched the given conditions.\n", "err")

    # ─────────────────────────────────────────────────────────
    #  TAB 6 — HEURISTIC SEARCH (CORRECTED)
    # ─────────────────────────────────────────────────────────

    def _tab_heuristic(self, parent):
        label(parent, " HEURISTIC SEARCH  —  Best Treatment Selection",
              11, True, C["accent2"]).pack(anchor="w", padx=10, pady=(8,4))
        sep(parent).pack(fill="x", padx=8)

        expl = card(parent)
        expl.pack(fill="x", padx=8, pady=6)
        label(expl,
              "  Heuristic score = (Effectiveness × 2) − Cost − (RecoveryDays / 10)\n"
              "  The treatment with the HIGHEST score is selected as the best option.\n"
              "  Cost: 1=cheap, 5=expensive.  Effectiveness: 1–10.  RecoveryDays: lower=better.",
              9, False, C["text_dim"]).pack(anchor="w", padx=10, pady=6)

        # Corrected: Removed the last two options that lacked evaluation records
        diseases_with_data = [
            "rice_blast","wheat_yellow_rust","cotton_leaf_curl","potato_late_blight"
        ]

        ctrl = styled_frame(parent)
        ctrl.pack(fill="x", padx=8, pady=6)

        self.hs_disease_var = tk.StringVar(value="rice_blast")
        f = tk.Frame(ctrl, bg=C["bg2"])
        f.pack(side="left", padx=10)
        tk.Label(f, text="DISEASE", font=FONT_TINY, fg=C["accent5"], bg=C["bg2"]).pack(anchor="w")
        dd = ttk.Combobox(f, textvariable=self.hs_disease_var,
                          values=diseases_with_data, state="readonly",
                          font=FONT_MONO, width=26)
        dd.pack()
        self._style_combo(dd)

        accent_button(ctrl, "▶ FIND BEST TREATMENT", self._run_heuristic).pack(
            side="left", padx=20)

        sc_frame = card(parent)
        sc_frame.pack(fill="x", padx=8, pady=4)
        label(sc_frame, "  Treatment Score Table  (Effectiveness×2 − Cost − Days/10):",
              9, True, C["accent5"]).pack(anchor="w", padx=10, pady=(6,2))
        self.hs_canvas = tk.Canvas(sc_frame, bg=C["bg2"], height=130, highlightthickness=0)
        self.hs_canvas.pack(fill="x", padx=10, pady=6)
        self._draw_score_table()

        oframe, self.hs_out = output_box(parent, height=14)
        oframe.pack(fill="both", expand=True, padx=8, pady=6)

        write_out(self.hs_out,
            "Select a disease and press ▶ FIND BEST TREATMENT\n"
            "to run the heuristic evaluation.\n", "info")

    def _draw_score_table(self, best_idx=None):
        disease = self.hs_disease_var.get()
        # Corrected: Synced dictionary keys perfectly with the updated dropdown list
        treatment_data = {
            "rice_blast":           [("T1: Tricyclazole spray", 2, 9, 7),
                                     ("T2: Drain field",        1, 6, 3),
                                     ("T3: Resistant variety",  3, 8, 21)],
            "wheat_yellow_rust":    [("T1: Propiconazole spray", 2, 9, 7),
                                     ("T2: Resistant variety",   3, 8, 21),
                                     ("T3: Field sanitation",    1, 5, 14)],
            "cotton_leaf_curl":     [("T1: Imidacloprid spray",  2, 8, 10),
                                     ("T2: Uproot infected",     1, 7, 5),
                                     ("T3: Resistant variety",   3, 9, 21)],
            "potato_late_blight":   [("T1: Metalaxyl spray",     3, 9, 5),
                                     ("T2: Remove infected",     1, 6, 3),
                                     ("T3: Resistant variety",   2, 7, 21)],
        }
        data = treatment_data.get(disease, [
            ("T1: Treatment A", 2, 8, 10),
            ("T2: Treatment B", 1, 6, 5),
            ("T3: Treatment C", 3, 9, 21),
        ])
        rows = []
        for name, cost, eff, days in data:
            score = round((eff * 2) - cost - (days / 10), 1)
            rows.append((name, cost, eff, days, score))
        if best_idx is None:
            best_idx = max(range(len(rows)), key=lambda i: rows[i][4]) + 1

        c = self.hs_canvas
        c.delete("all")
        headers = ["Treatment", "Cost", "Eff", "Days", "Score"]
        widths   = [280, 60, 60, 70, 80]
        xs = [20]
        for w in widths[:-1]:
            xs.append(xs[-1] + w)
        for h, x in zip(headers, xs):
            c.create_text(x+5, 15, text=h, fill=C["accent2"],
                          font=("Courier New", 9, "bold"), anchor="w")
        c.create_line(20, 25, 580, 25, fill=C["border"])
        for row_i, (name, cost, eff, days, score) in enumerate(rows):
            y = 40 + row_i * 28
            is_best = (row_i + 1 == best_idx)
            bg = C["sel"] if is_best else C["bg2"]
            c.create_rectangle(18, y-10, 582, y+15, fill=bg, outline="")
            values = [name, str(cost), str(eff), str(days), f"{score:.1f}"]
            for val, x in zip(values, xs):
                col = C["accent3"] if is_best else C["text2"]
                c.create_text(x+5, y+2, text=val, fill=col,
                              font=("Courier New", 9), anchor="w")
            if is_best:
                c.create_text(580, y+2, text="◀ BEST", fill=C["accent"],
                              font=("Courier New", 8, "bold"), anchor="e")

    def _run_heuristic(self):
        disease = self.hs_disease_var.get()
        clear_out(self.hs_out)
        write_out(self.hs_out, f"Running heuristic search for: {disease}\n\n", "dim")
        self.sb_var.set("Heuristic search...")

        def run():
            r = self.bridge.best_treatment(disease)
            self.after(0, lambda: self._show_hs(r, disease))
        threading.Thread(target=run, daemon=True).start()

    def _show_hs(self, raw, disease):
        self.sb_var.set("Ready.")
        write_out(self.hs_out, f"Disease: {disease}\n", "disease")
        write_out(self.hs_out, "─" * 48 + "\n", "dim")
        best_idx = None
        for line in raw.split("\n"):
            if "Best Treatment Index:" in line:
                try:
                    best_idx = int(line.split(":")[-1].strip())
                except:
                    pass
        self._draw_score_table(best_idx)
        for line in raw.split("\n"):
            if "Best Treatment" in line:
                write_out(self.hs_out, f"  {line}\n", "cf_high")
            elif "Score" in line:
                write_out(self.hs_out, f"  {line}\n", "cf_med")
            elif "Explanation" in line:
                write_out(self.hs_out, f"  {line}\n", "info")
            elif line.strip():
                write_out(self.hs_out, f"  {line}\n", "treat")
        write_out(self.hs_out, "\n✔ Heuristic selection complete.\n", "ok")

    # ─────────────────────────────────────────────────────────
    #  TAB 7 — KB EXPLORER
    # ─────────────────────────────────────────────────────────

    def _tab_kb(self, parent):
        label(parent, " KNOWLEDGE BASE EXPLORER  —  Disease Encyclopedia",
              11, True, C["accent2"]).pack(anchor="w", padx=10, pady=(8,4))
        sep(parent).pack(fill="x", padx=8)

        all_diseases = [
            "rice_blast","wheat_yellow_rust","wheat_brown_rust","wheat_loose_smut",
            "wheat_powdery_mildew","cotton_leaf_curl","cotton_boll_rot",
            "cotton_fusarium_wilt","rice_bacterial_blight","rice_sheath_blight",
            "rice_brown_spot","rice_tungro","maize_smut","maize_downy_mildew",
            "maize_stalk_rot","sugarcane_red_rot","sugarcane_smut",
            "potato_late_blight","potato_early_blight","potato_blackleg",
            "tomato_early_blight","tomato_fusarium_wilt","mango_anthracnose",
            "mango_malformation","citrus_canker","citrus_greening",
        ]

        ctrl = styled_frame(parent)
        ctrl.pack(fill="x", padx=8, pady=6)

        self.kb_disease_var = tk.StringVar(value="rice_blast")
        f = tk.Frame(ctrl, bg=C["bg2"])
        f.pack(side="left", padx=10)
        tk.Label(f, text="SELECT DISEASE", font=FONT_TINY, fg=C["accent5"], bg=C["bg2"]).pack(anchor="w")
        dd = ttk.Combobox(f, textvariable=self.kb_disease_var,
                          values=all_diseases, state="readonly",
                          font=FONT_MONO, width=30)
        dd.pack()
        self._style_combo(dd)

        accent_button(ctrl, "▶ QUERY KB", self._run_kb).pack(side="left", padx=20)
        accent_button(ctrl, "🔍  ALL DISEASES", self._list_all_diseases,
                      color="#37474f").pack(side="left", padx=4)

        oframe, self.kb_out = output_box(parent, height=24)
        oframe.pack(fill="both", expand=True, padx=8, pady=6)

        write_out(self.kb_out,
            "Select a disease above and press ▶ QUERY KB\n"
            "to retrieve all encyclopaedic facts from the Prolog knowledge base.\n\n"
            "Facts include: Pathogen, Disease class, Spread mode,\n"
            "Yield loss range, Resistant varieties, Recommended chemicals.\n", "info")

    def _run_kb(self):
        disease = self.kb_disease_var.get()
        clear_out(self.kb_out)
        write_out(self.kb_out, f"  Querying KB for: {disease}\n\n", "dim")
        self.sb_var.set("KB query...")

        def run():
            r = self.bridge.kb_query(disease.replace(" ","_"), disease)
            self.after(0, lambda: self._show_kb(r, disease))
        threading.Thread(target=run, daemon=True).start()

    def _show_kb(self, raw, disease):
        self.sb_var.set("Ready.")
        write_out(self.kb_out,
            f"╔═══════════════════════════════════════════════════╗\n"
            f"║  DISEASE: {disease.upper():<39}║\n"
            f"╚═══════════════════════════════════════════════════╝\n\n", "disease")
        icons = {"Pathogen":"🔬","Class":"🏷","Spread":"💨",
                 "Yield Loss":"📉","Resistant Varieties":"🌾"}
        for line in raw.split("\n"):
            if not line.strip():
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                icon = icons.get(k.strip(), "•")
                write_out(self.kb_out, f"  {icon}  ", "section")
                write_out(self.kb_out, f"{k.strip():<24}", "label")
                write_out(self.kb_out, f"{v.strip()}\n", "treat")
            else:
                write_out(self.kb_out, line + "\n", "treat")
        write_out(self.kb_out, "\n", "treat")

    def _list_all_diseases(self):
        clear_out(self.kb_out)
        write_out(self.kb_out, "  All diseases in the Knowledge Base:\n\n", "section")
        diseases_by_crop = {
            "WHEAT":     ["wheat_yellow_rust","wheat_brown_rust","wheat_loose_smut","wheat_powdery_mildew"],
            "RICE":      ["rice_blast","rice_bacterial_blight","rice_sheath_blight","rice_brown_spot","rice_tungro"],
            "COTTON":    ["cotton_leaf_curl","cotton_boll_rot","cotton_fusarium_wilt","cotton_alternaria"],
            "MAIZE":     ["maize_smut","maize_downy_mildew","maize_stalk_rot","maize_leaf_blight"],
            "SUGARCANE": ["sugarcane_red_rot","sugarcane_smut","sugarcane_ratoon_stunt"],
            "POTATO":    ["potato_late_blight","potato_early_blight","potato_blackleg"],
            "TOMATO":    ["tomato_early_blight","tomato_fusarium_wilt","tomato_bacterial_spot"],
            "MANGO":     ["mango_anthracnose","mango_malformation"],
            "CITRUS":    ["citrus_canker","citrus_greening"],
        }
        for crop, ds in diseases_by_crop.items():
            write_out(self.kb_out, f"  ── {crop} ────────────────────────\n", "section")
            for d in ds:
                write_out(self.kb_out, f"     • {d}\n", "treat")
            write_out(self.kb_out, "\n", "treat")

    # ─────────────────────────────────────────────────────────
    #  TAB 8 — PREVENTION
    # ─────────────────────────────────────────────────────────

    def _tab_prevention(self, parent):
        label(parent, " PREVENTION ADVISOR  —  Seasonal & Disease-Class Advice",
              11, True, C["accent2"]).pack(anchor="w", padx=10, pady=(8,4))
        sep(parent).pack(fill="x", padx=8)

        ctrl = styled_frame(parent)
        ctrl.pack(fill="x", padx=8, pady=8)

        self.prev_class_var  = tk.StringVar(value="fungal")
        self.prev_season_var = tk.StringVar(value="kharif")

        for lbl, var, values in [
            ("DISEASE CLASS", self.prev_class_var, ["fungal","bacterial","viral"]),
            ("SEASON",        self.prev_season_var, ["kharif","rabi"]),
        ]:
            f = tk.Frame(ctrl, bg=C["bg2"])
            f.pack(side="left", padx=10)
            tk.Label(f, text=lbl, font=FONT_TINY, fg=C["accent5"], bg=C["bg2"]).pack(anchor="w")
            dd = ttk.Combobox(f, textvariable=var, values=values,
                              state="readonly", font=FONT_MONO, width=16)
            dd.pack()
            self._style_combo(dd)

        accent_button(ctrl, "▶ GET PREVENTION ADVICE", self._run_prevention).pack(
            side="left", padx=20)
        accent_button(ctrl, "🌾  SEASONAL TIPS", self._run_seasonal,
                      color="#37474f").pack(side="left", padx=4)

        oframe, self.prev_out = output_box(parent, height=28)
        oframe.pack(fill="both", expand=True, padx=8, pady=6)

        write_out(self.prev_out,
            "Select disease class and season above.\n\n"
            "▶ GET PREVENTION ADVICE  →  Disease-class specific prevention tips\n"
            "🌾 SEASONAL TIPS         →  Season-specific field management advice\n\n"
            "Seasons: Kharif (May-Oct, summer) | Rabi (Nov-Apr, winter)\n", "info")

    def _run_prevention(self):
        dc = self.prev_class_var.get()
        clear_out(self.prev_out)
        write_out(self.prev_out, f"  Prevention Advice for {dc.upper()} diseases:\n\n", "section")
        self.sb_var.set("Fetching prevention advice...")

        def run():
            r = self.bridge.prevention_advice(dc)
            self.after(0, lambda: self._show_prev(r, dc))
        threading.Thread(target=run, daemon=True).start()

    def _show_prev(self, raw, dc):
        self.sb_var.set("Ready.")
        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("* ") or line.startswith("*"):
                write_out(self.prev_out, f"   ✓  {line[2:]}\n", "treat")
            elif line:
                write_out(self.prev_out, f"  {line}\n", "treat")
        write_out(self.prev_out, "\n✔ Prevention advice loaded.\n", "ok")

    def _run_seasonal(self):
        season = self.prev_season_var.get()
        clear_out(self.prev_out)
        write_out(self.prev_out,
            f"  Seasonal Field Management — {season.upper()}\n"
            f"  {'(Kharif: May–October, Summer Crops)' if season=='kharif' else '(Rabi: November–April, Winter Crops)'}\n\n",
            "section")
        self.sb_var.set("Fetching seasonal advice...")

        def run():
            r = self.bridge.seasonal_advice(season)
            self.after(0, lambda: self._show_prev(r, season))
        threading.Thread(target=run, daemon=True).start()

    # ─────────────────────────────────────────────────────────
    #  TAB 9 — ECONOMIC DAMAGE PREDICTOR  (pure-Python regression)
    # ─────────────────────────────────────────────────────────

    def _tab_regression(self, parent):
        label(parent, " ECONOMIC DAMAGE PREDICTOR  —  Linear Regression  (pure Python)",
              11, True, C["accent2"]).pack(anchor="w", padx=10, pady=(8,4))
        sep(parent).pack(fill="x", padx=8)

        expl = card(parent)
        expl.pack(fill="x", padx=8, pady=4)
        label(expl,
              "  Answers: 'How much money will I lose if this disease goes untreated?'\n"
              "  Step 1 — Prolog gives CF score (disease confidence)\n"
              "  Step 2 — Pure-Python OLS regression predicts yield loss% (β = (XᵀX)⁻¹Xᵀy)\n"
              "  Step 3 — Economic model converts loss% → PKR damage & treatment ROI\n"
              "  No sklearn or numpy required — works on any Python version.",
              9, False, C["text_dim"]).pack(anchor="w", padx=10, pady=6)

        main = tk.Frame(parent, bg=C["bg2"])
        main.pack(fill="both", expand=True, padx=8, pady=4)

        # LEFT: inputs
        left = card(main, width=310)
        left.pack(side="left", fill="y", padx=(0,4), pady=0)
        left.pack_propagate(False)

        label(left, " FIELD PARAMETERS", 10, True, C["accent5"]).pack(
            anchor="w", padx=10, pady=(10,4))
        sep(left).pack(fill="x", padx=8, pady=4)

        self.reg_crop_var    = tk.StringVar(value="wheat")
        self.reg_weather_var = tk.StringVar(value="cool_wet")
        self.reg_soil_var    = tk.StringVar(value="normal_moisture")

        for lbl_txt, var, values, w in [
            ("CROP",          self.reg_crop_var,    CROPS,    20),
            ("WEATHER",       self.reg_weather_var, WEATHERS, 20),
            ("SOIL CONDITION",self.reg_soil_var,    SOILS,    20),
        ]:
            f = tk.Frame(left, bg=C["bg2"])
            f.pack(fill="x", padx=12, pady=(6,2))
            tk.Label(f, text=lbl_txt, font=FONT_TINY,
                     fg=C["accent5"], bg=C["bg2"]).pack(anchor="w")
            dd = ttk.Combobox(f, textvariable=var, values=values,
                              state="readonly", font=FONT_MONO, width=w)
            dd.pack(anchor="w")
            self._style_combo(dd)

        sep(left).pack(fill="x", padx=8, pady=8)

        # CF Slider
        cf_f = tk.Frame(left, bg=C["bg2"])
        cf_f.pack(fill="x", padx=12, pady=4)
        tk.Label(cf_f, text="DISEASE CF SCORE  (from Diagnosis tab)",
                 font=FONT_TINY, fg=C["accent5"], bg=C["bg2"]).pack(anchor="w")
        self.reg_cf_var   = tk.IntVar(value=80)
        self.reg_cf_disp  = tk.Label(cf_f, text="80%",
                                      font=("Courier New", 14, "bold"),
                                      fg=C["accent3"], bg=C["bg2"])
        self.reg_cf_disp.pack(anchor="w")
        cf_slider = tk.Scale(cf_f, from_=0, to=99,
                             orient="horizontal", variable=self.reg_cf_var,
                             bg=C["bg2"], fg=C["text"], troughcolor=C["bg3"],
                             highlightthickness=0, length=260,
                             command=lambda v: self.reg_cf_disp.config(text=f"{v}%"))
        cf_slider.pack(anchor="w")

        sep(left).pack(fill="x", padx=8, pady=8)

        # Field size
        fs_f = tk.Frame(left, bg=C["bg2"])
        fs_f.pack(fill="x", padx=12, pady=4)
        tk.Label(fs_f, text="FIELD SIZE (Hectares)",
                 font=FONT_TINY, fg=C["accent5"], bg=C["bg2"]).pack(anchor="w")
        self.reg_hectares_var = tk.StringVar(value="2.0")
        tk.Entry(fs_f, textvariable=self.reg_hectares_var,
                 font=FONT_MONO, bg=C["bg3"], fg=C["text"],
                 insertbackground=C["accent"], relief="flat", width=12).pack(anchor="w")

        # Market price
        mp_f = tk.Frame(left, bg=C["bg2"])
        mp_f.pack(fill="x", padx=12, pady=4)
        tk.Label(mp_f, text="MARKET PRICE (PKR per Maund / 40kg)",
                 font=FONT_TINY, fg=C["accent5"], bg=C["bg2"]).pack(anchor="w")
        self.reg_price_var = tk.StringVar(value="4000")
        tk.Entry(mp_f, textvariable=self.reg_price_var,
                 font=FONT_MONO, bg=C["bg3"], fg=C["text"],
                 insertbackground=C["accent"], relief="flat", width=12).pack(anchor="w")
        self.reg_crop_var.trace_add("write", self._on_reg_crop_change)

        sep(left).pack(fill="x", padx=8, pady=8)

        # Treatment type
        tt_f = tk.Frame(left, bg=C["bg2"])
        tt_f.pack(fill="x", padx=12, pady=4)
        tk.Label(tt_f, text="TREATMENT TYPE (for ROI calc)",
                 font=FONT_TINY, fg=C["accent5"], bg=C["bg2"]).pack(anchor="w")
        self.reg_treat_var = tk.StringVar(value="fungicide")
        tt_dd = ttk.Combobox(tt_f, textvariable=self.reg_treat_var,
                              values=["fungicide","pesticide","biocontrol"],
                              state="readonly", font=FONT_MONO, width=16)
        tt_dd.pack(anchor="w")
        self._style_combo(tt_dd)

        sep(left).pack(fill="x", padx=8, pady=10)

        accent_button(left, "▶  CALCULATE ECONOMIC DAMAGE",
                      self._run_regression).pack(padx=12, pady=4, fill="x")
        accent_button(left, "⟳  CLEAR",
                      lambda: (clear_out(self.reg_out), self._draw_reg_plot()),
                      color="#37474f").pack(padx=12, pady=2, fill="x")

        exp_f = tk.Frame(left, bg=C["bg2"])
        exp_f.pack(padx=12, pady=(6,2), fill="x")
        accent_button(exp_f, "⬇ CSV", lambda: self._export_regression("csv"),
                      color=C["accent3"]).pack(side="left", expand=True, fill="x", padx=(0,2))
        accent_button(exp_f, "⬇ PDF", lambda: self._export_regression("pdf"),
                      color=C["accent3"]).pack(side="left", expand=True, fill="x", padx=(2,0))

        # RIGHT: plot + output
        right = tk.Frame(main, bg=C["bg2"])
        right.pack(side="left", fill="both", expand=True, padx=(4,0))

        plot_card = card(right)
        plot_card.pack(fill="x", pady=(0,4))
        label(plot_card,
              "  Regression Plot  — CF Score vs Predicted Yield Loss%  （● = same-crop data）",
              9, True, C["accent5"]).pack(anchor="w", padx=10, pady=(6,2))
        self.reg_canvas = tk.Canvas(plot_card, bg=C["bg2"],
                                    height=200, highlightthickness=0)
        self.reg_canvas.pack(fill="x", padx=10, pady=6)
        self._draw_reg_plot()

        oframe, self.reg_out = output_box(right, height=14)
        oframe.pack(fill="both", expand=True, pady=4)

        write_out(self.reg_out,
            "╔══════════════════════════════════════════════════════╗\n"
            "║       Economic Damage Predictor  —  How It Works     ║\n"
            "╠══════════════════════════════════════════════════════╣\n"
            "║  1. Get CF score from the DIAGNOSE tab               ║\n"
            "║  2. Enter that CF value using the slider              ║\n"
            "║  3. Set field size & current market price            ║\n"
            "║  4. Press ▶ CALCULATE ECONOMIC DAMAGE                ║\n"
            "╠══════════════════════════════════════════════════════╣\n"
            "║  Output:  Yield loss %  →  Maunds lost  →  PKR loss ║\n"
            "║           Treatment cost  →  Net savings (ROI)      ║\n"
            "╚══════════════════════════════════════════════════════╝\n\n",
            "section")
        write_out(self.reg_out,
            "  Regression engine: pure Python OLS — no sklearn/numpy needed.\n"
            "  Algorithm: Normal Equation  β = (XᵀX)⁻¹Xᵀy\n\n",
            "info")

    def _on_reg_crop_change(self, *args):
        crop = self.reg_crop_var.get()
        self.reg_price_var.set(str(DEFAULT_PRICES.get(crop, 4000)))

    def _draw_reg_plot(self, scatter_pts=None, line_pts=None,
                        pred_cf=None, pred_loss=None):
        c = self.reg_canvas
        c.delete("all")

        W = 900
        H = 190
        PL, PR, PT, PB = 55, 20, 15, 35

        c.create_line(PL, PT, PL, H-PB, fill=C["border"], width=1)
        c.create_line(PL, H-PB, W-PR, H-PB, fill=C["border"], width=1)
        c.create_text(PL + (W-PL-PR)//2, H-8,
                      text="CF Score  (0 → 99)  →",
                      fill=C["text_dim"], font=("Courier New", 8))
        c.create_text(14, PT + (H-PT-PB)//2,
                      text="Loss\n  %",
                      fill=C["text_dim"], font=("Courier New", 7))

        if not scatter_pts:
            c.create_text(W//2, H//2,
                          text="Press  ▶ CALCULATE ECONOMIC DAMAGE  to generate plot",
                          fill=C["text_dim"], font=("Courier New", 9))
            return

        max_loss = max((p[1] for p in scatter_pts), default=60)
        max_loss = max(max_loss, 60)

        def sx(cf):
            return PL + int(cf / 99 * (W - PL - PR))
        def sy(loss):
            return H - PB - int(loss / max_loss * (H - PT - PB))

        for tick in range(0, int(max_loss)+1, 10):
            ty = sy(tick)
            c.create_line(PL-4, ty, PL, ty, fill=C["border"])
            c.create_text(PL-7, ty, text=str(tick),
                          fill=C["text_dim"], font=("Courier New", 7), anchor="e")

        for tick in range(0, 100, 20):
            tx = sx(tick)
            c.create_line(tx, H-PB, tx, H-PB+4, fill=C["border"])
            c.create_text(tx, H-PB+10, text=str(tick),
                          fill=C["text_dim"], font=("Courier New", 7))

        if line_pts and len(line_pts) >= 2:
            pts_sorted = sorted(line_pts, key=lambda p: p[0])
            for i in range(len(pts_sorted)-1):
                x1 = sx(pts_sorted[i][0]);   y1 = sy(pts_sorted[i][1])
                x2 = sx(pts_sorted[i+1][0]); y2 = sy(pts_sorted[i+1][1])
                c.create_line(x1, y1, x2, y2,
                              fill=C["accent2"], width=2, dash=(6,3))

        for cf_v, loss_v, is_crop in scatter_pts:
            col = C["accent"]   if is_crop else C["text_dim"]
            r   = 5             if is_crop else 2
            c.create_oval(sx(cf_v)-r, sy(loss_v)-r,
                          sx(cf_v)+r, sy(loss_v)+r,
                          fill=col, outline="")

        if pred_cf is not None and pred_loss is not None:
            px, py = sx(pred_cf), sy(pred_loss)
            c.create_oval(px-8, py-8, px+8, py+8,
                          fill=C["accent4"], outline=C["accent3"], width=2)
            lbl = f"CF={pred_cf}% → Loss={pred_loss:.1f}%"
            c.create_text(min(px+14, W-120), py,
                          text=lbl, fill=C["accent3"],
                          font=("Courier New", 9, "bold"), anchor="w")

        c.create_oval(W-160, 12, W-152, 20, fill=C["accent"],   outline="")
        c.create_text(W-148, 16, text="same crop", fill=C["text_dim"],
                      font=("Courier New", 7), anchor="w")
        c.create_oval(W-160, 28, W-152, 36, fill=C["text_dim"], outline="")
        c.create_text(W-148, 32, text="other crops", fill=C["text_dim"],
                      font=("Courier New", 7), anchor="w")
        c.create_line(W-160, 46, W-120, 46, fill=C["accent2"], width=2, dash=(5,3))
        c.create_text(W-116, 46, text="fit line", fill=C["text_dim"],
                      font=("Courier New", 7), anchor="w")

    def _export_regression(self, fmt):
        if not self._last_reg_result:
            messagebox.showinfo("Export", "Run a calculation first, then export.")
            return
        res = self._last_reg_result
        default_name = f"agriexpert_econ_damage_{res.get('crop','report')}.{fmt}"
        filetypes = [("CSV file", "*.csv")] if fmt == "csv" else [("PDF file", "*.pdf")]
        path = filedialog.asksaveasfilename(defaultextension=f".{fmt}",
                                             initialfile=default_name, filetypes=filetypes)
        if not path:
            return
        try:
            if fmt == "csv":
                export_text_report_csv(path, f"AgriExpert-PK Economic Damage — {res.get('crop','')}",
                                        [[k, v] for k, v in res.items()], headers=["Field", "Value"])
            else:
                body = [f"{k}: {v}" for k, v in res.items()]
                export_text_report_pdf(path, "AgriExpert-PK Economic Damage Report", body)
            messagebox.showinfo("Export", f"Report saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    def _run_regression(self):
        if self._reg_model is None:
            messagebox.showerror("Error", "Regression model not initialised.")
            return

        crop    = self.reg_crop_var.get()
        weather = self.reg_weather_var.get()
        soil    = self.reg_soil_var.get()
        cf_val  = self.reg_cf_var.get()

        try:
            hectares = float(self.reg_hectares_var.get())
            if hectares <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Input Error", "Field size must be a positive number.")
            return

        try:
            price_per_maund = float(self.reg_price_var.get())
            if price_per_maund <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Input Error", "Market price must be a positive number.")
            return

        treat_type = self.reg_treat_var.get()

        clear_out(self.reg_out)
        write_out(self.reg_out, "⚙ Running pure-Python regression model...\n\n", "dim")
        self.sb_var.set("Predicting economic damage...")
        self.update()

        def run():
            w_idx = self._reg_enc_wth.get(weather, 0)
            s_idx = self._reg_enc_soil.get(soil, 0)
            c_idx = self._reg_enc_crop.get(crop, 0)

            # Predict yield loss % — pure Python, no numpy
            x_pred      = [[c_idx, cf_val, w_idx, s_idx]]
            raw_pred     = self._reg_model.predict(x_pred)[0]
            pred_loss_pct = _clip(raw_pred, 0.0, 100.0)

            # R² on training data
            X_all = [[self._reg_enc_crop.get(r[0], 0),
                       float(r[1]), float(r[2]), float(r[3])]
                     for r in REGRESSION_TRAINING_DATA]
            y_all = [float(r[4]) for r in REGRESSION_TRAINING_DATA]
            r2 = self._reg_model.score(X_all, y_all)

            # Regression line for plot
            line_pts = []
            for cf_x in range(0, 100, 5):
                xp  = [[c_idx, float(cf_x), w_idx, s_idx]]
                lp  = _clip(self._reg_model.predict(xp)[0], 0.0, 100.0)
                line_pts.append((cf_x, lp))

            # Scatter from training data
            scatter_pts = [
                (row[1], row[4], row[0] == crop)
                for row in REGRESSION_TRAINING_DATA
            ]

            # Economic calculation
            yield_per_ha     = DEFAULT_YIELD_PER_HECTARE.get(crop, 60)
            total_yield      = yield_per_ha * hectares
            lost_maunds      = total_yield * (pred_loss_pct / 100.0)
            loss_pkr         = lost_maunds * price_per_maund

            treat_cost_per_ha = TREATMENT_COSTS.get(crop, {}).get(treat_type, 4000)
            total_treat_cost  = treat_cost_per_ha * hectares

            treatment_efficacy = 0.70
            saved_maunds = lost_maunds * treatment_efficacy
            saved_pkr    = saved_maunds * price_per_maund
            net_saving   = saved_pkr - total_treat_cost
            roi_pct      = (net_saving / total_treat_cost * 100) if total_treat_cost > 0 else 0

            self.after(0, lambda: self._show_regression(
                pred_loss_pct, r2, hectares, price_per_maund,
                total_yield, lost_maunds, loss_pkr,
                total_treat_cost, saved_pkr, net_saving, roi_pct,
                crop, weather, soil, cf_val, treat_type,
                scatter_pts, line_pts
            ))

        threading.Thread(target=run, daemon=True).start()

    def _show_regression(self, pred_loss, r2,
                          hectares, price_per_maund,
                          total_yield, lost_maunds, loss_pkr,
                          treat_cost, saved_pkr, net_saving, roi_pct,
                          crop, weather, soil, cf_val, treat_type,
                          scatter_pts, line_pts):
        self.sb_var.set("Ready.")

        self._last_reg_result = {
            "crop": crop, "weather": weather, "soil": soil, "cf_score": cf_val,
            "treatment": treat_type, "predicted_loss_pct": round(pred_loss, 2),
            "model_r2": round(r2, 3), "hectares": hectares,
            "price_per_maund_pkr": price_per_maund,
            "total_yield_maunds": round(total_yield, 1),
            "lost_maunds": round(lost_maunds, 1),
            "estimated_loss_pkr": round(loss_pkr, 0),
            "treatment_cost_pkr": round(treat_cost, 0),
            "value_saved_pkr": round(saved_pkr, 0),
            "net_saving_pkr": round(net_saving, 0),
            "roi_pct": round(roi_pct, 1),
            "decision": "treat immediately" if net_saving > 0 else "marginal — consider alternatives",
        }

        self._draw_reg_plot(
            scatter_pts=scatter_pts,
            line_pts=line_pts,
            pred_cf=cf_val,
            pred_loss=pred_loss
        )

        txt = self.reg_out

        write_out(txt, "┌─ REGRESSION MODEL (pure Python OLS) ───────────────┐\n", "dim")
        write_out(txt, f"   Crop:     {crop:<18}  CF Score: {cf_val}%\n", "info")
        write_out(txt, f"   Weather: {weather:<18}  Soil:     {soil}\n", "info")
        write_out(txt,
            f"   Coefficients:  β_crop={self._reg_model.coef_[0]:+.2f}  "
            f"β_cf={self._reg_model.coef_[1]:+.2f}  "
            f"β_weather={self._reg_model.coef_[2]:+.2f}  "
            f"β_soil={self._reg_model.coef_[3]:+.2f}\n", "dim")
        write_out(txt,
            f"   Intercept: {self._reg_model.intercept_:+.2f}   "
            f"Model R²: {r2:.3f}   "
            f"Training samples: {len(REGRESSION_TRAINING_DATA)}\n", "dim")
        write_out(txt, "└────────────────────────────────────────────────────┘\n\n", "dim")

        loss_tag = ("cf_low" if pred_loss > 35
                    else ("cf_med" if pred_loss > 20 else "cf_high"))
        write_out(txt, "  PREDICTED YIELD LOSS\n", "section")
        bar_len = int(pred_loss / 2)
        bar = "█" * bar_len + "░" * (50 - bar_len)
        write_out(txt, f"  [{bar}] {pred_loss:.1f}%\n\n", loss_tag)

        write_out(txt, "┌─ FIELD ECONOMICS ──────────────────────────────────┐\n", "dim")
        write_out(txt, f"  Field size          : {hectares:.1f} hectares\n", "treat")
        write_out(txt, f"  Expected total yield: {total_yield:.0f} maunds\n", "treat")
        write_out(txt, f"  Market price        : PKR {price_per_maund:,.0f} / maund\n", "treat")
        write_out(txt, f"  Predicted loss      : {lost_maunds:.1f} maunds  ({pred_loss:.1f}%)\n",
                  loss_tag)
        write_out(txt, f"\n  ► ESTIMATED CROP LOSS  :  PKR {loss_pkr:>12,.0f}\n", "money")
        write_out(txt, "└────────────────────────────────────────────────────┘\n\n", "dim")

        write_out(txt, "┌─ TREATMENT ROI ANALYSIS ───────────────────────────┐\n", "dim")
        write_out(txt, f"  Treatment type       : {treat_type}\n", "treat")
        write_out(txt, f"  Treatment cost       : PKR {treat_cost:>10,.0f}  ({hectares:.1f} ha)\n",
                  "treat")
        write_out(txt, f"  Crop saved (est 70%) : {lost_maunds*0.7:.1f} maunds\n", "treat")
        write_out(txt, f"  Value of saved crop  : PKR {saved_pkr:>10,.0f}\n", "treat")

        net_tag = "cf_high" if net_saving > 0 else "cf_low"
        write_out(txt, f"\n  ► NET SAVING IF TREATED:  PKR {net_saving:>10,.0f}\n", "money")

        decision = "YES — treat immediately" if net_saving > 0 else "MARGINAL — consider alternatives"
        dec_tag  = "ok" if net_saving > 0 else "warning"
        write_out(txt, f"  ► ROI                  :  {roi_pct:+.1f}%\n", net_tag)
        write_out(txt, f"  ► TREATMENT DECISION   :  {decision}\n", dec_tag)
        write_out(txt, "└────────────────────────────────────────────────────┘\n\n", "dim")

        if pred_loss > 40:
            risk, rtag = "🚨  CRITICAL RISK  — Act within 48 hours", "cf_low"
        elif pred_loss > 25:
            risk, rtag = "⚠   HIGH RISK     — Schedule treatment this week", "warning"
        elif pred_loss > 12:
            risk, rtag = "⚡  MEDIUM RISK    — Monitor and prepare", "cf_med"
        else:
            risk, rtag = "✔   LOW RISK      — Routine monitoring sufficient", "cf_high"

        write_out(txt, f"  {risk}\n\n", rtag)
        write_out(txt, "✔ Economic damage prediction complete.\n", "ok")


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = AgriExpertApp()
    app.mainloop()