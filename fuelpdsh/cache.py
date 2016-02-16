# -*- coding: utf-8 -*-


import errno
import gzip
import functools
import os
import os.path
import pickle

import fuelpdsh


LOG = fuelpdsh.logger(__name__)
"""Logger."""

NO_VALUE = object()
"""Sentinel object."""


def clear_cache(cachefile):
    try:
        os.remove(cachefile)
    except os.error as err:
        if err.errno != errno.ENOENT:
            raise


def cached(cachefile):
    def outer_decorator(func):
        @functools.wraps(func)
        def inner_decorator(*args, **kwargs):
            cached_value = get_cached_value(cachefile)

            if cached_value is NO_VALUE:
                cached_value = func(*args, **kwargs)
                set_cached_value(cachefile, cached_value)

            return cached_value

        return inner_decorator
    return outer_decorator


def get_cached_value(cachefile):
    try:
        with gzip.open(cachefile, "rb") as filep:
            return pickle.load(filep)
    except Exception as exc:
        LOG.warning("Cannot load cached file: %s", exc)
        return NO_VALUE


def set_cached_value(cachefile, value):
    try:
        os.makedirs(os.path.dirname(cachefile))
    except:
        pass

    try:
        with gzip.open(cachefile, "wb") as filep:
            pickle.dump(value, filep)
    except Exception as exc:
        LOG.warning("Cannot store cached value %s to %s: %s",
                    value, cachefile, exc)
