# -*- coding: utf-8 -*-


import logging
import os.path


DIR_HOME = os.path.expanduser("~")
"""Default home directory."""

DIR_APP = os.path.join(DIR_HOME, ".fuelpdsh")
"""Default app directory."""


def logger(namespace):
    return logging.getLogger("fuelpdsh." + namespace)
