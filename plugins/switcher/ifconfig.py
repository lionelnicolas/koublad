#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import struct
import subprocess
import sys
import time

import config
import mod_utils

ETHER_BCAST = "\xff\xff\xff\xff\xff\xff" # FF:FF:FF:FF:FF:FF
ETHER_TYPE  = 0x0806                     # ARP

ARP_HTYPE = 1     # Ethernet
ARP_PTYPE = 0x800 # IP
ARP_HLEN  = 6     # Hardware address length
ARP_PLEN  = 4     # Protocol address length
ARP_OPER  = 1     # Request

import mod_logger
log = mod_logger.initlog(__name__)

config_checks = {
    "virtual_ip": { "type": "str", "default": False,  "check": False },
    "interface":  { "type": "str", "default": "eth0", "check": False},
}

config_optional = [
]

def add_virtual_ip(interface, virtual_ip):
    res, output = mod_utils.execute("ip addr add dev %s local %s" % (interface, virtual_ip))

    if res:
        log.error("failed to set virtual IP %s on %s", virtual_ip, interface)
        return False

    return True

def del_virtual_ip(interface, virtual_ip):
    res, output = mod_utils.execute("ip addr delete dev %s local %s" % (interface, virtual_ip))

    if res:
        log.error("failed to set virtual IP %s on %s", virtual_ip, interface)
        return False

    return True

def send_gratuitous_arp(interface, virtual_ip):
    raw_socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    raw_socket.bind((interface, ETHER_TYPE))

    ether_src_addr = raw_socket.getsockname()[4]

    eth_layer  = ETHER_BCAST
    eth_layer += ether_src_addr
    eth_layer += struct.pack("!h", ETHER_TYPE)

    arp_layer  = struct.pack("!hhBBh", ARP_HTYPE, ARP_PTYPE, ARP_HLEN, ARP_PLEN, ARP_OPER)
    arp_layer += ether_src_addr
    arp_layer += socket.inet_aton(virtual_ip)
    arp_layer += ETHER_BCAST
    arp_layer += socket.inet_aton(virtual_ip)

    raw_socket.send(eth_layer+arp_layer)
    raw_socket.close()

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

