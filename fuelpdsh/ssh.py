# -*- coding: utf-8 -*-


import sys

import asyncssh

import fuelpdsh


LOG = fuelpdsh.logger(__name__)
"""Logger."""


class SSHClientSession(asyncssh.SSHClientSession):

    PREFIX_LENGTH = 10

    def __init__(self, hostname):
        super(SSHClientSession, self).__init__()

        self.obuffer = ""
        self.ebuffer = ""
        self.prefix = hostname.ljust(self.PREFIX_LENGTH) + ": "

    def data_received(self, data, datatype):
        if datatype == asyncssh.EXTENDED_DATA_STDERR:
            self.ebuffer += data
            self.ebuffer = self.doprint(self.ebuffer, stderr=True)
        else:
            self.obuffer += data
            self.obuffer = self.doprint(self.obuffer, stderr=False)

        return super(SSHClientSession, self).data_received(data, datatype)

    def doprint(self, buf, *, flush=False, stderr=False):
        if not buf:
            return buf

        stream = sys.stderr if stderr else sys.stdout

        if flush:
            print(self.data(buf), file=stream)
            return ""

        buf = buf.split("\n")
        for chunk in buf[:-1]:
            print(self.data(chunk), file=stream)

        return buf[-1] if buf else ""

    def data(self, text):
        return self.prefix + text

    def connection_lost(self, exc):
        self.doprint(self.obuffer, stderr=False, flush=True)
        self.doprint(self.ebuffer, stderr=True, flush=True)

        if exc:
            LOG.error("SSH connection %s has been dropped: %s", self, exc)
