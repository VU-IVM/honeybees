# -*- coding: utf-8 -*-
from random import random
from numba import njit


@njit
def bernoulli(p: float) -> bool:
    """Takes value from bernoulli distribution.

    Args:
        p: Probability

    Returns:
        outcome: True or False
    """
    assert 0 <= p <= 1
    return random() < p
