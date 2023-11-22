# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Any

RADIUS_EARTH_EQUATOR = 40075017  # m
distance_1_degree_latitude = RADIUS_EARTH_EQUATOR / 360  # m


def timeprint(*args, **kwargs: Any) -> None:
    """This function prints the current time in isoformat, followed by the normal print.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    print(datetime.now().isoformat(), *args, **kwargs)
