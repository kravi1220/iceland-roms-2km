#!/usr/bin/env python3
"""
Render the Iceland 2km ROMS domain as a 3D "extracted slab" box: a flat top
face draped with a ROMS SST snapshot (ocean) / a flat land colour, a bottom
face following the real bathymetry (so the seafloor relief is visible below
the box, mountains and trenches alike), and translucent side walls closing
the volume in between -- the style used in many ocean-model promo graphics
(e.g. Copernicus Marine, met.no).
"""
import numpy as np
from scipy import ndimage
import netCDF4 as nc
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers the 3d projection)
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import cartopy.io.shapereader as shpreader
import shapely.geometry as sgeom

GRID_NC = "/Volumes/Expansion/MFRI_Work/iceland2km_grid.nc"
SST_NC = "/Volumes/Expansion/Ice_ROMS_outpu/AVHRR/temp_SST_SSS_roms_iceland_201712_201812.nc"
SST_INDEX = 258  # 2018-08-15: a summer field with strong warm/cool contrast
OUT_PNG = "/Volumes/Expansion/MFRI_Work/iceland-roms-2km/assets/img/overview/bathymetry_3d.png"

DOWNSAMPLE = 3
VERT_EXAGGERATION = 22  # box thickness relative to the lon/lat footprint
LAND_COLOR = (0.66, 0.64, 0.48, 1.0)
WALL_COLOR = "#9aa1a8"
BOTTOM_COLOR = "#c7cacd"


def fill_nearest(data, valid_mask):
    """Fill invalid cells with the value of their nearest valid neighbour."""
    idx = ndimage.distance_transform_edt(~valid_mask, return_distances=False, return_indices=True)
    return data[tuple(idx)]


def wall_quads(lon_e, lat_e, z_top_e, z_bot_e):
    quads = []
    for i in range(len(lon_e) - 1):
        quads.append([
            (lon_e[i], lat_e[i], z_top_e[i]),
            (lon_e[i + 1], lat_e[i + 1], z_top_e[i + 1]),
            (lon_e[i + 1], lat_e[i + 1], z_bot_e[i + 1]),
            (lon_e[i], lat_e[i], z_bot_e[i]),
        ])
    return quads


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

    # Extend real bathymetry under land (nearest ocean neighbour) so the
    # bottom face has a plausible continuous shape instead of a flat plateau.
    h_filled = fill_nearest(h_d, mask_d)
    bottom_z = -h_filled / 1000.0 * VERT_EXAGGERATION
    top_z = np.zeros_like(bottom_z)

    fig = plt.figure(figsize=(11, 9), dpi=170)
    ax = fig.add_subplot(111, projection="3d")

    # --- Top face: SST drape over ocean, flat colour over land ---
    ocean_sst = sst_d[mask_d]
    sst_norm = plt.Normalize(vmin=float(np.percentile(ocean_sst, 1)),
                              vmax=float(np.percentile(ocean_sst, 99)))
    top_cmap = plt.get_cmap("turbo")
    top_facecolors = top_cmap(sst_norm(np.where(mask_d, sst_d, sst_norm.vmin)))
    top_facecolors[~mask_d] = LAND_COLOR

    ax.plot_surface(lon_d, lat_d, top_z, facecolors=top_facecolors,
                     rstride=1, cstride=1, linewidth=0, antialiased=True,
                     shade=False, zorder=3)

    # crisp high-res coastline right at the land/sea seam
    domain_box = sgeom.box(lon_min - 0.5, lat_min - 0.5, lon_max + 0.5, lat_max + 0.5)
    shp = shpreader.natural_earth(resolution="10m", category="physical", name="coastline")
    for rec in shpreader.Reader(shp).geometries():
        clipped = rec.intersection(domain_box)
        if clipped.is_empty:
            continue
        geoms = clipped.geoms if hasattr(clipped, "geoms") else [clipped]
        for geom in geoms:
            xs, ys = geom.xy
            ax.plot(xs, ys, np.full(len(xs), 0.01), color="#1c1c1c", linewidth=0.6, zorder=4)

    # --- Bottom face: real bathymetric relief ---
    ax.plot_surface(lon_d, lat_d, bottom_z, color=BOTTOM_COLOR,
                     rstride=1, cstride=1, linewidth=0, antialiased=True,
                     shade=True, zorder=1)

    # --- Side walls closing the box along the domain perimeter ---
    edges = [
        (lon_d[0, :], lat_d[0, :], top_z[0, :], bottom_z[0, :]),
        (lon_d[-1, :], lat_d[-1, :], top_z[-1, :], bottom_z[-1, :]),
        (lon_d[:, 0], lat_d[:, 0], top_z[:, 0], bottom_z[:, 0]),
        (lon_d[:, -1], lat_d[:, -1], top_z[:, -1], bottom_z[:, -1]),
    ]
    quads = []
    for lon_e, lat_e, zt, zb in edges:
        quads += wall_quads(lon_e, lat_e, zt, zb)
    wall = Poly3DCollection(quads, facecolor=WALL_COLOR, edgecolor="none",
                             alpha=1.0, zorder=2)
    ax.add_collection3d(wall)

    ax.set_box_aspect((lon_max - lon_min, lat_max - lat_min,
                        (lat_max - lat_min) * 0.42))
    ax.view_init(elev=26, azim=-58)
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    ax.set_zlim(bottom_z.min(), 0)
    ax.set_axis_off()

    m = plt.cm.ScalarMappable(cmap=top_cmap, norm=sst_norm)
    m.set_array([])
    cbar = fig.colorbar(m, ax=ax, shrink=0.45, pad=0.0, aspect=25)
    cbar.set_label("Sea surface temperature (°C), 2018-08-15", fontsize=9)

    fig.savefig(OUT_PNG, bbox_inches="tight", transparent=True)
    plt.close(fig)
    print(f"[OUT] {OUT_PNG}")


if __name__ == "__main__":
    main()
