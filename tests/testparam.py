# -*- coding: utf-8 -*-
import pytest


@pytest.fixture()
def name(pytestconfig):
    return pytestconfig.getoption("extended")
