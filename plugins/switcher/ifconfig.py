#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import sys
import time

import config

import mod_logger
log = mod_logger.initlog(__name__)

config_checks = {
    "virtual_ip": { "type": "str", "default": False,  "check": False },
    "interface":  { "type": "str", "default": "eth0", "check": False},
}

config_optional = [
]

def execute(cmd, timeout=10):
    try:
        pipe = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except Exception, e:
        log.error("Failed to execute command '%s' (%s)", cmd, e)
        return 1, ""

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

def add_virtual_ip(interface, virtual_ip):
    res, output = execute("ip addr add dev %s local %s" % (interface, virtual_ip))

    if res:
        log.error("failed to set virtual IP %s on %s", virtual_ip, interface)
        return False

    return True

def del_virtual_ip(interface, virtual_ip):
    res, output = execute("ip addr delete dev %s local %s" % (interface, virtual_ip))

    if res:
        log.error("failed to set virtual IP %s on %s", virtual_ip, interface)
        return False

    return True

def send_gratuitous_arp(interface, virtual_ip):
    res, output = execute("arping -U %s -c 2 -I %s" % (virtual_ip, interface))

    if res:
        log.error("failed to send gratuitous ARP on %s", interface)
        return False

    return True

### PLUGIN INTERFACE ###

# function called by monitor to activate traffic
def activate():
    global interface
    global virtual_ip

    if not add_virtual_ip(interface, virtual_ip):
        return False

    if not send_gratuitous_arp(interface, virtual_ip):
        return False

    return True

# function called by monitor to activate traffic
def deactivate():
    global interface
    global virtual_ip

    if not del_virtual_ip(interface, virtual_ip):
        return False

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

