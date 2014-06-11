#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import signal
import os
import re
import sys

def critical_with_shutdown(self, msg, *args, **kwargs):
    if logging.CRITICAL >= self.getEffectiveLevel():
        apply(self._log, (logging.CRITICAL, msg, args), kwargs)

    # we've got a critical error, shutdown ...
    os.kill(os.getpid(), signal.SIGTERM)

logging.Logger.critical = critical_with_shutdown
logging.Logger.fatal    = logging.Logger.critical

def initlog(name):
    return logging.getLogger(re.sub("^mod_", "", name))

logger = logging.getLogger()
logger.setLevel(logging.INFO)

file_formatter   = logging.Formatter("%(asctime)s - %(name)-8s - %(levelname)-6s - %(message)s")
stream_formatter = logging.Formatter("%(asctime)s.%(msecs)03d - %(name)-8s - %(levelname)-6s - %(message)s", datefmt="%H:%M:%S")

file_handler = logging.FileHandler('/tmp/failover.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(file_formatter)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(stream_formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

