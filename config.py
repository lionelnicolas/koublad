#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import os
import re
import sys

import mod_plugins

import mod_logger
log = mod_logger.initlog(__name__)

CONFIG_FILE = "/etc/koublad.conf"
DRBD_DIR    = "/etc/drbd.d"
PLUGIN_DIR  = "plugins/"

RE_CONFIG_LINE   = re.compile("^[\ \t]*()([a-zA-Z0-9_]+)[\ \t]*=[\ \t]*([^#\n\r]+).*$")
RE_CONFIG_LINE_P = re.compile("^[\ \t]*([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)[\ \t]*=[\ \t]*([^#\n\r]+).*$")
RE_DRBD_RESOURCE = re.compile("^[\ \t]*resource[\ \t]+([a-z0-9]+).*$")

config_checks = {
    "port":            { "type": "int",   "default": 4997,       "check": "> 1024" },
    "role":            { "type": "str",   "default": False,      "check": "in ['master', 'slave']" },
    "initdead":        { "type": "float", "default": 5.0,        "check": "> 0.0" },
    "peer_host":       { "type": "str",   "default": False,      "check": False },
    "peer_port":       { "type": "int",   "default": False,      "check": "> 1024" },
    "timeout":         { "type": "float", "default": 2.0,        "check": ">= 0.1" },
    "interval":        { "type": "float", "default": 0.2,        "check": ">= 0.2" },
    "services":        { "type": "list",  "default": [],         "check": "checkServices(value)" },
    "drbd_resources":  { "type": "list",  "default": [],         "check": "checkDrbdResources(value)" },
    "plugin_dir":      { "type": "str",   "default": PLUGIN_DIR, "check": "checkDirectory(value)" },
    "quorum_plugin":   { "type": "str",   "default": False,      "check": "checkQuorumPlugin(value)" },
    "switcher_plugin": { "type": "str",   "default": False,      "check": "checkSwitcherPlugin(value)" },
}

config_optional = [
    "quorum_plugin",
    "switcher_plugin",
]

config_dict = dict()

def splitIntoList(value):
    if   len(value) == 0:       return []
    elif value.count(',') == 0: return [value]
    else:                       return value.split(',')

def convertType(name, value, vartype):
    ret   = False
    value = value.strip()

    try:
        if   vartype == "list":  ret = splitIntoList(value)
        elif len(value) == 0:    ret = False
        elif vartype == "int":   ret = int(value)
        elif vartype == "float": ret = float(value)
        else:                    ret = str(value)

    except ValueError:
        log.fatal("Parameter '%s' should be a %s" % (name, vartype))

    return ret

def checkValue(name, value, check):
    if not check:            return True
    elif "(value)" in check: return eval(check)
    elif type(value) == str: return eval("\"%s\" %s" % (value, check))
    else:                    return eval("%.1f %s" % (value, check))

def checkNonEmptyList(value):
    return len(value) != 0

def checkDrbdResources(resources):
    global drbd_dir

    resources_dup = list(resources)

    for res in glob.glob("%s/*.res" % (drbd_dir)):
        resource = False

        for line in open(res).readlines():
            match = RE_DRBD_RESOURCE.match(line)

            if match:
                resource = match.group(1)

                if resources.count(resource):
                    resources_dup.remove(resource)

    if len(resources_dup):
        log.fatal("The following DRBD resources do not exist: %s" % (resources_dup))

    return True

def checkServices(services):
    for service in services:
        if not os.path.isfile(os.path.join("/etc/init.d", service)):
            log.fatal("Service '%s' does not exist" % (service))

    return True

def checkQuorumPlugin(filepath):
    global config_dict

    if not filepath:
        return True

    return os.path.isfile(os.path.join(config_dict['plugin_dir'], "quorum", "%s.py" % filepath)) or log.fatal("Quorum plugin '%s' does not exist." % (filepath))

def checkSwitcherPlugin(filepath):
    global config_dict

    if not filepath:
        return True

    return os.path.isfile(os.path.join(config_dict['plugin_dir'], "switcher", "%s.py" % filepath)) or log.fatal("Switcher plugin '%s' does not exist." % (filepath))

def checkFile(filepath):
    return os.path.isfile(filepath) or log.fatal("File '%s' does not exist." % (filepath))

def checkDirectory(dirpath):
    return os.path.isdir(dirpath) or log.fatal("Directory '%s' does not exist." % (dirpath))

def defaultVariables(config_checks):
    config_dict = dict()

    for name in config_checks.keys():
        config_dict[name] = config_checks[name]['default']

    return config_dict

def parseConfigurationFile(config_file, config_checks, config_optional, config_dict, plugin_name=False):
    for line in open(config_file).readlines():
        if plugin_name:
            match = RE_CONFIG_LINE_P.match(line)
        else:
            match = RE_CONFIG_LINE.match(line)

        if match:
            plugin = match.group(1)
            name   = match.group(2).strip()
            value  = match.group(3).replace('\t', '').replace(' ', '').strip()

            if plugin_name and plugin != plugin_name:
                print "non-matching plugin %s -- %s" % (plugin, plugin_name)

            if name in config_checks.keys():
                vartype           = config_checks[name]['type']
                check             = config_checks[name]['check']
                config_dict[name] = convertType(name, value, vartype)
                res               = checkValue(name, config_dict[name], check)

                if not res:
                    log.fatal("Parameter '%s' validation failed (%s)" % (name, check))


    # check mandatory variables
    for name in config_checks.keys():
        if name not in config_optional and config_dict[name] == False:
            log.fatal("Parameter '%s' cannot be empty or unset" % (name))

    return config_dict

def show(data=False):
    global config_dict

    if not data:
        data = config_dict

    keys = data.keys()
    keys.sort()

    for name in keys:
        print "%-16s: %s" % (name, data[name])
    print


# set configuration file path
if len(sys.argv) > 1: config_file = sys.argv[1]
else:                 config_file = CONFIG_FILE

checkFile(config_file)


# set DRBD configuration directory
if len(sys.argv) > 2: drbd_dir = sys.argv[2]
else:                 drbd_dir = DRBD_DIR

checkDirectory(drbd_dir)


# set default values
config_dict = defaultVariables(config_checks)


# parse configuration file
config_dict = parseConfigurationFile(config_file, config_checks, config_optional, config_dict)


# set variable globaly (seems ugly to use exec(), maybe use globals() dict in the future
for name in config_checks.keys():
    exec("%s = config_dict[name]" % (name))


# search for plugins
mod_plugins.search(plugin_dir)

