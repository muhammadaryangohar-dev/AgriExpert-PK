#!/usr/bin/env python3
"""
AgriExpert-PK :: Headless CLI
==============================
Run diagnosis, forward chaining, and economic-damage regression from the
terminal or scripts — no GUI, no display server required. Reuses the exact
same Prolog KB and regression engine as the desktop app (agriexpert_core.py).

Examples
--------
  # Diagnose wheat with two observed symptoms
  python agriexpert_cli.py diagnose --crop wheat \\
      --symptoms yellow_pustules orange_pustules \\
      --weather warm_humid --soil normal_moisture

  # Same, but auto-fill weather from a real city and export a PDF report
  python agriexpert_cli.py diagnose --crop rice --symptoms diamond_shaped_lesions \\
      --city Lahore --export-pdf report.pdf

  # Forward-chain from asserted facts
  python agriexpert_cli.py forward --crop cotton --symptoms mosaic_pattern \\
      --weather hot_dry --soil dry_cracked

  # Predict economic loss + treatment ROI for a field
  python agriexpert_cli.py regression --crop rice --cf 82 --weather cool_wet \\
      --soil waterlogged --hectares 5 --price 6000 --treatment fungicide \\
      --export-csv loss_report.csv

  # Look up live weather for a city (no diagnosis)
  python agriexpert_cli.py weather --city Multan

  # List valid crops / symptoms for scripting
  python agriexpert_cli.py list-crops
  python agriexpert_cli.py list-symptoms --crop maize

Every command supports --json for machine-readable output, so this CLI can
be wired into cron jobs, CI regression checks, or other tools.
"""

import argparse
import json
import sys

import agriexpert_core as core


def _resolve_weather_soil(args):
    """Apply --city live-weather override on top of --weather/--soil flags."""
    weather, soil, weather_info = args.weather, args.soil, None
    if getattr(args, "city", None):
        try:
            weather_info = core.fetch_live_weather(args.city)
            weather = weather_info["mapped_weather"]
            if not args.soil:
                soil = weather_info["mapped_soil_hint"]
        except core.WeatherLookupError as e:
            print(f"WARNING: live weather lookup failed ({e}); "
                  f"falling back to --weather/--soil flags.", file=sys.stderr)
    if not weather:
        weather = "moderate"
    if not soil:
        soil = "normal_moisture"
    return weather, soil, weather_info


def cmd_diagnose(args):
    bridge = core.PrologBridge()
    weather, soil, w_info = _resolve_weather_soil(args)
    symptoms = args.symptoms or core.SYMPTOMS.get(args.crop, [])

    raw = bridge.diagnose(args.crop, symptoms, weather, soil)

    if args.json:
        print(json.dumps({
            "crop": args.crop, "symptoms": symptoms, "weather": weather, "soil": soil,
            "weather_source": w_info, "raw_output": raw,
        }, indent=2))
    else:
        print(f"crop={args.crop}  weather={weather}  soil={soil}")
        if w_info:
            print(f"(live weather for {w_info['city']}: "
                  f"{w_info['temperature_c']}°C, {w_info['humidity_pct']}% humidity)")
        print("-" * 60)
        print(raw)

    if args.export_csv:
        rows = _parse_diagnosis_rows(raw)
        core.export_text_report_csv(args.export_csv, f"AgriExpert-PK Diagnosis — {args.crop}",
                                     rows, headers=["Disease", "Class", "CF%", "Treatments"])
        print(f"\n✔ CSV report written to {args.export_csv}", file=sys.stderr)
    if args.export_pdf:
        body = [f"Crop: {args.crop}", f"Weather: {weather}   Soil: {soil}", ""] + raw.splitlines()
        core.export_text_report_pdf(args.export_pdf, f"AgriExpert-PK Diagnosis Report", body)
        print(f"✔ PDF report written to {args.export_pdf}", file=sys.stderr)

    return 0


def _parse_diagnosis_rows(raw):
    rows, cur = [], None
    for line in raw.splitlines():
        if line.startswith("DISEASE:"):
            if cur:
                rows.append(cur)
            cur = [line.split("DISEASE:")[-1].strip(), "", "", ""]
        elif cur and line.startswith("CLASS:"):
            cur[1] = line.split("CLASS:")[-1].strip()
        elif cur and line.startswith("CF:"):
            cur[2] = line.split("CF:")[-1].strip()
        elif cur and line.startswith("  - "):
            cur[3] = (cur[3] + "; " if cur[3] else "") + line[4:].strip()
    if cur:
        rows.append(cur)
    return rows


def cmd_forward(args):
    bridge = core.PrologBridge()
    weather, soil, _ = _resolve_weather_soil(args)
    symptoms = args.symptoms or core.SYMPTOMS.get(args.crop, [])
    raw = bridge.forward_chain(args.crop, symptoms, weather, soil)
    if args.json:
        print(json.dumps({"crop": args.crop, "weather": weather, "soil": soil, "raw_output": raw}, indent=2))
    else:
        print(raw)
    return 0


