#!/usr/bin/env python
# -*- coding: utf-8 -*-


import setuptools


setuptools.setup(
    name="fuel-pdsh",
    description="Pure Python PDSH replacement which work on Fuel OpenStack node.",
    version="0.0.0",
    author="Sergey Arkhipov",
    license="MIT",
    author_email="serge@aerialsounds.org",
    maintainer="Sergey Arkhipov",
    maintainer_email="serge@aerialsounds.org",
    url="https://github.com/9seconds/fuel-pdsh",
    entry_points={
        "console_scripts": ["fuel-pdsh=fuel_pdsh.pdsh:main"],
    },
    install_requires=[
        "python-fuelclient",
        "spur",
        "futures"
    ],
    packages=setuptools.find_packages("."),
    zip_safe=True
)
