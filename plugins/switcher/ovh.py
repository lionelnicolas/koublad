#!/usr/bin/env python
# -*- coding: utf-8 -*-

import config

log = mod_logger.initlog(__name__)

config_checks = {
    "nickhandle":          { "type": "str",  "default": False, "check": False },
    "password":            { "type": "str",  "default": False, "check": False },
    "ip_failover_owner":   { "type": "str",  "default": False, "check": False },
    "ip_failover_address": { "type": "str",  "default": False, "check": False },
    "ip_failover_target":  { "type": "str",  "default": False, "check": False },
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
nickhandle          = config_dict['nickhandle']
password            = config_dict['password']
ip_failover_owner   = config_dict['ip_failover_owner']
ip_failover_address = config_dict['ip_failover_address']
ip_failover_target  = config_dict['ip_failover_target']

log.info("Plugin '%s' loaded" % (__name__))
config.show(config_dict)

