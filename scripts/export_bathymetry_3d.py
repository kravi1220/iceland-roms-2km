#!/usr/bin/env python3
"""
Export the data behind the Home page's 3D domain view as JSON, for an
interactive Plotly (WebGL) scene instead of a static image: a flat ocean
top face coloured by a ROMS SST snapshot, a flat land top face, the real
bathymetric relief on the bottom face, and wall geometry (triangulated for
Plotly's mesh3d) closing the volume along the domain perimeter.
"""
import json

import numpy as np
from scipy import ndimage
import netCDF4 as nc
import cartopy.io.shapereader as shpreader
import shapely.geometry as sgeom

GRID_NC = "/Volumes/Expansion/MFRI_Work/iceland2km_grid.nc"
SST_NC = "/Volumes/Expansion/Ice_ROMS_outpu/AVHRR/temp_SST_SSS_roms_iceland_201712_201812.nc"
SST_INDEX = 258  # 2018-08-15
OUT_JSON = "/Volumes/Expansion/MFRI_Work/iceland-roms-2km/data/bathymetry_3d.json"

DOWNSAMPLE = 5
# Kept small deliberately: the front end uses Plotly's aspectmode="data" (the
# well-tested path -- "manual" aspectratio + custom camera renders broken on
# first paint in this Plotly version), so z must already be in the same
# numeric ballpark as the lon/lat degree spans for the box proportions to
# come out right without any manual ratio.
VERT_EXAGGERATION = 3.1


def fill_nearest(data, valid_mask):
    idx = ndimage.distance_transform_edt(~valid_mask, return_distances=False, return_indices=True)
    return data[tuple(idx)]


def rnd(arr, nd=3):
    """Round to nd decimals and turn NaN into None for JSON, as nested lists."""
    a = np.asarray(arr, dtype=float)
    a = np.round(a, nd)
    return [[None if np.isnan(v) else v for v in row] for row in a]


def wall_mesh(lon_e, lat_e, z_top_e, z_bot_e, x_all, y_all, z_all):
    """Append this edge's quads (as two triangles each) to the running vertex/face lists."""
    n = len(lon_e)
    base = len(x_all)
    for i in range(n):
        x_all.append(float(lon_e[i]))
        y_all.append(float(lat_e[i]))
        z_all.append(float(z_top_e[i]))
    for i in range(n):
        x_all.append(float(lon_e[i]))
        y_all.append(float(lat_e[i]))
        z_all.append(float(z_bot_e[i]))
    faces = []
    for i in range(n - 1):
        t, b = base + i, base + n + i
        t1, b1 = base + i + 1, base + n + i + 1
        faces.append((t, t1, b))
        faces.append((t1, b1, b))
    return faces


def main():
    with nc.Dataset(GRID_NC) as g:
        lon = g.variables["lon_rho"][:]
        lat = g.variables["lat_rho"][:]
        h = g.variables["h"][:]
        mask = g.variables["mask_rho"][:].astype(bool)
    with nc.Dataset(SST_NC) as s:
        sst = np.asarray(s.variables["temp"][SST_INDEX])

    lon_min, lon_max = float(lon.min()), float(lon.max())
    lat_min, lat_max = float(lat.min()), float(lat.max())

    ds = DOWNSAMPLE
    lon_d = lon[::ds, ::ds]
    lat_d = lat[::ds, ::ds]
    h_d = h[::ds, ::ds]
    mask_d = mask[::ds, ::ds]
    sst_d = sst[::ds, ::ds]

    h_filled = fill_nearest(h_d, mask_d)
    bottom_z = -h_filled / 1000.0 * VERT_EXAGGERATION
    top_z = np.zeros_like(bottom_z)

    ocean_sst = sst_d[mask_d]
    sst_vmin = float(np.percentile(ocean_sst, 1))
    sst_vmax = float(np.percentile(ocean_sst, 99))

    ocean_color = np.where(mask_d, sst_d, np.nan)
    ocean_z = np.where(mask_d, 0.0, np.nan)
    land_z = np.where(~mask_d, 0.0, np.nan)

    # Perimeter walls (triangulated for mesh3d)
    x_all, y_all, z_all, faces = [], [], [], []
    edges = [
        (lon_d[0, :], lat_d[0, :], top_z[0, :], bottom_z[0, :]),
        (lon_d[-1, :], lat_d[-1, :], top_z[-1, :], bottom_z[-1, :]),
        (lon_d[:, 0], lat_d[:, 0], top_z[:, 0], bottom_z[:, 0]),
        (lon_d[:, -1], lat_d[:, -1], top_z[:, -1], bottom_z[:, -1]),
    ]
    for lon_e, lat_e, zt, zb in edges:
        faces += wall_mesh(lon_e, lat_e, zt, zb, x_all, y_all, z_all)

    # High-res coastline for a crisp seam, drawn as a set of 3D lines at z=0.
    domain_box = sgeom.box(lon_min - 0.5, lat_min - 0.5, lon_max + 0.5, lat_max + 0.5)
    shp = shpreader.natural_earth(resolution="10m", category="physical", name="coastline")
    coast_lines = []
    for rec in shpreader.Reader(shp).geometries():
        clipped = rec.intersection(domain_box)
        if clipped.is_empty:
            continue
        geoms = clipped.geoms if hasattr(clipped, "geoms") else [clipped]
        for geom in geoms:
            xs, ys = geom.xy
            coast_lines.append(dict(lon=[round(float(v), 4) for v in xs],
                                     lat=[round(float(v), 4) for v in ys]))

    payload = dict(
        lon=rnd(lon_d, 4),
        lat=rnd(lat_d, 4),
        ocean_z=rnd(ocean_z),
        ocean_color=rnd(sst_d if False else ocean_color, 3),
        land_z=rnd(land_z),
        bottom_z=rnd(bottom_z),
        sst_range=[round(sst_vmin, 2), round(sst_vmax, 2)],
        wall=dict(x=x_all, y=y_all, z=z_all,
                  i=[f[0] for f in faces], j=[f[1] for f in faces], k=[f[2] for f in faces]),
        coastlines=coast_lines,
        bounds=dict(lon_min=lon_min, lon_max=lon_max, lat_min=lat_min, lat_max=lat_max,
                    z_min=float(bottom_z.min())),
        sst_date="2018-08-15",
    )
    with open(OUT_JSON, "w") as f:
        json.dump(payload, f)
    print(f"[OUT] {OUT_JSON}")
    import os
    print(f"size: {os.path.getsize(OUT_JSON) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
