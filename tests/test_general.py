# -*- coding: utf-8 -*-
from numba import config, njit, threading_layer
import numpy as np
import honeybees

def test_treading_layer():
    @njit(parallel=True)
    def foo(a, b):
        return a + b

    x = np.arange(10.)
    y = x.copy()

    # this will force the compilation of the function, select a threading layer
    # and then execute in parallel
    foo(x, y)

    # assert threading layer chosen is tbb
    assert threading_layer() == 'tbb'