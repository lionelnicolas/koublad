#!/usr/bin/env python
# -*- coding: utf-8 -*-

import config

log = mod_logger.initlog(__name__)

config_checks = {
}

config_optional = [
]

### PLUGIN INTERFACE ###

# function called by monitor to notify an activate action
def activate():
    return True

# function called by monitor to notify a deactivate action
def deactivate():
    return True

# function used to send a custom notification
def event(msg):
    return True

### END OF PLUGIN INTERFACE ###


# read configuration
config_dict = config.defaultVariables(config_checks)
config_dict = config.parseConfigurationFile(config.config_file, config_checks, config_optional, config_dict, plugin_name=__name__)

log.info("Plugin '%s' loaded" % (__name__))
config.show(config_dict)

