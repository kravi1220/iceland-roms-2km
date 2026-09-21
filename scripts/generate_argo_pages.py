#!/usr/bin/env python3
"""
Generate the per-float ROMS-vs-Argo comparison pages and the Argo index page
from data/float_metadata.csv and the images in assets/img/floats/<id>/.

Run from the repo root:
    python3 scripts/generate_argo_pages.py
"""
from __future__ import annotations

import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METADATA_CSV = os.path.join(ROOT, "data", "float_metadata.csv")
FLOATS_DIR = os.path.join(ROOT, "assets", "img", "floats")
ARGO_DIR = os.path.join(ROOT, "argo")

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://*.tile.openstreetmap.org; font-src 'self'; connect-src 'self'; worker-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'none'">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Iceland ROMS 2km</title>
<link rel="stylesheet" href="{css}">
</head>
<body>
<header class="site-header">
  <a class="brand" href="https://www.hafogvatn.is" target="_blank" rel="noopener">
    <img src="../assets/img/brand/mfri_logo.png" alt="MFRI logo">
    <span class="brand-text">
      <span class="brand-org">Marine &amp; Freshwater Research Institute</span>
      <span class="brand-sub">Iceland ROMS 2km</span>
    </span>
  </a>
  <nav>
    <a href="{home}">Home</a>
    <a href="{about}">About the Model</a>
    <a href="{argo_index}" class="active">ROMS vs Argo</a>
    <a href="{moorings}">ROMS vs Moorings</a>
    <a href="{sst_sss}">SST &amp; SSS</a>
    <a href="{roms_cice}">ROMS-CICE</a>
  </nav>
</header>
<main>
"""

FOOT = """</main>
<footer class="site-footer">
  <div class="footer-brand">
    <img src="../assets/img/brand/mfri_logo.png" alt="MFRI logo">
    <span>Marine and Freshwater Research Institute<br>Hafrannsóknastofnun (HAFRO)</span>
  </div>
  <p>ROMS Iceland 2&nbsp;km &mdash; experimental model output, research use only.
  Source: <a href="https://github.com/kravi1220/iceland-roms-2km">github.com/kravi1220/iceland-roms-2km</a></p>
</footer>
</body>
</html>
"""


def float_page(fid: str, lon: str, lat: str, n_days: str, have: dict) -> str:
    cards = []
    order = [
        ("timeseries", "Time series at fixed depths (10, 20, 50 m)"),
        ("profile", "Profile comparison"),
        ("TS", "T-S diagram"),
        ("hov", "Hovmöller diagram (depth vs time)"),
    ]
    for key, caption in order:
        if have.get(key):
            cards.append(
                f'<figure class="card">'
                f'<a href="../assets/img/floats/{fid}/{key}.png">'
                f'<img loading="lazy" src="../assets/img/floats/{fid}/{key}.png" alt="{caption} for float {fid}"></a>'
                f'<figcaption>{caption}</figcaption></figure>'
            )
    cards_html = "\n".join(cards)

    lat_f, lon_f = float(lat), float(lon)
    ns = "N" if lat_f >= 0 else "S"
    ew = "E" if lon_f >= 0 else "W"
    meta_line = f"Location: {abs(lat_f):.4f}&deg;{ns}, {abs(lon_f):.4f}&deg;{ew}"
    if n_days not in ("", "0"):
        meta_line += f" &middot; {n_days} colocated days"

    body = HEAD.format(
        title=f"Argo float {fid}",
        css="../assets/css/style.css?v=8",
        home="../index.html",
        about="../about.html",
        argo_index="index.html",
        moorings="../moorings.html",
        sst_sss="../sst_sss.html",
        roms_cice="../roms_cice.html",
    )
    body += f"""
<a class="back-link" href="index.html">&larr; All floats</a>
<h1>Argo float {fid}</h1>
<p class="meta">{meta_line}</p>
<div class="gallery">
{cards_html}
</div>
"""
    body += FOOT
    return body


def main() -> None:
    with open(METADATA_CSV, newline="") as f:
        rows = list(csv.DictReader(f))

    os.makedirs(ARGO_DIR, exist_ok=True)

    # NOTE: argo/index.html is hand-maintained (the interactive Leaflet/Plotly
    # explorer) and is NOT generated here. This script only builds the static
    # per-float report pages linked from that explorer's "Full static report"
    # link and from data/argo_floats.json.
    for row in rows:
        fid = row["float_wmo_id"]
        fdir = os.path.join(FLOATS_DIR, fid)
        have = {}
        if os.path.isdir(fdir):
            for key in ("timeseries", "profile", "TS", "hov"):
                have[key] = os.path.exists(os.path.join(fdir, f"{key}.png"))

        page = float_page(fid, row["lon"], row["lat"], row["n_matched_days"], have)
        with open(os.path.join(ARGO_DIR, f"float_{fid}.html"), "w") as f:
            f.write(page)

    print(f"Generated {len(rows)} float pages")


if __name__ == "__main__":
    main()
