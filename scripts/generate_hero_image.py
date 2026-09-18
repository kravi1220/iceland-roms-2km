#!/usr/bin/env python3
"""
Render a wide, vivid ROMS sea-surface-temperature snapshot as the Home page's
hero background -- an actual model field rather than a stock ocean photo, so
there's no licensing question and it's directly relevant to the site.
"""
import numpy as np
import netCDF4 as nc
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SST_SSS_NC = "/Volumes/Expansion/Ice_ROMS_outpu/AVHRR/temp_SST_SSS_roms_iceland_201712_201812.nc"
GRID_NC = "/Volumes/Expansion/MFRI_Work/iceland2km_grid.nc"
OUT_PNG = "/Volumes/Expansion/MFRI_Work/iceland-roms-2km/assets/img/brand/hero_ocean.jpg"
TIME_INDEX = 258  # 2018-08-15, a summer field with good warm/cool contrast

def main():
    with nc.Dataset(SST_SSS_NC) as d:
        temp = d.variables["temp"][TIME_INDEX]
    with nc.Dataset(GRID_NC) as g:
        mask = g.variables["mask_rho"][:].astype(bool)
        lon = g.variables["lon_rho"][:]
        lat = g.variables["lat_rho"][:]

    temp_masked = np.ma.masked_where(~mask, temp)

    fig = plt.figure(figsize=(16, 6.5), dpi=150)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.set_facecolor("#03202e")
    fig.patch.set_facecolor("#03202e")
    ax.pcolormesh(lon, lat, temp_masked, cmap="turbo", shading="auto")
    ax.set_xlim(lon.min(), lon.max())
    ax.set_ylim(lat.min(), lat.max())

    fig.savefig(OUT_PNG, facecolor="#03202e", pil_kwargs={"quality": 87})
    plt.close(fig)
    print(f"[OUT] {OUT_PNG}")


if __name__ == "__main__":
    main()
