# -*- coding: utf-8 -*-
"""Submodule that implements several classes for reading maps (image type and NetCDF type)."""

import datetime
import numpy as np
from math import ceil, floor
import xarray as xr
from honeybees.library.raster import sample_from_map
import rasterio
from rasterio import mask
from rasterio.windows import Window
from inspect import getcallargs
from typing import Union


class Reader:
    """This is a base class to read mapdata from files. The class takes as input the bounds of the relevant area. Any input maps are automatically cut to only read the required area. The class contains several functions to make reading data per agent easy and fast.

    Args:
        bounds: tuple of xmin, xmax, ymin, ymax of study_area.
    """

    def __init__(self, xmin: float, ymin: float, xmax: float, ymax: float) -> None:
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax

    def get_source_gt(self) -> None:
        """Get Geotransformation of the source file. Must be implemented in the child class."""
        raise NotImplementedError

    def set_window_and_gt(self) -> None:
        """This function gets the geotransformation (gt) of the cut map, and the rows to read from the original data (rowslice, colslice)."""
        gt_ds = self.get_source_gt()

        colmin = floor((self.xmin - gt_ds[0]) / gt_ds[1])
        colmax = ceil((self.xmax - gt_ds[0]) / gt_ds[1])
        self.colslice = slice(colmin, colmax)

        rowmin = (self.ymax - gt_ds[3]) / gt_ds[5]
        rowmax = (self.ymin - gt_ds[3]) / gt_ds[5]
        # Detect if array is flipped upside down. If so, reverse rowmin and rowmax and use self.flipup to flip array when returned
        if rowmin > rowmax:
            rowmin, rowmax = rowmax, rowmin
            self.flipud = True
        else:
            self.flipud = False

        rowmin = floor(rowmin)
        rowmax = ceil(rowmax)

        self.rowslice = slice(rowmin, rowmax)

        assert colmin >= 0
        assert rowmin >= 0

        if self.flipud:
            self.gt = (
                gt_ds[0] + colmin * gt_ds[1],
                gt_ds[1],
                gt_ds[2],
                gt_ds[3] + rowmax * gt_ds[5],
                gt_ds[4],
                -gt_ds[5],
            )
        else:
            self.gt = (
                gt_ds[0] + colmin * gt_ds[1],
                gt_ds[1],
                gt_ds[2],
                gt_ds[3] + rowmin * gt_ds[5],
                gt_ds[4],
                gt_ds[5],
            )

    def sample_coords(self, coords: np.ndarray, *args, **kwargs) -> np.ndarray:
        """
        Args:
            coords: 2D NumPy array of coordinates to sample. First dimension is a list of coordinates, second dimension are the x and y.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            data: values as read from map for given coordinates.
        """
        array = self.get_data_array(*args, **kwargs)
        return sample_from_map(array, coords, self.gt)

    def get_data_array(self, *args, cache: bool = False, **kwargs):
        """Read data array from map.

        Parameters:
            cache (bool): cache output from previous call to function, check parameters (default: False)
            args: passed to child _get_data_array
            kwargs: passed to child _get_data_array

        Returns:
            array: requested array
        """
        if cache:
            call_args = getcallargs(self._get_data_array, *args, **kwargs)
            call_args.pop("self")
            if "kwargs" in call_args:
                call_args.update(call_args.pop("kwargs"))
            if (
                hasattr(self, "get_data_array_cache_args")
                and call_args == self.get_data_array_cache_args
            ):
                return self.get_data_array_cache

        array = self._get_data_array(*args, **kwargs)
        if cache:
            self.get_data_array_cache = array
            self.get_data_array_cache_args = call_args
        return array

    def delete_get_data_array_cache(self) -> None:
        """If results from get_data_array were cached, these can be deleted using this function."""
        if hasattr(self, "get_data_array_cache"):
            delattr(self, "get_data_array_cache")
            delattr(self, "get_data_array_cache_args")


class MapReader(Reader):
    """This class can be used to read image type data from files, and then to easily sample data from it.

    Args:
        fp: Filepath of file.
        bounds: tuple of xmin, xmax, ymin, ymax of study_area.
    """

    def __init__(
        self, fp: str, xmin: float, ymin: float, xmax: float, ymax: float
    ) -> None:
        Reader.__init__(self, xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax)
        self.fp = fp
        self.ds = rasterio.open(fp, "r")
        self.set_window_and_gt()

    def get_source_gt(self) -> tuple[float, float, float, float, float, float]:
        """Get geotransformation of the source file.

        Returns:
            gt: Geotransformation of source file.
        """
        return self.ds.transform.to_gdal()

    @property
    def source_shape(self) -> tuple[int, int]:
        """Get shape of source file.

        Returns:
            height: height of array.
            width: width of array.
        """
        return self.ds.shape

    def _get_data_array(self) -> np.ndarray:
        """Read array from file for study_area.

        Returns:
            data: Array of data for study_area.
        """
        data = self.ds.read(window=Window.from_slices(self.rowslice, self.colslice))
        if data.shape[0] == 1:
            return data[0]
        else:
            return data

    def sample_geom(
        self, geom: dict, all_touched=False, nodata: Union[float, int] = -1
    ) -> np.ndarray:
        """Sample geometry from array.

        Args:
            geom: GeoJSON dictionary of geometry.
            nodata: Value to fill nodata.
            all_touched: Bool to include a pixel in the mask if it touches any of the shapes.
        Returns:
            data: Values for geometry.
        """
        geom = geom["geometry"] if "geometry" in geom else geom
        data, transform = mask.mask(
            self.ds, [geom], crop=True, all_touched=all_touched, nodata=nodata
        )
        return data[0, :, :]

    def sample_geoms(self, geoms: list[dict], nodata: int = -1):
        """Sample multiple geometries from data array.

        Args:
            geoms: List of GeoJSON dictionary of geometries.
            nodata: Value to fill nodata.

        Yields:
            data: Values for geometry.
        """
        for geom in geoms:
            yield self.sample_geom(geom=geom, nodata=nodata)


