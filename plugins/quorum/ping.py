#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import sys
import time

import config

import mod_logger
log = mod_logger.initlog(__name__)

import mod_utils

config_checks = {
    "interval": { "type": "float", "default": 0.2, "check": ">= 0.2" },
    "hosts":    { "type": "list",  "default": [],  "check": "checkNonEmptyList(value)" },
}

config_optional = [
]

### PLUGIN INTERFACE ###

# function called by monitor to get third party quorum status (return True on success)
def get():
    global hosts
    global interval

    ret     = 0
    count   = 3
    timeout = 3.0

    for host in hosts:
        res, output  = mod_utils.execute("/bin/ping -n -c%d -w%.1f -i%.1f %s" % (count, timeout, interval , host))
        ret         += res

    return not res

# function called by monitor to update/send our status to a third party (return True on success)
def update():
    return True

# function called by monitor during koublad startup (return True on success)
def run():
    return True

# function called by monitor during koublad tear down (return True on success)
def terminate():
    return True

### END OF PLUGIN INTERFACE ###


# read configuration
config_dict = config.defaultVariables(config_checks)
config_dict = config.parseConfigurationFile(config.config_file, config_checks, config_optional, config_dict, plugin_name=__name__)

# set variable globaly for easier access
interval = config_dict['interval']
hosts    = config_dict['hosts']


log.info("Plugin '%s' loaded" % (__name__))
config.show(config_dict)

