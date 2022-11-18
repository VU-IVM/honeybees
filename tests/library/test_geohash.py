# -*- coding: utf-8 -*-
from honeybees.library import geohash

def test_geohash_encode_decode_coord(pytestconfig):
    lon = 86.925278
    lat = 27.988056
    nbits = 61

    gh = geohash.encode_precision(lon, lat, nbits)
    assert "{0:b}".format(gh) == '111100111010110111111100100101010000100100000011111101011000010'
    lon, lat = geohash.decode(gh, nbits)
    assert lon == 86.92527785897255 
    assert lat == 27.9880559630692

    north = geohash.shift(gh, nbits, 0, 1)
    assert "{0:b}".format(north) == '111100111010110111111100100101010000100100000011111101011001000'

def test_geohash_encode_decode_m(pytestconfig):
    x = 10000
    y = 20000
    nbits = 61

    gh = geohash.encode_precision(x, y, nbits, minx=0, maxx=20000, miny=0, maxy=40000)
    x_, y_ = geohash.decode(gh, nbits, minx=0, maxx=20000, miny=0, maxy=40000)
    assert x == x_
    assert y == y_


def test_window_coordinates(bits=32):
    assert geohash.window(31) == (0.0054931640625, 0.0054931640625)
    assert geohash.window(32) == (0.0054931640625, 0.00274658203125)

def test_window_meters(bits=32, minx=0, maxx=10_000, miny=0, maxy=10_000):
    assert geohash.window(31, minx, maxx, miny, maxy) == (0.152587890625, 0.30517578125)
    assert geohash.window(32, minx, maxx, miny, maxy) == (0.152587890625, 0.152587890625)

def test_plot_geohashes(plt):
    geohash.plot_geohash_shifts(show=False)