def cmd_regression(args):
    model, enc_crop, enc_wth, enc_soil = core.build_regression_model()
    w_idx = enc_wth.get(args.weather, 0)
    s_idx = enc_soil.get(args.soil, 0)
    c_idx = enc_crop.get(args.crop, 0)

    pred_loss = core._clip(model.predict([[c_idx, args.cf, w_idx, s_idx]])[0], 0.0, 100.0)

    yield_per_ha = core.DEFAULT_YIELD_PER_HECTARE.get(args.crop, 60)
    total_yield = yield_per_ha * args.hectares
    lost_maunds = total_yield * (pred_loss / 100.0)
    loss_pkr = lost_maunds * args.price

    treat_cost_per_ha = core.TREATMENT_COSTS.get(args.crop, {}).get(args.treatment, 4000)
    total_treat_cost = treat_cost_per_ha * args.hectares

    treatment_efficacy = 0.70
    saved_maunds = lost_maunds * treatment_efficacy
    saved_pkr = saved_maunds * args.price
    net_saving = saved_pkr - total_treat_cost
    roi_pct = (net_saving / total_treat_cost * 100) if total_treat_cost > 0 else 0

    result = {
        "crop": args.crop, "cf": args.cf, "weather": args.weather, "soil": args.soil,
        "predicted_loss_pct": round(pred_loss, 2),
        "hectares": args.hectares, "price_per_maund_pkr": args.price,
        "total_yield_maunds": round(total_yield, 1),
        "lost_maunds": round(lost_maunds, 1),
        "loss_pkr": round(loss_pkr, 0),
        "treatment": args.treatment,
        "treatment_cost_pkr": round(total_treat_cost, 0),
        "net_saving_pkr": round(net_saving, 0),
        "roi_pct": round(roi_pct, 1),
        "decision": "treat immediately" if net_saving > 0 else "marginal — consider alternatives",
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Predicted yield loss : {result['predicted_loss_pct']}%")
        print(f"Estimated crop loss  : PKR {result['loss_pkr']:,.0f}")
        print(f"Treatment cost       : PKR {result['treatment_cost_pkr']:,.0f}")
        print(f"Net saving if treated: PKR {result['net_saving_pkr']:,.0f}  (ROI {result['roi_pct']:+.1f}%)")
        print(f"Decision             : {result['decision']}")

    if args.export_csv:
        core.export_text_report_csv(
            args.export_csv, f"AgriExpert-PK Economic Damage — {args.crop}",
            [[k, v] for k, v in result.items()], headers=["Field", "Value"]
        )
        print(f"\n✔ CSV report written to {args.export_csv}", file=sys.stderr)
    if args.export_pdf:
        body = [f"{k}: {v}" for k, v in result.items()]
        core.export_text_report_pdf(args.export_pdf, "AgriExpert-PK Economic Damage Report", body)
        print(f"✔ PDF report written to {args.export_pdf}", file=sys.stderr)

    return 0


def cmd_weather(args):
    try:
        info = core.fetch_live_weather(args.city)
    except core.WeatherLookupError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(info, indent=2))
    else:
        print(f"{info['city']}, {info['country']}")
        print(f"  Temperature : {info['temperature_c']}°C")
        print(f"  Humidity    : {info['humidity_pct']}%")
        print(f"  Precipitation: {info['precipitation_mm']} mm")
        print(f"  → mapped weather category: {info['mapped_weather']}")
        print(f"  → mapped soil hint       : {info['mapped_soil_hint']}")
    return 0


def cmd_list_crops(args):
    if args.json:
        print(json.dumps(core.CROPS, indent=2))
    else:
        print("\n".join(core.CROPS))
    return 0


def cmd_list_symptoms(args):
    syms = core.SYMPTOMS.get(args.crop, [])
    if args.json:
        print(json.dumps(syms, indent=2))
    else:
        print("\n".join(syms))
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="agriexpert_cli.py",
        description="AgriExpert-PK headless CLI — diagnosis & economic-damage regression without the GUI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="command", required=True)

    def add_common_weather_flags(sp):
        sp.add_argument("--weather", choices=core.WEATHERS, default=None, help="Qualitative weather category")
        sp.add_argument("--soil", choices=core.SOILS, default=None, help="Qualitative soil condition")
        sp.add_argument("--city", default=None,
                         help="Auto-fill weather/soil from live conditions in this city "
                              "(overrides --weather/--soil unless lookup fails)")

    sp = sub.add_parser("diagnose", help="Run backward-chaining diagnosis with certainty factors")
    sp.add_argument("--crop", required=True, choices=core.CROPS)
    sp.add_argument("--symptoms", nargs="*", default=None, help="Observed symptoms (defaults to all known for crop)")
    add_common_weather_flags(sp)
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--export-csv", metavar="PATH")
    sp.add_argument("--export-pdf", metavar="PATH")
    sp.set_defaults(func=cmd_diagnose)

    sp = sub.add_parser("forward", help="Run forward-chaining inference from asserted facts")
    sp.add_argument("--crop", required=True, choices=core.CROPS)
    sp.add_argument("--symptoms", nargs="*", default=None)
    add_common_weather_flags(sp)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_forward)

    sp = sub.add_parser("regression", help="Predict yield loss, economic damage, and treatment ROI")
    sp.add_argument("--crop", required=True, choices=core.CROPS)
    sp.add_argument("--cf", type=float, required=True, help="Certainty-factor / disease severity score (0-100)")
    sp.add_argument("--weather", choices=core.WEATHERS, required=True)
    sp.add_argument("--soil", choices=core.SOILS, required=True)
    sp.add_argument("--hectares", type=float, required=True)
    sp.add_argument("--price", type=float, required=True, help="Market price per maund (PKR)")
    sp.add_argument("--treatment", choices=["fungicide", "pesticide", "biocontrol"], default="fungicide")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--export-csv", metavar="PATH")
    sp.add_argument("--export-pdf", metavar="PATH")
    sp.set_defaults(func=cmd_regression)

    sp = sub.add_parser("weather", help="Look up live weather for a city and show KB category mapping")
    sp.add_argument("--city", required=True)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_weather)

    sp = sub.add_parser("list-crops", help="List supported crops")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_list_crops)

    sp = sub.add_parser("list-symptoms", help="List known symptoms for a crop")
    sp.add_argument("--crop", required=True, choices=core.CROPS)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_list_symptoms)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
