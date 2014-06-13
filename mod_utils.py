#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import time

import mod_logger
log = mod_logger.initlog(__name__)

def execute(cmd, timeout=10):
    pipe  = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    res   = pipe.poll()
    start = time.time()

    while res == None and time.time() - start < timeout:
        res = pipe.poll()
        time.sleep(0.1)

    if res == None:
        pipe.kill()
        log.warn("Killed command '%s'" % (cmd))
        res = 1

    return res, pipe.stdout.readlines()

