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
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Iceland ROMS 2km</title>
<link rel="stylesheet" href="{css}">
</head>
<body>
<header class="site-header">
  <a class="brand" href="{home}">Iceland ROMS 2km</a>
  <nav>
    <a href="{home}">Home</a>
    <a href="{about}">About the Model</a>
    <a href="{argo_index}">ROMS vs Argo</a>
    <a href="{moorings}">ROMS vs Moorings</a>
  </nav>
</header>
<main>
"""

FOOT = """</main>
<footer class="site-footer">
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
        css="../assets/css/style.css",
        home="../index.html",
        about="../about.html",
        argo_index="index.html",
        moorings="../moorings.html",
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

    table_rows = []
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

        thumb = "TS" if have.get("TS") else next((k for k, v in have.items() if v), None)
        thumb_cell = (
            f'<a href="float_{fid}.html"><img class="thumb" loading="lazy" '
            f'src="../assets/img/floats/{fid}/{thumb}.png" alt=""></a>'
            if thumb
            else ""
        )
        table_rows.append(
            f"<tr><td>{thumb_cell}</td>"
            f'<td><a href="float_{fid}.html">{fid}</a></td>'
            f"<td>{row['lat']}</td><td>{row['lon']}</td>"
            f"<td>{row['n_matched_days'] or 0}</td></tr>"
        )

    index = HEAD.format(
        title="ROMS vs Argo Floats",
        css="../assets/css/style.css",
        home="../index.html",
        about="../about.html",
        argo_index="index.html",
        moorings="../moorings.html",
    )
    index += """
<h1>ROMS vs Argo Floats</h1>
<p>The Iceland 2&nbsp;km ROMS daily-average output is colocated with Argo float
profiles: for each Argo profile, the nearest ocean grid cell (great-circle
nearest-neighbour on the model's wet-point mask) and the closest daily model
record in time are selected, then temperature and salinity are compared on
common depth levels (10, 20 and 50&nbsp;m) and over the full water column.
Floats farther than 50&nbsp;km from any model grid cell are excluded.</p>

<h2>Overview</h2>
<div class="gallery">
  <figure class="card">
    <a href="../assets/img/overview/float_roms_colocation_map.png">
      <img loading="lazy" src="../assets/img/overview/float_roms_colocation_map.png" alt="Map of colocated Argo floats over the model domain"></a>
    <figcaption>Float positions colocated with the model domain</figcaption>
  </figure>
  <figure class="card">
    <a href="../assets/img/overview/TS_all_floats.png">
      <img loading="lazy" src="../assets/img/overview/TS_all_floats.png" alt="Combined T-S diagram, all floats"></a>
    <figcaption>Combined T-S diagram, all floats</figcaption>
  </figure>
  <figure class="card">
    <a href="../assets/img/overview/taylor_temperature_combined.png">
      <img loading="lazy" src="../assets/img/overview/taylor_temperature_combined.png" alt="Taylor diagram, temperature skill"></a>
    <figcaption>Taylor diagram &mdash; temperature skill</figcaption>
  </figure>
  <figure class="card">
    <a href="../assets/img/overview/taylor_salinity_combined.png">
      <img loading="lazy" src="../assets/img/overview/taylor_salinity_combined.png" alt="Taylor diagram, salinity skill"></a>
    <figcaption>Taylor diagram &mdash; salinity skill</figcaption>
  </figure>
</div>

<h2>Floats ({n} total)</h2>
<table class="float-table">
  <thead><tr><th></th><th>WMO ID</th><th>Lat (&deg;N)</th><th>Lon (&deg;E)</th><th>Colocated days</th></tr></thead>
  <tbody>
{rows_html}
  </tbody>
</table>
""".format(n=len(rows), rows_html="\n".join(table_rows))
    index += FOOT

    with open(os.path.join(ARGO_DIR, "index.html"), "w") as f:
        f.write(index)

    print(f"Generated {len(rows)} float pages + argo/index.html")


if __name__ == "__main__":
    main()
