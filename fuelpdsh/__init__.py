# -*- coding: utf-8 -*-


import logging

try:
    import gevent.monkey
except ImportError:
    pass
else:
    gevent.monkey.patch_all()


def logger(name):
    return logging.getLogger("fuelpdsh." + name)
