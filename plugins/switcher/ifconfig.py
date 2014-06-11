#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import sys
import time

import config

import mod_logger
log = mod_logger.initlog(__name__)

config_checks = {
    "virtual_ip": { "type": "str", "default": False },
    "interface":  { "type": "str", "default": "eth0:0" },
}

config_optional = [
]


### PLUGIN INTERFACE ###

# function called by monitor to activate traffic
def activate():
    return True

# function called by monitor to activate traffic
def deactivate():
    return True

### END OF PLUGIN INTERFACE ###


# read configuration
config_dict = config.defaultVariables(config_checks)
config_dict = config.parseConfigurationFile(config.config_file, config_checks, config_optional, config_dict, plugin_name=__name__)

# set variable globaly for easier access
virtual_ip = config_dict['virtual_ip']
interface  = config_dict['interface']

log.info("Plugin '%s' loaded" % (__name__))
config.show(config_dict)

