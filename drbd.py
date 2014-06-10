#!/usr/bin/env python
# -*- coding: utf-8 -*-

import config
import glob
import os
import re
import subprocess
import sys
import time

import logger
log = logger.initlog(__name__)

RE_DRBD_RESOURCE   = re.compile("^[\ \t]*resource[\ \t]+([a-z0-9]+).*$")
RE_DRBD_DEVICE     = re.compile("^[\ \t]*device[\ \t]+([a-z0-9/]+).*$")
RE_DRBD_ROLE       = re.compile("^([^/]+)/([^\n]+)$")
RE_DRBD_MINOR      = re.compile("^/dev/drbd([0-9]+)$")
RE_DRBD_PROC_LINE1 = re.compile("^[ \t]*([0-9]+): cs:([^ ]+) ro:([^/]+)/([^ ]+) ds:([^/]+)/([^ ]+) ([^ ]+) ([^ ]+)\n$")
RE_DRBD_PROC_LINE2 = re.compile("^[ \t]*ns:([0-9]+) nr:([0-9]+) dw:([0-9]+) dr:([0-9]+) al:([0-9]+) bm:([0-9]+) lo:([0-9]+) pe:([0-9]+) ua:([0-9]+) ap:([0-9]+) ep:([0-9]+) wo:([a-z]+) oos:([0-9]+)\n$")

RE_FUSER = re.compile("^[ \t]+([^ \t]+)[ \t]+([0-9]+)[ \t]+([^ \t]+)[ \t]+(.*)\n$")

PROC_DRBD   = "/proc/drbd"
PROC_MOUNTS = "/proc/mounts"

MOUNT_TIMEOUT        = 3.0
UMOUNT_TIMEOUT       = 3.0
FUSERKILL_TIMEOUT    = 3.0
DRBD_SETROLE_TIMEOUT = 5.0

resources = list()

def execute(cmd, timeout=10):
	pipe  = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	res   = pipe.poll()
	start = time.time()

	while res == None and time.time() - start < timeout:
		res = pipe.poll()
		time.sleep(0.1)

	if res == None:
		pipe.kill()
		sys.stdout.write("Killed command '%s'" % (cmd))
		res = 1

	return res, pipe.stdout.readlines()

class Resource():
	def __init__(self, name, device):
		self.name   = name
		self.device = device
		self.minor  = self.getMinor()

		self.connection_status  = False
		self.role_local         = False
		self.role_peer          = False
		self.diskstatus_local   = False
		self.diskstatus_peer    = False
		self.replation_protocol = False
		self.io_flags           = False

		self.readStatus()

	def getMinor(self):
		match = RE_DRBD_MINOR.match(self.device)

		if match:
			return int(match.group(1))

		return 99

	# Sample from /proc/drbd
	# 2: cs:Connected ro:Secondary/Secondary ds:UpToDate/UpToDate C r-----
	#    ns:0 nr:0 dw:0 dr:0 al:0 bm:0 lo:0 pe:0 ua:0 ap:0 ep:1 wo:f oos:0
	def readStatus(self):
		if not os.path.isfile(PROC_DRBD):
			log.fatal("failed to open %s", PROC_DRBD)
			return False

		for line in open(PROC_DRBD).readlines():
			match1 = RE_DRBD_PROC_LINE1.match(line)

			if match1:
				# we have reached matched first status line

				if self.minor == int(match1.group(1)):
					# we have reached our device status line
					self.connection_status  = match1.group(2).lower()
					self.role_local         = match1.group(3).lower()
					self.role_peer          = match1.group(4).lower()
					self.diskstatus_local   = match1.group(5).lower()
					self.diskstatus_peer    = match1.group(6).lower()
					self.replation_protocol = match1.group(7).lower()
					self.io_flags           = match1.group(8).lower()

					return True

		return False

	def getConnectionStatus(self):
		return self.readStatus() and self.connection_status

	def getLocalRole(self):
		return self.readStatus() and self.role_local

	def getPeerRole(self):
		return self.readStatus() and self.role_peer

	def getLocalDiskStatus(self):
		return self.readStatus() and self.diskstatus_local

	def getPeerDiskStatus(self):
		return self.readStatus() and self.diskstatus_peer

	def isMounted(self):
		for line in open(PROC_MOUNTS).readlines():
			if line.startswith("%s " % (self.device)):
				return True

		return False

	def isInUse(self):
		res, output = execute("fuser -v -m %s" % (self.device))
		in_use      = False

		for line in output:
			if RE_FUSER.match(line):
				in_use = True

		return in_use

	def mount(self):
		if self.isMounted():
			return True

		res, output = execute("mount %s" % (self.device))
		start       = time.time()

		if res:
			# fail to mount
			return False

		while not self.isMounted() and time.time() - start <= MOUNT_TIMEOUT:
			time.sleep(0.1)

		if time.time() - start > MOUNT_TIMEOUT:
			# timeout while waiting for device to appear in /proc/mounts
			return False

		return True

	def umount(self):
		if not self.isMounted():
			return True

		if self.isInUse():
			start = time.time()

			while self.isInUse() and time.time() - start <= FUSERKILL_TIMEOUT:
				execute("fuser -k -m %s -TERM" % (self.device))
				time.sleep(0.1)

			if time.time() - start > FUSERKILL_TIMEOUT:
				execute("fuser -k -m %s -KILL" % (self.device))

		res, output = execute("umount %s" % (self.device))
		start       = time.time()

		if res:
			# fail to unmount
			return False

		while self.isMounted() and time.time() - start <= UMOUNT_TIMEOUT:
			time.sleep(0.1)

		if time.time() - start > UMOUNT_TIMEOUT:
			# timeout while waiting for device to disapear from /proc/mounts
			return False

		return True

	def setRole(self, role):
		if role not in [ "primary", "secondary" ]:
			return False

		if not self.getLocalRole():
			return False

		elif self.getLocalRole() == role:
			return True

		res, output = execute("drbdadm %s %s" % (role, self.name))
		start       = time.time()

		if res:
			# fail to set role
			return False

		while self.getLocalRole() != role and time.time() - start <= DRBD_SETROLE_TIMEOUT:
			time.sleep(0.1)

		if time.time() - start > DRBD_SETROLE_TIMEOUT:
			# timeout while waiting for resource role to change
			return False

		return True

	def setPrimary(self):
		if not self.setRole("primary"):
			return False

		return self.mount()

	def setSecondary(self):
		if not self.umount():
			return False

		return self.setRole("secondary")

def load():
	global resources

	for res in glob.glob("%s/*.res" % (config.drbd_dir)):
		resource = False
		device   = False

		for line in open(res).readlines():
			matchresource = RE_DRBD_RESOURCE.match(line)
			matchdevice   = RE_DRBD_DEVICE.match(line)

			if matchresource: resource = matchresource.group(1)
			if matchdevice:   device   = matchdevice.group(1)

			if resource and device and resource in config.drbd_resources:
				resources.append(Resource(resource, device))
				resource = False
				device   = False

def show():
	global resources

	print "DRBD resources :"
	for resource in resources:
		print "    %s from %-10s (current local role is %s)" % (resource.device, resource.name, resource.getLocalRole())
	print

