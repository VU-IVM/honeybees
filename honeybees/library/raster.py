# -*- coding: utf-8 -*-
from typing import Tuple
from rasterio.transform import Affine
from rasterio.profiles import Profile
from numba import njit, prange
import numpy as np
from rasterio.windows import Window
from rasterio.crs import CRS
from rasterio.io import DatasetReader
from netCDF4 import Dataset, date2num
from datetime import datetime
import os
from typing import Union


@njit(cache=True)
def reproject_pixel(
    gt_from: tuple[float, float, float, float, float, float],
    gt_to: tuple[float, float, float, float, float, float],
    px_in: int,
    py_in: int,
) -> tuple[int, int]:
    """Reproject pixel.

    Args:
        gt_from: Orginal geotransformation.
        gt_to: Target geotransformation.
        px_in: Input xpixel.
        py_in: Input ypixel.
    """
    px_out = (gt_from[0] + gt_from[1] * px_in - gt_to[0]) / gt_to[1]
    py_out = (gt_from[3] + gt_from[5] * py_in - gt_to[3]) / gt_to[5]
    return int(px_out), int(py_out)


@njit(cache=True)
def pixel_to_coord(px: int, py: int, gt: tuple) -> Tuple[float, float]:
    """Converts pixel (x, y) to coordinate (lon, lat) for given geotransformation.
    Uses the upper left corner of the pixel. To use the center, add 0.5 to input pixel.

        Parameters:
            pixel: the pixel (x, y) that need to be transformed to coordinate
            gt: the geotransformation. Must be unrotated

        Returns:
            array: the coordinate (lon, lat)
    """
    if gt[2] + gt[4] == 0:
        lon = px * gt[1] + gt[0]
        lat = py * gt[5] + gt[3]
        return lon, lat
    else:
        raise ValueError("Cannot convert rotated maps")


@njit(cache=True, parallel=True)
def pixels_to_coords(pixels: np.ndarray, gt: tuple) -> np.ndarray:
    """Converts pixels (x, y) to coordinates (lon, lat) for given geotransformation.
    Uses the upper left corner of the pixels. To use the centers, add 0.5 to input pixels.

        Parameters:
            pixels: the pixels (x, y) that need to be transformed to coordinates (shape: 2, n)
            gt: the geotransformation. Must be unrotated

        Returns:
            array: the coordinates (lon, lat) (shape: 2, n)
    """
    assert pixels.shape[1] == 2
    if gt[2] + gt[4] == 0:
        coords = np.empty(pixels.shape, dtype=np.float64)
        for i in prange(coords.shape[0]):
            coords[i, 0] = pixels[i, 0] * gt[1] + gt[0]
            coords[i, 1] = pixels[i, 1] * gt[5] + gt[3]
        return coords
    else:
        raise ValueError("Cannot convert rotated maps")


@njit(cache=True)
def coord_to_pixel(
    coord: np.ndarray, gt: tuple[float, float, float, float, float, float]
) -> tuple[int, int]:
    """Converts coordinate to pixel (x, y) for given geotransformation.

    Parameters:
        coord: the coordinate (lon, lat) that need to be transformed to pixel
        gt: the geotransformation. Must be unrotated

    Returns:
        array: tuple of pixel (x, y)
    """
    if gt[2] + gt[4] == 0:
        px = (coord[0] - gt[0]) / gt[1]
        py = (coord[1] - gt[3]) / gt[5]
        return int(px), int(py)
    else:
        raise ValueError("Cannot convert rotated maps")


@njit(parallel=True)
def coords_to_pixels(
    coords, gt: tuple, dtype=np.uint32
) -> tuple[np.ndarray, np.ndarray]:
    """Converts array of coordinates to array of pixels for given geotransformation.

    Parameters:
        coords: the coordinates (lon, lat) that need to be transformed to pixels (shape: 2, n)
        gt: the geotransformation. Must be unrotated

    Returns:
        array: 2d-array of pixels per coordinate (shape: 2, n)
    """
    if gt[2] + gt[4] == 0:
        size = coords.shape[0]
        x_offset = gt[0]
        y_offset = gt[3]
        x_step = gt[1]
        y_step = gt[5]
        pxs = np.empty(size, dtype=dtype)
        pys = np.empty(size, dtype=dtype)
        for i in prange(size):
            pxs[i] = int((coords[i, 0] - x_offset) / x_step)
            pys[i] = int((coords[i, 1] - y_offset) / y_step)
        return pxs, pys
    else:
        raise ValueError("Cannot convert rotated maps")


