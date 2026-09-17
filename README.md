# Iceland ROMS 2km

An open, static website presenting a 2 km-resolution ROMS (Regional Ocean
Modeling System) implementation of the seas around Iceland, with validation
against independent observations (Argo floats, moorings). Modeled after
[LiveOcean](https://faculty.washington.edu/pmacc/LO/LiveOcean.html).

Live site: `https://kravi1220.github.io/iceland-roms-2km/` (once GitHub Pages
is enabled, see below).

## Contents

- `index.html`, `about.html`, `moorings.html` — hand-written static pages.
- `argo/` — the ROMS-vs-Argo gallery. `argo/index.html` and the 36
  `argo/float_<WMO_ID>.html` pages are generated (see below); don't hand-edit them.
- `assets/img/` — figures (bathymetry map, per-float comparison plots, overview
  skill diagrams).
- `data/float_metadata.csv` — float WMO ID, position and number of colocated
  days, used to build the Argo pages.
- `scripts/generate_argo_pages.py` — regenerates `argo/index.html` and the
  per-float pages from `data/float_metadata.csv` and `assets/img/floats/`.

## Regenerating the Argo pages

If float images or metadata change, regenerate the pages:

```bash
python3 scripts/generate_argo_pages.py
```

## Local preview

```bash
python3 -m http.server 8000
```

then open `http://localhost:8000/`.

## Deploying with GitHub Pages

1. Push this repo to `github.com/kravi1220/iceland-roms-2km`.
2. In the repo's Settings &rarr; Pages, set the source to the `main` branch, root folder.
3. The site will be published at `https://kravi1220.github.io/iceland-roms-2km/`.

## Status

- **ROMS vs Argo floats**: complete (36 colocated floats).
- **ROMS vs moorings**: in progress — see [moorings.html](moorings.html).

## About the model

See [about.html](about.html) for the model domain, resolution and bathymetry.
The grid was built at HAFRO (the Icelandic Marine and Freshwater Research
Institute / Hafrannsóknastofnun).

## License

Code (HTML/CSS/scripts) is licensed under the MIT License, see [LICENSE](LICENSE).
Figures are experimental research output, provided for research use only —
see the disclaimer on the site.
