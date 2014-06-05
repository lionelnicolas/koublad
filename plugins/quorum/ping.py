#!/usr/bin/env python

import subprocess
import time

import config

config_checks = {
	"interval": { "type": "float", "default": 0.2, "check": ">= 0.2" },
	"hosts":    { "type": "list",  "default": [],  "check": "checkNonEmptyList(value)" },
}

config_optional = [
]

def ping(host):
	pipe = subprocess.Popen(["/bin/ping", "-c5", "-w3", "-i0.2", host], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	res  = pipe.poll()

	while res == None:
		res = pipe.poll()
		time.sleep(0.05)
	
	return res


### PLUGIN INTERFACE ###

# function called by monitor to get third party quorum status (return True on success)
def get():
	global hosts

	res = 0
	for host in hosts:
		res += ping(host)
	
	return not res

# function called by monitor to update/send our status to a third party (return True on success)
def update():
	return True

# function called by monitor during failover-manager startup (return True on success)
def run():
	return True

# function called by monitor during failover-manager tear down (return True on success)
def terminate():
	return True

### END OF PLUGIN INTERFACE ###


# read configuration
config_dict = config.defaultVariables(config_checks)
config_dict = config.parseConfigurationFile(config.config_file, config_checks, config_optional, config_dict, plugin_name=__name__)

# set variable globaly for easier access
interval = config_dict['interval']
hosts    = config_dict['hosts']

print "Plugin '%s' loaded" % (__name__)
config.show(config_dict)

