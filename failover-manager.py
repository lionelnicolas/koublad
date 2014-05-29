#!/usr/bin/env python

import os
import re
import sys

CONFIG         = "/etc/failover.conf"
RE_CONFIG_LINE = re.compile("^[\ \t]*([a-zA-Z0-9]+)[\ \t]*=[\ \t]*([^#\n\r]+).*$")
RE_CONFIG_PEER = re.compile("^([^:]+):([0-9]+)$")

def fail(text, code=1):
	sys.stderr.write("%s\n" % text)
	sys.stderr.flush()
	sys.exit(code)

class Config():
	def __init__(self):
		self.configfile = CONFIG
		self.port       = False
		self.peer_host  = False
		self.peer_port  = False
		self.timeout    = False
		self.interval   = False
		self.services   = list()
		self.drbd_res   = list()

		if len(sys.argv) > 1:
			self.configfile = sys.argv[1]

		self.Parse()

	def Parse(self):
		if not os.path.isfile(self.configfile):
			fail("Cannot open '%s'" % self.configfile)

		for line in open(self.configfile).readlines():
			match = RE_CONFIG_LINE.match(line)

			if match:
				name   = match.group(1).strip()
				value  = match.group(2).replace('\t', '').replace(' ', '').strip()

				if   name == "port":
					try:
						self.port  = int(value)

					except:
						fail("Value 'port' must be an integer")

				elif   name == "peer":
					match = RE_CONFIG_PEER.match(value)

					if match:
						self.peer_host = match.group(1)
						self.peer_port = int(match.group(2))
					else:
						fail("Bad format for 'peer', must be 'HOST:PORT'")

				elif name == "timeout":
					try:
						self.timeout  = float(value)
						self.interval = float(self.timeout - 0.5)

						if self.timeout < 1:
							fail("Value 'timeout' must be at least 1 second")

					except:
						fail("Value 'timeout' must be a float")

				elif name == "services":
					self.services = self.SplitIntoList(value)

					for service in self.services:
						if not os.path.isfile("/etc/init.d/%s" % (service)):
							fail("Service '%s' does not exist" % (service))

				elif name == "drbd_resources":
					self.drbd_res = self.SplitIntoList(value)

				else:
					fail("Bad configuration value '%s'" % (name))

		if self.port and self.peer_host and self.peer_port and self.timeout and self.interval:
			# configuration is complete
			pass

		else:
			fail("Configuration is incomplete")

	def SplitIntoList(self, value):
		value = value.strip()

		if value.count(',') == 0 and len(value) == 0:
			return list()

		elif value.count(',') == 0:
			return [value]

		else:
			return value.split(',')

	def Show(self):
		print "%-12s: %s" % ("configfile", self.configfile)
		print "%-12s: %d" % ("port", self.port)
		print "%-12s: %s" % ("peer_host", self.peer_host)
		print "%-12s: %d" % ("peer_port", self.peer_port)
		print "%-12s: %d" % ("timeout", self.timeout)
		print "%-12s: %d" % ("interval", self.interval)
		print "%-12s: %s" % ("services", self.services)
		print "%-12s: %s" % ("drbd_res", self.drbd_res)

def main():
	config = Config()
	config.Show()

if __name__ == '__main__':
	main()

