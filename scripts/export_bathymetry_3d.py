#!/usr/bin/env python3
"""
Export the data behind the Home page's 3D domain view as JSON, for an
interactive Plotly (WebGL) scene instead of a static image: a flat ocean
top face coloured by real bathymetric depth (same yellow-to-purple scale as
the 2-D bathymetry map on About the Model), a flat land top face, the real
bathymetric relief on the bottom face (coloured the same way), and wall
geometry closing the volume along the domain perimeter.

Everything is exported as explicit triangle meshes (Plotly mesh3d): one list
of vertices, each with its own lon, lat, z and depth, plus triangle indices.
Plotly's 2-D-array "surface" trace was NOT used: with a curvilinear grid it
paired depth values with the wrong lon/lat (transposed indices) in tooltips,
so the depth shown did not match the position. With meshes every vertex
carries its own depth, so colour, position and tooltip always agree.
"""
import json

import numpy as np
from scipy import ndimage
import netCDF4 as nc
import cartopy.io.shapereader as shpreader
import shapely.geometry as sgeom

GRID_NC = "/Volumes/Expansion/MFRI_Work/iceland2km_grid.nc"
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


def grid_mesh(quad_ok, lon_d, lat_d, z, depth, nd_xy=4, nd_z=3):
    """Triangulate the grid quads flagged in quad_ok ((ny-1, nx-1) bool).

    Returns a dict of compact vertex arrays (only vertices that are used) and
    triangle index arrays, ready for Plotly mesh3d.
    """
    ny, nx = lon_d.shape
    idx = np.arange(ny * nx).reshape(ny, nx)
    qi, qj = np.nonzero(quad_ok)
    a = idx[qi, qj]
    b = idx[qi, qj + 1]
    c = idx[qi + 1, qj + 1]
    d = idx[qi + 1, qj]
    tris = np.concatenate([np.stack([a, b, c], axis=1), np.stack([a, c, d], axis=1)])
    used = np.unique(tris)
    remap = -np.ones(ny * nx, dtype=np.int64)
    remap[used] = np.arange(len(used))
    tris = remap[tris]
    flat = lambda arr: np.asarray(arr, dtype=float).ravel()[used]
    return dict(
        x=[round(float(v), nd_xy) for v in flat(lon_d)],
        y=[round(float(v), nd_xy) for v in flat(lat_d)],
        z=[round(float(v), nd_z) for v in flat(z)],
        c=[round(float(v), 1) for v in flat(depth)],
        i=tris[:, 0].tolist(), j=tris[:, 1].tolist(), k=tris[:, 2].tolist(),
    )


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

    lon_min, lon_max = float(lon.min()), float(lon.max())
    lat_min, lat_max = float(lat.min()), float(lat.max())

    ds = DOWNSAMPLE
    lon_d = lon[::ds, ::ds]
    lat_d = lat[::ds, ::ds]
    h_d = h[::ds, ::ds]
    mask_d = mask[::ds, ::ds]

    h_filled = fill_nearest(h_d, mask_d)
    bottom_z = -h_filled / 1000.0 * VERT_EXAGGERATION
    top_z = np.zeros_like(bottom_z)

    # Same fixed scale as the 2-D map (scripts/generate_bathymetry_overlay.py),
    # deeper than the deepest model cell so nothing is clipped.
    depth_vmin, depth_vmax = 0.0, 4000.0

    # Both the flat top face and the real-relief bottom face are coloured by
    # the same underlying depth field, so the whole slab reads as one
    # consistent bathymetry map -- just like About the Model's 2-D overlay.
    m = mask_d
    all_ocean = m[:-1, :-1] & m[:-1, 1:] & m[1:, 1:] & m[1:, :-1]
    any_land = ~all_ocean
    ocean_mesh = grid_mesh(all_ocean, lon_d, lat_d, top_z, h_d)
    # land: any quad touching a land cell, so there is no gap along the coast
    land_mesh = grid_mesh(any_land, lon_d, lat_d, top_z, np.zeros_like(top_z))
    seafloor_mesh = grid_mesh(np.ones_like(all_ocean), lon_d, lat_d, bottom_z, h_filled)

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
        ocean=ocean_mesh,
        land=dict(x=land_mesh["x"], y=land_mesh["y"], z=land_mesh["z"],
                  i=land_mesh["i"], j=land_mesh["j"], k=land_mesh["k"]),
        seafloor=seafloor_mesh,
        depth_range=[depth_vmin, depth_vmax],
        wall=dict(x=x_all, y=y_all, z=z_all,
                  i=[f[0] for f in faces], j=[f[1] for f in faces], k=[f[2] for f in faces]),
        coastlines=coast_lines,
        bounds=dict(lon_min=lon_min, lon_max=lon_max, lat_min=lat_min, lat_max=lat_max,
                    z_min=float(bottom_z.min())),
    )
    with open(OUT_JSON, "w") as f:
        json.dump(payload, f)
    print(f"[OUT] {OUT_JSON}")
    import os
    print(f"size: {os.path.getsize(OUT_JSON) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
