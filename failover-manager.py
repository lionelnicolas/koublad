#!/usr/bin/env python

import os
import re
import signal
import socket
import SocketServer
import sys
import threading
import time

CONFIG         = "/etc/failover.conf"
RE_CONFIG_LINE = re.compile("^[\ \t]*([a-zA-Z0-9]+)[\ \t]*=[\ \t]*([^#\n\r]+).*$")
RE_CONFIG_PEER = re.compile("^([^:]+):([0-9]+)$")

loop     = True
listener = False
pinger   = False

def fail(text, code=1):
	sys.stderr.write("%s\n" % text)
	sys.stderr.flush()
	sys.exit(code)

def error(text):
	sys.stderr.write("%s\n" % text)
	sys.stderr.flush()

def log(text):
	sys.stdout.write("%s\n" % text)
	sys.stdout.flush()

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

class ClientHandler(SocketServer.BaseRequestHandler):
	def handle(self):
		self.data, self.sock = self.request
		print "Received '%s' from %s" % (self.data, self.client_address[0])

		# self.server.config

class UdpPingServer(SocketServer.UDPServer):
	def __init__(self, config):
		SocketServer.UDPServer.__init__(self, ("0.0.0.0", config.port), ClientHandler)

		self.config              = config
		self.timeout             = self.config.timeout
		self.allow_reuse_address = True

	def handle_timeout(self):
		print "No data received in the last %d seconds" % (self.timeout)

class Listener(threading.Thread):
	def __init__(self, config):
		threading.Thread.__init__(self)

		self.config = config
		self.loop   = True
		self.server = UdpPingServer(self.config)

	def run(self):
		log("Starting listener")

		while self.loop:
			self.server.handle_request()

		log("Listener stopped")

	def stop(self):
		log("Stopping listener")

		self.loop = False

class Pinger(threading.Thread):
	def __init__(self, config):
		threading.Thread.__init__(self)

		self.config = config
		self.loop   = True
		self.sock   = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	def run(self):
		log("Starting pinger")

		while self.loop:
			self.sock.sendto("time:%f" % (time.time().real), (self.config.peer_host, self.config.peer_port))
			time.sleep(self.config.interval)

		log("Pinger stopped")

	def stop(self):
		log("Stopping pinger")

		self.loop = False

def signal_handler(signum, frame):
	global listener
	global loop
	global pinger

	loop = False

	if signum == signal.SIGINT:
		listener.stop()
		pinger.stop()

def main():
	global listener
	global loop
	global pinger

	config = Config()
	config.Show()

	signal.signal(signal.SIGINT, signal_handler)

	listener = Listener(config)
	pinger   = Pinger(config)

	listener.start()
	pinger.start()

	while loop:
		time.sleep(.1)

if __name__ == '__main__':
	main()