@njit(parallel=False)
def sample_from_map(
    array: np.ndarray,
    coords: np.ndarray,
    gt: tuple[float, float, float, float, float, float],
) -> np.ndarray:
    """Sample coordinates from a map. Can handle multiple dimensions.

    Parameters:
        array: the map to sample from (2+n dimensions)
        coords: the coordinates used to sample (shape: 2, m)
        gt: the geotransformation. Must be unrotated

    Returns:
        array: values per coordinate
    """
    assert gt[2] + gt[4] == 0
    size = coords.shape[0]
    x_offset = gt[0]
    y_offset = gt[3]
    x_step = gt[1]
    y_step = gt[5]
    values = np.empty((size,) + array.shape[:-2], dtype=array.dtype)
    for i in prange(size):
        values[i] = array[
            ...,
            int((coords[i, 1] - y_offset) / y_step),
            int((coords[i, 0] - x_offset) / x_step),
        ]
    return values


@njit(
    parallel=False,
    cache=True,
)  # Writing to an array cannot be parallelized as race conditions would occur.
def write_to_array(
    array: np.ndarray,
    values: np.ndarray,
    coords: np.ndarray,
    gt: tuple[float, float, float, float, float, float],
):
    """Write values using coordinates to a map. If multiple coordinates map to a single cell,
    the values are added. The operation is inplace

        Parameters:
            array: the 2-dimensional array to write to
            values: the values to write (shape: n)
            coords: the coordinates of the values (shape: 2, n)
            gt: the geotransformation. Must be unrotated

        Returns:
            array: the array with the values added (operation is inplace)
    """
    assert values.size == coords.shape[0]
    assert gt[2] + gt[4] == 0
    size = values.size
    x_offset = gt[0]
    y_offset = gt[3]
    x_step = gt[1]
    y_step = gt[5]
    for i in range(size):
        array[
            int((coords[i, 1] - y_offset) / y_step),
            int((coords[i, 0] - x_offset) / x_step),
        ] += values[i]
    return array


def clip_to_xy_bounds(
    src: DatasetReader,
    profile: Profile,
    array: np.ndarray,
    xmin: int,
    xmax: int,
    ymin: int,
    ymax: int,
) -> np.ndarray:
    """Clips rasterio dataset to given bounds.

    Args:
        src: Rasterio dataset.
        profile: Rasterio profile of dataset.
        array: Array to clip.
        xmin: Minimum xbound.
        xmax: Maximum xbound.
        ymin: Minimum ybound.
        ymax: Maximum ybound.

    Returns:
        profile: Updated profile for cut array.
        array: Array data.
    """
    window = Window.from_slices(slice(ymin, ymax), slice(xmin, xmax))
    profile.update(
        {
            "transform": src.window_transform(window),
            "height": int(window.height),
            "width": int(window.width),
        }
    )
    return profile, array[ymin:ymax, xmin:xmax].copy()


def clip_to_other(
    array: np.ndarray, src_profile: Profile, other_profile: Profile
) -> tuple[np.ndarray, Profile]:
    """Clip array to rasterio profile.

    Args:
        array: Array to clip.
        src_profile: Rasterio profile of source array.
        other_profile: Rasterio profile of array to clip to.

    Returns:
        outarray: Clipped array.
        profile: Updated profile.
    """

    xmin = round(
        (other_profile["transform"].c - src_profile["transform"].c)
        / src_profile["transform"].a
    )
    assert abs(xmin) == xmin  # assert xmin is positive
    ymin = round(
        (other_profile["transform"].f - src_profile["transform"].f)
        / src_profile["transform"].e
    )
    assert abs(ymin) == ymin  # assert ymin is positive

    profile = dict(src_profile)
    profile.update(
        {
            "transform": other_profile["transform"],
            "height": other_profile["height"],
            "width": other_profile["width"],
        }
    )
    outarray = array[
        ymin : ymin + other_profile["height"], xmin : xmin + other_profile["width"]
    ].copy()
    return outarray, profile


def upscale(
    array: np.ndarray, src_profile: np.ndarray, factor: np.ndarray
) -> tuple[np.ndarray, Profile]:
    """ "Upscale array and rasterio profile by x amount.

    Args:
        array: Array to upscale.
        src_profile: Rasterio profile of source array.
        factor: Factor by which to upscale.

    Returns:
        array: Upscaled array.
        profile: Updated rasterio profile.
    """
    profile = dict(src_profile)
    transform = src_profile["transform"]
    profile["transform"] = Affine(
        transform.a / factor,
        transform.b,
        transform.c,
        transform.d,
        transform.e / factor,
        transform.f,
    )
    profile["height"] = src_profile["height"] * factor
    profile["width"] = src_profile["width"] * factor
    array = array.repeat(factor, axis=-2).repeat(factor, axis=-1)
    return array, profile


