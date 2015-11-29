# -*- coding: utf-8 -*-


import codecs
import logging
import Queue
import threading
import time

import fuelpdsh


LOG = fuelpdsh.logger(__name__)
"""Logger."""


class Stream(object):

    QUEUE_LENGTH = 10000
    NO_ITEM = object()

    def __init__(self, original_stream):
        self.stream = original_stream
        self.stop_ev = threading.Event()
        self.queue = Queue.Queue(self.QUEUE_LENGTH)
        self.thread = None

    def run(self):
        self.thread = threading.Thread(target=self.background_task)
        self.thread.daemon = True
        self.thread.start()

        LOG.debug("Background thread %s was started", self.thread.ident)

    def stop(self):
        self.stop_ev.set()

    def wait(self):
        if self.thread is None:
            return

        thread, self.thread = self.thread, None

        LOG.debug("Starting queue flush for thread %s", thread.ident)
        self.queue.join()

        LOG.debug("Waiting for background thread %s to be finished", thread.ident)
        thread.join()

    def background_task(self):
        while not self.stop_ev.is_set():
            item = self.fetch_item()
            if item is self.NO_ITEM:
                time.sleep(0.01)
                continue
            self.process_item(item)

        LOG.debug("Stop event is set for thread %s, start to flush queue", threading.current_thread().ident)

        while not self.queue.empty():
            item = self.fetch_item()
            if item is self.NO_ITEM:
                break
            self.process_item(item)

        LOG.debug("Thread %s finished", threading.current_thread().ident)

    def fetch_item(self):
        try:
            return self.queue.get_nowait()
        except Queue.Empty:
            return self.NO_ITEM

    def put_item(self, data):
        self.queue.put(data, True)

    def process_item(self, item):
        self.stream.write(item)
        self.stream.write("\n")
        self.queue.task_done()

    def make_host_stream(self, hostname, hostname_length):
        return HostStream(self, hostname, hostname_length)


class HostStream(object):

    __slots__ = "prefix", "stream", "accumulator", "closed", "lock"

    DECODER = codecs.getdecoder("unicode_escape")

    def __init__(self, stream, hostname, hostname_length):
        self.prefix = hostname.ljust(hostname_length) + ":  "
        self.stream = stream
        self.accumulator = ""
        self.closed = False
        self.lock = threading.RLock()

    def put(self, data):
        if not self.closed:
            data = self.DECODER(data, "replace")
            self.stream.put_item(self.prefix + data[0])

    def write(self, data):
        chunks = []

        with self.lock:
            self.accumulator += data
            if "\n" in self.accumulator:
                chunks = self.accumulator.rsplit("\n")
                self.accumulator = chunks.pop()

        for chunk in chunks:
            self.put(chunk)

    def close(self):
        with self.lock:
            if self.accumulator:
                self.put(self.accumulator)
                self.accumulator = ""
            self.closed = True

    flush = close
