# -*- coding: utf-8 -*-
from honeybees.library.raster import (
    pixel_to_coord,
    pixels_to_coords,
    reproject_pixel,
    coord_to_pixel,
    coords_to_pixels,
)
import numpy as np


def test_reproject_pixel():
    from_gt = (
        73.517314369,
        0.00026949458512559436,
        0.0,
        18.438819522,
        0.0,
        -0.0002694945854623959,
    )
    to_gt = (
        73.1666666666954,
        0.008333333333339965,
        0.0,
        19.500000000006278,
        0.0,
        -0.008333333333339965,
    )

    px_in, py_in = 100, 530
    px_out, py_out = reproject_pixel(from_gt, to_gt, px_in, py_in)

    assert px_out == 45
    assert py_out == 144


def test_pixel_to_coord():
    gt = (
        73.517314369,
        0.00026949458512559436,
        0.0,
        18.438819522,
        0.0,
        -0.0002694945854623959,
    )
    lon, lat = pixel_to_coord(10, 56, gt)
    assert (
        lon == 73.517314369 + 10 * 0.00026949458512559436
        and lat == 18.438819522 + 56 * -0.0002694945854623959
    )


def test_pixels_to_coords():
    gt = (-180, 1 / (12 * 360), 0, 90, 0, -1 / (12 * 360))
    n = 100

    xs = np.random.uniform(100, 1000, n)
    ys = np.random.uniform(90, 2300, n)
    pixels = np.squeeze(np.dstack([xs, ys]))
    coords = pixels_to_coords(pixels, gt)
    for i, (x, y) in enumerate(zip(xs, ys)):
        lon, lat = pixel_to_coord(x, y, gt)
        assert lon == coords[i, 0]
        assert lat == coords[i, 1]


def test_coord_to_pixel():
    gt = (
        73.517314369,
        0.00026949458512559436,
        0.0,
        18.438819522,
        0.0,
        -0.0002694945854623959,
    )
    px, py = coord_to_pixel(
        (
            73.517314369 + 10 * 0.00026949458512559436,
            18.438819522 + 56 * -0.0002694945854623959,
        ),
        gt,
    )
    assert px == 10 and py == 56
    px, py = coord_to_pixel(
        (
            73.517314369 + 10 * 0.00026949458512559436 - 0.000001,
            18.438819522 + 56 * -0.0002694945854623959 + 0.000001,
        ),
        gt,
    )
    assert px == 9 and py == 55


def test_coords_to_pixels():
    gt = (-180, 1 / (12 * 360), 0, 90, 0, -1 / (12 * 360))
    n = 100

    lons = np.random.uniform(-180, 180, n)
    lats = np.random.uniform(-80, 80, n)
    coords = np.squeeze(np.dstack([lons, lats]))
    pxs, pys = coords_to_pixels(coords, gt)
    for i, (lon, lat) in enumerate(zip(lons, lats)):
        px, py = coord_to_pixel((lon, lat), gt)
        assert px == pxs[i]
        assert py == pys[i]

    gt = (-10000, 1000, 0, 20000, 0, -1000)
    n = 100

    xs = np.random.uniform(-10000, 10000, n)
    ys = np.random.uniform(10000, 20000, n)
    coords = np.squeeze(np.dstack([xs, ys]))
    pxs, pys = coords_to_pixels(coords, gt)
    for i, (x, y) in enumerate(zip(xs, ys)):
        px, py = coord_to_pixel((x, y), gt)
        assert px == pxs[i]
        assert py == pys[i]
