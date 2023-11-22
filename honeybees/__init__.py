# -*- coding: utf-8 -*-
"""This package is a framework for creating large-scale agent-based geographical models.

Submodules
==========


"""

__title__ = "honeybees"
__version__ = 0.1
__email__ = "j.a.debruijn at outlook com"
__status__ = "development"

from numba import config

config.THREADING_LAYER = "safe"  # set threading mode for numba to safe, requires tbb
