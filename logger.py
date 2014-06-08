#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import signal
import os
import sys

def initlog(name):
	return logging.getLogger(name)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

file_formatter   = logging.Formatter("%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s")
stream_formatter = logging.Formatter("%(asctime)s.%(msecs)03d - %(name)-12s - %(levelname)-8s - %(message)s", datefmt="%H:%M:%S")

file_handler = logging.FileHandler('/tmp/failover.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(file_formatter)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(stream_formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

