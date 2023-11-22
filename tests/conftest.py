# -*- coding: utf-8 -*-
def pytest_addoption(parser):
    parser.addoption("--extended", action="store_true")
    parser.addoption("--compare", action="store_true")