class NetCDFHasEmtpyLayersException(Exception):
    """Raised when one or more layers are empty"""

    pass


class CreateNetCDF:
    """Class to create easy create a spatial NetCDF-file.

    Args:
        fn: Filepath.
        title: Title of NetCDF.
        source: Source of data.
        institution: Institution where data was created.
        n_timesteps: Number of timesteps in NetCDF. None if NetCDF should not have time dimension.
        lons: Array of longitudes.
        lats: Array of latitudes.
        epsg: EPSG code.
        varname: Name of variable to store.
        units: Unit of variable.
        dtype: NetCDF dtype. See NetCDF documentation for valid dtypes: https://unidata.github.io/netcdf4-python/
        chunksizes: Sizes of datachunks. (time, lat, lon) if time dimension exists, otherwise (lat, lon).
        fill_value: Value to represent nodata.
        compression_level: NetCDF compression level (1-9)
        comment: Optional dataset comment.
    """

    def __init__(
        self,
        fp: str,
        title: str,
        source: str,
        institution: str,
        n_timesteps: Union[None, int],
        lons: np.ndarray,
        lats: np.ndarray,
        epsg: int,
        varname: str,
        units: str,
        dtype: str,
        chunksizes: tuple[int],
        fill_value: Union[float, int],
        compression_level: int,
        comment: str = None,
    ) -> None:
        self.fp = fp
        self.ds = Dataset(self.fp, "w", format="NETCDF4")
        self.ds.set_always_mask(False)

        self.ds.date_created = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        self.ds.source = source
        self.ds.institution = institution
        self.ds.title = title
        self.ds.Conventions = "CF-1.6"
        if comment:
            self.ds.comment = comment

        if n_timesteps:
            self.ds.createDimension("time", n_timesteps)
        self.ds.createDimension("lat", len(lats))
        self.ds.createDimension("lon", len(lons))

        lat = self.ds.createVariable("lat", "f8", ("lat",))
        lat.standard_name = "latitude"
        lat.units = "degrees_north"
        lat.axis = "Y"
        lat[:] = lats

        lon = self.ds.createVariable("lon", "f8", ("lon",))
        lon.standard_name = "longitude"
        lon.units = "degrees_east"
        lon.axis = "X"
        lon[:] = lons

        crs = self.ds.createVariable("spatial_ref", "i4")
        crs.spatial_ref = CRS.from_epsg(epsg).to_wkt()

        if n_timesteps:
            self.times = self.ds.createVariable("time", "f4", ("time",))
            self.times.standard_name = "time"
            self.times.long_name = "time"
            self.times.units = "hours since 1970-01-01 00:00:00"
            self.times.calendar = "gregorian"

        self.values = self.ds.createVariable(
            varname,
            datatype=dtype,
            dimensions=("time", "lat", "lon") if n_timesteps else ("lat", "lon"),
            chunksizes=chunksizes,
            zlib=bool(compression_level),
            complevel=compression_level,  # ignored if zlib is False
            contiguous=False,  # do not neccesarily store contiguous on disk
            fill_value=fill_value,
        )
        self.values.standard_name = varname
        self.values.units = units
        self.current_timestep = 0

    def write(self, values: np.ndarray, dt: datetime = None) -> None:
        """Write layer to file.

        Args:
            values: Values to write.
            dt: Optional datetime to write. If NetCDF has no time dimension, do not write.
        """
        if dt:
            assert dt >= datetime(1970, 1, 1)
            self.times[self.current_timestep] = date2num(
                dt, units=self.times.units, calendar=self.times.calendar
            )
            self.values[self.current_timestep, :, :] = values
            self.current_timestep += 1
        else:
            assert not hasattr(self, "times")
            self.values[:, :] = values

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Check if NetCDF has no empty layers on exit."""
        if hasattr(self, "times"):
            checklayer = self.times
        else:
            checklayer = self.values

        if np.ma.is_masked(checklayer[:]):
            self.ds.close()
            os.remove(self.fp)
            raise NetCDFHasEmtpyLayersException
        else:
            self.ds.close()
            if exc_type is not None:
                os.remove(self.fp)
