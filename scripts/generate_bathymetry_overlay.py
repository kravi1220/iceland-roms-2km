#!/usr/bin/env python3
"""
Render the Iceland 2km ROMS grid's own bathymetry (h, mask_rho) as a plain,
borderless PNG for use as a Leaflet image overlay, plus a small JSON with the
exact geographic bounds and colour-scale so the front end can draw a legend.

Also writes a "depth raster" (bathymetry_depth.png) on the same Web Mercator
layout: each ocean pixel stores the model depth in metres as R*256+G (A=255;
land/outside-domain pixels have A=0). The front end reads it to show the true
model depth under the cursor, so the colour scale can always be checked
against the actual numbers.

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
from PIL import Image
from scipy.spatial import cKDTree

GRID_NC = "/Volumes/Expansion/MFRI_Work/iceland2km_grid.nc"
OUT_PNG = "/Volumes/Expansion/MFRI_Work/iceland-roms-2km/assets/img/overview/bathymetry_overlay.png"
OUT_JSON = "/Volumes/Expansion/MFRI_Work/iceland-roms-2km/data/bathymetry_overlay.json"
OUT_DEPTH_PNG = "/Volumes/Expansion/MFRI_Work/iceland-roms-2km/assets/img/overview/bathymetry_depth.png"

CMAP_NAME = "viridis_r"
DPI = 200
# Fixed, round upper end of the colour scale (deeper than the deepest model
# cell, 3827 m) so no depth is clipped to the same colour as a shallower one.
VMAX = 4000.0
DEPTH_RASTER_WIDTH = 1000


def web_mercator_y(lat_deg):
    """Web Mercator northing (unnormalized, in radians of 'stretched' latitude).

    Leaflet's default CRS is Web Mercator, so an L.imageOverlay's pixel rows
    are spaced linearly in *this* coordinate, not in plain latitude. Rendering
    the raster with plain lat on the y-axis (equirectangular/Plate Carree)
    makes it drift away from the OSM basemap as latitude increases -- most
    visible here since the domain spans 57.5-72.4 N. Pre-warping the y-axis to
    Mercator space before rasterizing keeps the pixel grid linear in the same
    coordinate Leaflet uses to place the image, so it lines up at every
    latitude.
    """
    lat_rad = np.radians(np.clip(lat_deg, -85.05, 85.05))
    return np.log(np.tan(np.pi / 4.0 + lat_rad / 2.0))


def write_depth_raster(lon, merc_y, h, mask, lon_min, lon_max, my_min, my_max, aspect):
    """Nearest-model-cell depth (integer metres, R*256+G) on a Mercator raster."""
    W = DEPTH_RASTER_WIDTH
    H = int(round(W * aspect))
    px_lon = lon_min + (np.arange(W) + 0.5) / W * (lon_max - lon_min)
    px_my = my_max - (np.arange(H) + 0.5) / H * (my_max - my_min)
    gx, gy = np.meshgrid(np.radians(px_lon), px_my)
    # lon and Mercator y are both radians (conformal), so plain Euclidean
    # distance in (lon, merc_y) is a fair nearest-cell metric.
    pts = np.column_stack([np.radians(lon).ravel(), merc_y.ravel()])
    tree = cKDTree(pts)
    dist, idx = tree.query(np.column_stack([gx.ravel(), gy.ravel()]))
    cell = 2000.0 / 6371000.0 / np.cos(np.radians(65))   # ~2 km in Mercator radians at 65N
    ocean = mask.ravel()[idx] & (dist < 1.2 * cell)
    depth = np.clip(np.round(h.ravel()[idx]), 0, 65535).astype(np.int64)
    rgba = np.zeros((H * W, 4), dtype=np.uint8)
    rgba[:, 0] = np.where(ocean, depth // 256, 0)
    rgba[:, 1] = np.where(ocean, depth % 256, 0)
    rgba[:, 3] = np.where(ocean, 255, 0)
    Image.fromarray(rgba.reshape(H, W, 4), "RGBA").save(OUT_DEPTH_PNG, optimize=True)
    print(f"[OUT] {OUT_DEPTH_PNG}  ({W}x{H})")


def main():
    with nc.Dataset(GRID_NC) as d:
        lon = d.variables["lon_rho"][:]
        lat = d.variables["lat_rho"][:]
        h = d.variables["h"][:]
        mask = d.variables["mask_rho"][:].astype(bool)

    h_masked = np.ma.masked_where(~mask, h)
    vmin, vmax = 0.0, VMAX

    lon_min, lon_max = float(lon.min()), float(lon.max())
    lat_min, lat_max = float(lat.min()), float(lat.max())
    merc_y = web_mercator_y(lat)
    merc_y_min, merc_y_max = web_mercator_y(lat_min), web_mercator_y(lat_max)

    # Match the canvas aspect ratio to the projected extent so the raster
    # isn't needlessly resampled anisotropically by Leaflet after warping.
    # Both spans must be in the same units (radians): Mercator is conformal,
    # so lon and merc_y are directly comparable once both are in radians.
    lon_span_rad = np.radians(lon_max - lon_min)
    merc_span = merc_y_max - merc_y_min
    fig_w = 10.0
    fig_h = fig_w * (merc_span / lon_span_rad)

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(merc_y_min, merc_y_max)

    cmap = cm.get_cmap(CMAP_NAME).copy()
    ax.pcolormesh(lon, merc_y, h_masked, cmap=cmap, vmin=vmin, vmax=vmax,
                  shading="auto", rasterized=True)
    # land: fully transparent so the Leaflet base map / land colour shows through
    ax.set_facecolor((0, 0, 0, 0))

    os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
    fig.savefig(OUT_PNG, transparent=True)
    plt.close(fig)

    write_depth_raster(lon, merc_y, h, mask, lon_min, lon_max, merc_y_min, merc_y_max, fig_h / fig_w)

    payload = dict(
        bounds=[[lat_min, lon_min], [lat_max, lon_max]],  # Leaflet [[south,west],[north,east]]
        vmin=vmin, vmax=vmax, cmap=CMAP_NAME,
        depth_label="Depth (m)",
        depth_png="bathymetry_depth.png",
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