class NetCDFReader(Reader):
    def __init__(
        self,
        fp: str,
        varname: str,
        xmin: float,
        ymin: float,
        xmax: float,
        ymax: float,
        latname: str = "lat",
        lonname: str = "lon",
        timename: str = "time",
    ) -> None:
        """This class can be used to read data from NetCDF files, and then to easily sample data from it.

        Args:
            fp: Filepath of file.
            varname: netcdf variable to read
            bounds: tuple of xmin, xmax, ymin, ymax of study_area.
            latname: name of latitude variable
            lonname: name of longitude variable
            timename: name of the time variable
        """
        self.fp = fp
        self.latname = latname
        self.lonname = lonname
        self.timename = timename

        Reader.__init__(self, xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax)
        self.ds = xr.open_dataset(self.fp)

        try:
            self.data = self.ds.variables[varname]
        except KeyError:
            raise KeyError(
                f'{varname} not found in NetCDF. Possible variables are {", ".join(self.ds.variables.keys())}'
            )

        self.set_window_and_gt()
        self.get_current_time_index()

    @property
    def title(self) -> str:
        """Title of NetCDF file."""
        return self.ds.title

    @property
    def source_shape(self):
        """Get shape of source file.

        Returns:
            height: height of array.
            width: width of array.
        """
        return (
            self.ds.variables[self.latname].size,
            self.ds.variables[self.lonname].size,
        )

    def get_source_gt(self):
        """Construct a GDAL-style Geotransformation from the source NetCDF using the longitude and latitude data.

        Returns:
            gt: Geotransformation of source file.
        """
        gt = (
            self.ds.rename({self.lonname: "x", self.latname: "y"})
            .rio.transform()
            .to_gdal()
        )
        assert gt[2] == 0 and gt[4] == 0, "Geotransformation must have no rotation."
        return gt

    def get_current_time_index(self) -> None:
        """Read the time indices from NetCDF file in Python datetime format. If time index does not exist, it is not set."""
        if self.timename in self.ds.variables:
            self.time_index = self.ds[self.timename].to_index()
        else:
            self.time_index = None

    def _get_data_array(self, dt: datetime.datetime = None) -> np.ndarray:
        """
        Read data array from NetCDF file for study_area.

        Args:
            dt: Datetime to read. Required if data has time dimension, otherwise should not be given.

        Returns:
            data: Array of data for study_area.
        """
        if self.time_index is not None:
            if not dt:
                raise ValueError(
                    "Must specify datetime for NetCDF with time component by passing dt-argument to the function call."
                )
            time_index = self.time_index.get_loc(dt)
            array = self.data.isel(
                {
                    self.timename: time_index,
                    self.latname: self.rowslice,
                    self.lonname: self.colslice,
                }
            )
        else:
            assert dt is None
            array = self.data.isel(
                {self.latname: self.rowslice, self.lonname: self.colslice}
            )
            # array = self.data[self.rowslice, self.colslice]

        assert array.size > 0
        if self.flipud:
            return np.flipud(array)
        else:
            return array.data

    def close(self) -> None:
        """Close NetCDF file."""
        self.ds.close()


class ArrayReader(Reader):
    def __init__(
        self,
        array: str,
        xmin: float,
        ymin: float,
        xmax: float,
        ymax: float,
        transform: Union[
            rasterio.Affine, tuple[float, float, float, float, float, float]
        ],
    ) -> None:
        Reader.__init__(self, xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax)
        self.array = array
        if isinstance(transform, rasterio.Affine):
            self.transform = transform.to_gdal()
        else:
            self.transform = transform
        self.set_window_and_gt()

    def get_source_gt(self) -> tuple[float, float, float, float, float, float]:
        """Get geotransformation of the source file.

        Returns:
            gt: Geotransformation of source file.
        """
        return self.transform

    @property
    def source_shape(self) -> tuple[int, int]:
        """Get shape of source file.

        Returns:
            height: height of array.
            width: width of array.
        """
        return self.array.shape

    def _get_data_array(self) -> np.ndarray:
        """Read array from file for study_area.

        Returns:
            data: Array of data for study_area.
        """
        data = self.array[self.rowslice, self.colslice]
        if data.shape[0] == 1:
            return data[0]
        else:
            return data

    def sample_geom(
        self, geom: dict, all_touched=False, nodata: Union[float, int] = -1
    ) -> np.ndarray:
        raise NotImplementedError

    def sample_geoms(self, geoms: list[dict], nodata: int = -1):
        raise NotImplementedError
