from honeybees.library.mapIO import ArrayReader, MapReader, NetCDFReader
import rasterio
import numpy as np
from pathlib import Path
import rioxarray as rxr

def test_mapIO():
    xmin, ymin, xmax, ymax = 73.7, 19, 73.9, 19.1

    example_map = Path("cell_area.tif")

    with rasterio.open(example_map) as src:
        data = src.read(1)
        transform = src.transform
        profile = src.profile

    arrayReader = ArrayReader(array=data, xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax, transform=transform)
    data_array = arrayReader.get_data_array()

    mapReader = MapReader(example_map, xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax)
    data_map = mapReader.get_data_array()

    assert np.array_equal(data_array, data_map)

    nc_fp = example_map.with_suffix('.nc')
    nc_raster = rxr.open_rasterio(example_map)
    nc_raster.to_netcdf(nc_fp)

    ncReader = NetCDFReader(
        nc_fp,
        varname='__xarray_dataarray_variable__',
        xmin=xmin,
        ymin=ymin,
        xmax=xmax,
        ymax=ymax
    )
    data_nc = ncReader.get_data_array()
    assert np.array_equal(data_array, data_nc)

    # remove the nc file
    ncReader.close()
    nc_fp.unlink()
