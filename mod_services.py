#!/usr/bin/env python
# -*- coding: utf-8 -*-

import config

import mod_logger
log = mod_logger.initlog(__name__)

import mod_utils

def start():
    ret = 0

    for service in config.services:
        log.info("Starting service '%s' ..." % (service))
        res, output  = mod_utils.execute("service %s start" % (service), timeout=20)
        ret         += res

        if res:
            log.error("Failed to start service %s: %s", service, ''.join(output).replace('\n', '\\n'))

    return not ret

def stop():
    ret = 0

    for service in config.services:
        log.info("Stopping service '%s' ..." % (service))
        res, output  = mod_utils.execute("service %s stop" % (service), timeout=20)
        ret         += res

        if res:
            log.error("Failed to stop service %s: %s", service, ''.join(output).replace('\n', '\\n'))

    return not ret

