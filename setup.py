#!/usr/bin/env python
# -*- coding: utf-8 -*-


import setuptools

try:
    import multiprocessing  # NOQA
except ImportError:
    pass


setuptools.setup(
    setup_requires=["pbr"],
    pbr=True)
