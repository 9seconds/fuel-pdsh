# -*- coding: utf-8 -*-


import logging


def logger(name):
    return logging.getLogger("fuelpdsh." + name)
