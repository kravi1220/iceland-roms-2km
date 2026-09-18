#!/usr/bin/env python3
"""
Render the Iceland 2km ROMS grid's own bathymetry (h, mask_rho) as a plain,
borderless PNG for use as a Leaflet image overlay, plus a small JSON with the
exact geographic bounds and colour-scale so the front end can draw a legend.

Source: /Volumes/Expansion/MFRI_Work/iceland2km_grid.nc (the actual model
grid), not a pre-made figure.
"""
import json
import os

import numpy as np
import netCDF4 as nc
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm

GRID_NC = "/Volumes/Expansion/MFRI_Work/iceland2km_grid.nc"
OUT_PNG = "/Volumes/Expansion/MFRI_Work/iceland-roms-2km/assets/img/overview/bathymetry_overlay.png"
OUT_JSON = "/Volumes/Expansion/MFRI_Work/iceland-roms-2km/data/bathymetry_overlay.json"

CMAP_NAME = "viridis_r"
DPI = 200


def main():
    with nc.Dataset(GRID_NC) as d:
        lon = d.variables["lon_rho"][:]
        lat = d.variables["lat_rho"][:]
        h = d.variables["h"][:]
        mask = d.variables["mask_rho"][:].astype(bool)

    h_masked = np.ma.masked_where(~mask, h)
    vmin, vmax = 0.0, float(np.percentile(h[mask], 99))

    lon_min, lon_max = float(lon.min()), float(lon.max())
    lat_min, lat_max = float(lat.min()), float(lat.max())

    fig = plt.figure(figsize=(10, 10), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)

    cmap = cm.get_cmap(CMAP_NAME).copy()
    ax.pcolormesh(lon, lat, h_masked, cmap=cmap, vmin=vmin, vmax=vmax,
                  shading="auto", rasterized=True)
    # land: fully transparent so the Leaflet base map / land colour shows through
    ax.set_facecolor((0, 0, 0, 0))

    os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
    fig.savefig(OUT_PNG, transparent=True)
    plt.close(fig)

    payload = dict(
        bounds=[[lat_min, lon_min], [lat_max, lon_max]],  # Leaflet [[south,west],[north,east]]
        vmin=vmin, vmax=vmax, cmap=CMAP_NAME,
        depth_label="Depth (m)",
        source="iceland2km_grid.nc (HAFRO ROMS Iceland 2km grid): variables h, mask_rho, lon_rho, lat_rho",
    )
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"[OUT] {OUT_PNG}")
    print(f"[OUT] {OUT_JSON}")
    print(f"bounds lat {lat_min:.3f}..{lat_max:.3f}  lon {lon_min:.3f}..{lon_max:.3f}  depth 0..{vmax:.0f} m")


if __name__ == "__main__":
    main()
