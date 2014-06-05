#!/usr/bin/env python
# -*- coding: utf-8 -*-

import imp
import os
import re
import sys

RE_PLUGIN_FILE = re.compile("^([^\.]+)\.py$")

found    = dict()
quorum   = False
switcher = False

def search(plugin_dir):
	global found

	for subdir in os.listdir(plugin_dir):
		if not os.path.isdir(os.path.join(plugin_dir, subdir)):
			continue

		for filename in os.listdir(os.path.join(plugin_dir, subdir)):
			if not os.path.isfile(os.path.join(plugin_dir, subdir, filename)):
				continue

			match = RE_PLUGIN_FILE.match(filename)

			if match:
				plugin_type = subdir
				plugin_name = match.group(1)
				plugin_desc = imp.find_module(plugin_name, [os.path.join(plugin_dir, plugin_type)])

				if not found.has_key(plugin_type):
					found[plugin_type] = dict()

				found[plugin_type][plugin_name] = plugin_desc

	return found

def load(plugin_type, plugin_name):
	global found

	if not found:
		sys.stderr.write("Plugins detection has not been done, please call plugins.search(plugin_dir) first.\n")
		return False

	if found.has_key(plugin_type) and found[plugin_type].has_key(plugin_name):
		return imp.load_module("%s_%s" % (plugin_type, plugin_name), *found[plugin_type][plugin_name])

	return False

def loadQuorum(quorum_plugin):
	global quorum

	# load quorum plugin if any
	if quorum_plugin:
		quorum = load("quorum", quorum_plugin) or fail("Failed to load quorum plugin '%s'" % (quorum_plugin))

def loadSwitcher(switcher_plugin):
	global switcher

	# load switcher plugin if any
	if switcher_plugin:
		switcher = load("switcher", switcher_plugin) or fail("Failed to load switcher plugin '%s'" % (switcher_plugin))

def show():
	global found

	if not found:
		sys.stderr.write("Plugins detection has not been done, please call plugins.search(plugin_dir) first.\n")
		return False

	print "Found plugins :"

	for plugin_type in found.keys():
		print "    %s :" % (plugin_type.title())
		for plugin_name in found[plugin_type].keys():
			print "        %s -- %s" % (plugin_name, found[plugin_type][plugin_name][1])
		print

	return True

