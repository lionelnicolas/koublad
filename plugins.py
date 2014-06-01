#!/usr/bin/env python

import imp
import os
import re
import sys

RE_PLUGIN_FILE = re.compile("^([^_]+)_(.*)\.py$")

plugins = False

class Plugins():
	# plugins used to switch IP address to master
	switcher = dict()

	# plugins used to get third party quorum
	quorum = dict()

def GetPlugins(plugindir):
	global plugins

	plugins = Plugins()

	for filename in os.listdir(plugindir):
		match = RE_PLUGIN_FILE.match(filename)

		if match:
			plugin_type = match.group(1)
			plugin_name = match.group(2)

			plugin_desc = imp.find_module("%s_%s" % (plugin_type, plugin_name), [plugindir])

			if   plugin_type == "quorum":
				plugins.quorum[plugin_name] = plugin_desc

			elif plugin_type == "switcher":
				plugins.switcher[plugin_name] = plugin_desc

	return plugins

def LoadPlugin(plugin_type, plugin_name):
	global plugins

	if not plugins:
		sys.stderr.write("Plugins detection has not been done, please call GetPlugins(plugin_path) first.\n")
		return False

	if   plugin_type == "quorum":
		plugin = plugins.quorum[plugin_name]
	elif plugin_type == "switcher":
		plugin = plugins.quorum[plugin_name]
	else:
		return False

	return imp.load_module("%s_%s" % (plugin_type, plugin_name), *plugin)

def ListPlugins():
	global plugins

	if not plugins:
		sys.stderr.write("Plugins detection has not been done, please call GetPlugins(plugin_path) first.\n")
		return False

	print "Found plugins :"

	print "    Quorum :"
	for plugin in plugins.quorum.keys():
		print "        %s -- %s" % (plugin, plugins.quorum[plugin][1])
	print

	print "    Failover switcher :"
	for plugin in plugins.switcher.keys():
		print "        %s -- %s" % (plugin, plugins.switcher[plugin][1])
	print

	return True

def test():
	global plugins

	GetPlugins("plugins")

	ListPlugins(plugins)

	quorum = LoadPlugin("quorum", "http")
	quorum.caca()

