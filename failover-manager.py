#!/usr/bin/env python

import glob
import os
import random
import re
import signal
import socket
import SocketServer
import sys
import threading
import time

CONFIG   = "/etc/failover.conf"
DRBD_DIR = "/etc/drbd.d"

STATES = [
	"starting",
	"waiting",
	"failback",
	"enabling",
	"master",
	"disabling",
	"slave",
	"unknown",
]

RE_CONFIG_LINE   = re.compile("^[\ \t]*([a-zA-Z0-9_]+)[\ \t]*=[\ \t]*([^#\n\r]+).*$")
RE_CONFIG_PEER   = re.compile("^([^:]+):([0-9]+)$")
RE_DRBD_RESOURCE = re.compile("^[\ \t]*resource[\ \t]+([a-z0-9]+).*$")
RE_DRBD_DEVICE   = re.compile("^[\ \t]*device[\ \t]+([a-z0-9/]+).*$")

loop     = True
monitor  = False

def fail(text, code=1):
	sys.stderr.write("%s\n" % text)
	sys.stderr.flush()
	sys.exit(code)

def error(text):
	sys.stderr.write("%s\n" % text)
	sys.stderr.flush()

def log(text):
	global monitor

	monitor.status.Show()

	sys.stdout.write("%s\n" % text)
	sys.stdout.flush()

class Config():
	def __init__(self):
		self.configfile = CONFIG
		self.port       = False
		self.role       = False
		self.initdead   = False
		self.peer_host  = False
		self.peer_port  = False
		self.timeout    = False
		self.interval   = False
		self.services   = list()
		self.drbd_res   = list()
		self.drbd       = Drbd()

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

				elif name == "role":
					if value not in [ "master", "slave" ]:
						fail("Bad value for 'role', must be 'master' or 'slave'")

					self.role = value

				elif name == "initdead":
					try:
						self.initdead  = float(value)

						if self.initdead < 0.1:
							fail("Value 'initdead' must be at least 0.1 seconds")

					except:
						fail("Value 'initdead' must be a float")

				elif name == "peer":
					match = RE_CONFIG_PEER.match(value)

					if match:
						self.peer_host = match.group(1)
						self.peer_port = int(match.group(2))
					else:
						fail("Bad format for 'peer', must be 'HOST:PORT'")

				elif name == "timeout":
					try:
						self.timeout  = float(value)
						self.interval = float(self.timeout / 2.0)

						if self.timeout < 0.1:
							fail("Value 'timeout' must be at least 0.1 seconds")

					except:
						fail("Value 'timeout' must be a float")

				elif name == "services":
					self.services = self.SplitIntoList(value)

					for service in self.services:
						if not os.path.isfile("/etc/init.d/%s" % (service)):
							fail("Service '%s' does not exist" % (service))

				elif name == "drbd_resources":
					self.drbd_res = self.SplitIntoList(value)

					for resource in self.drbd_res:
						if resource not in self.drbd.resources.keys():
							fail("DRBD resource '%s' does not exist" % (resource))

				else:
					fail("Bad configuration value '%s'" % (name))

		if self.port and self.role and self.initdead and self.peer_host and self.peer_port and self.timeout and self.interval:
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
		print "%-12s: %s"   % ("configfile", self.configfile)
		print "%-12s: %d"   % ("port", self.port)
		print "%-12s: %s"   % ("role", self.role)
		print "%-12s: %.1f" % ("initdead", self.initdead)
		print "%-12s: %s"   % ("peer_host", self.peer_host)
		print "%-12s: %d"   % ("peer_port", self.peer_port)
		print "%-12s: %.1f" % ("timeout", self.timeout)
		print "%-12s: %.1f" % ("interval", self.interval)
		print "%-12s: %s"   % ("services", self.services)
		print "%-12s: %s"   % ("drbd_res", self.drbd_res)
		print

class Drbd:
	def __init__(self):
		self.drbd_dir  = DRBD_DIR
		self.resources = dict()

		if len(sys.argv) > 2:
			self.drbd_dir = sys.argv[2]

		self.GetResources()

	def GetResources(self):
		for res in glob.glob("%s/*.res" % (self.drbd_dir)):
			resource = False
			device   = False

			for line in open(res).readlines():
				matchresource = RE_DRBD_RESOURCE.match(line)
				matchdevice   = RE_DRBD_DEVICE.match(line)

				if matchresource: resource = matchresource.group(1)
				if matchdevice:   device   = matchdevice.group(1)

			if resource and device:
				self.resources[resource] = device

class ClientHandler(SocketServer.BaseRequestHandler):
	def handle(self):
		self.data, self.sock = self.request

		self.server.last_udp_data = self.data
		self.server.got_remote_ping.set()

class UdpPingServer(SocketServer.UDPServer):
	def __init__(self, config):
		SocketServer.UDPServer.__init__(self, ("0.0.0.0", config.port), ClientHandler)

		self.config              = config
		self.last_udp_data       = "unknown"
		self.got_remote_ping     = threading.Event()
		self.allow_reuse_address = True

		self.got_remote_ping.clear()

class Listener(threading.Thread):
	def __init__(self, config):
		threading.Thread.__init__(self)

		self.config = config
		self.server = UdpPingServer(self.config)

	def run(self):
		log("Starting listener")

		self.server.serve_forever()

		log("Listener stopped")

	def stop(self):
		log("Stopping listener")

		self.server.shutdown()

class Pinger(threading.Thread):
	def __init__(self, config):
		threading.Thread.__init__(self)

		self.config = config
		self.loop   = True
		self.sock   = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.wakeup = threading.Event()

	def run(self):
		log("Starting pinger")

		global monitor

		while self.loop:
			self.send(monitor.status.state)
			self.wakeup.wait(self.config.interval)
			self.wakeup.clear()

		log("Pinger stopped")

	def stop(self):
		log("Stopping pinger")

		self.loop = False

	def wake(self):
		self.wakeup.set()

	def send(self, data):
		self.sock.sendto(data, (self.config.peer_host, self.config.peer_port))

class Monitor(threading.Thread):
	def __init__(self, config, listener, pinger):
		threading.Thread.__init__(self)

		self.config   = config
		self.listener = listener
		self.pinger   = pinger
		self.loop     = True
		self.status   = Status(self, self.config)

	def run(self):
		log("Starting monitor")

		self.listener.start()
		self.pinger.start()

		self.status.SetDead()
		# TODO: get current "real" state (DRBD, services ???)

		while self.loop:
			if self.listener.server.got_remote_ping.wait(self.config.timeout):
				self.listener.server.got_remote_ping.clear()

				if not self.loop:
					continue

				self.status.SetPeerState(self.listener.server.last_udp_data)

				if self.status.state == "master":
					if self.listener.server.config.role == "master":
						if self.status.pstate != "master":
							log("We are already master, so do nothing ...")
							self.status.SetState("master")

					else:
						if   self.status.peer in [ "starting", "waiting", "disabling", "slave", "unknown" ]:
							log("We are currently master, the legitimate master is slave or not ready")

						elif self.status.peer in [ "master" ]:
							log("Oops, we have a split brain")

						elif self.status.peer in [ "enabling", "failback" ]:
							log("Peer is transitioning to master")
							self.status.Disable()

						else:
							log("Oops, peer state is wrong")

				elif self.status.state in [ "slave", "enabling", "failback" ]:
					if self.listener.server.config.role == "master":
						if   self.status.peer in [ "starting", "waiting", "slave", "unknown" ]:
							log("We are supposed to be master, peer is slave or not ready")
							self.status.Enable()

						elif self.status.peer in [ "disabling" ]:
							log("We are supposed to be master, peer is transitioning to slave, wait for him to shutdown")

						elif self.status.peer in [ "enabling" ]:
							log("We are supposed to be master, peer is transitioning to master, wait for him to come up")

						elif self.status.peer in [ "master" ]:
							log("We are supposed to be master, peer is currently master, tell him to transition to slave")
							self.status.NotifyMasterTransition()

						else:
							log("Oops, peer state is wrong")

					else:
						if self.status.pstate != "slave":
							log("We are already slave, so do nothing ...")
							self.status.SetState("slave")

				elif self.status.state in [ "starting", "waiting", "disabling", "unknown" ]:
					log("We are transitioning, wait for us to finish")

				elif self.status.state in [ "shutdown" ]:
					log("We are shutting down ...")

				else:
					log("Oops, our state is wrong")

			else:
				if not self.loop:
					continue

				self.status.SetPeerState("unknown")

				if   self.status.state == "master":
					if self.status.pstate != "master":
						log("We are already master, so do nothing ...")
						self.status.SetState("master")

				elif self.status.state == "slave":
					log("Peer is down")
					self.status.Enable()

				elif self.status.state in [ "starting", "waiting", "disabling", "enabling", "unknown", "failback" ]:
					log("We are transitioning, wait for us to finish")

				elif self.status.state in [ "shutdown" ]:
					log("We are shutting down ...")

				else:
					log("Oops, our state is wrong")

		self.listener.stop()
		self.pinger.stop()

		log("Monitor stopped")

	def stop(self):
		log("Stopping monitor")

		self.loop = False

class Status():
	def __init__(self, monitor, config):
		self.monitor = monitor
		self.pstate  = "unknown"
		self.state   = "starting"
		self.peer    = False
		self.config  = config

	def Show(self):
		sys.stdout.write("state:%-9s peer:%-9s -- " % (self.state, self.peer))

	def SetState(self, newstate):
		self.pstate = self.state
		self.state  = newstate

		self.monitor.pinger.wake()

	def SetPeerState(self, newstate):
		oldstate  = self.peer
		self.peer = newstate

		if oldstate and newstate != oldstate:
			if   newstate == "unknown":
				log("Peer is down")

			elif newstate == "shutdown":
				log("Peer is shutting down")

			else:
				log("Peer state is now '%s'" % (newstate))


	def SetDead(self):
		log("Waiting for a while before handling events")

		self.SetState("waiting")
		time.sleep(self.config.initdead)
		self.SetState("slave")

	def NotifyMasterTransition(self):
		log("Notifying that we are transitioning to master")

		if self.config.role == "master":
			self.SetState("failback")
			time.sleep(0.5)

		self.SetState("enabling")

	def Enable(self):
		if self.state == "shutdown":
			return

		if self.state != "enabling":
			self.SetState("enabling")

		log("Transitioning to master")

		time.sleep(5 * random.random()) # fake processing time
		self.SetState("master")

		log("We are now master")

	def Disable(self):
		if self.state == "slave":
			return

		log("Transitioning to slave")

		self.SetState("disabling")
		time.sleep(5 * random.random()) # fake processing time
		self.SetState("slave")

		log("We are now slave")

	def Shutdown(self):
		log("Initiating shutdown ...")

		self.monitor.pinger.send("shutdown")
		self.Disable()

def signal_handler(signum, frame):
	global loop
	global monitor

	loop = False

	if signum in [ signal.SIGINT, signal.SIGTERM ]:
		monitor.status.Shutdown()
		monitor.stop()

def main():
	global loop
	global monitor

	config = Config()
	config.Show()

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)

	listener = Listener(config)
	pinger   = Pinger(config)
	monitor  = Monitor(config, listener, pinger)

	monitor.start()

	while loop:
		time.sleep(.1)

if __name__ == '__main__':
	main()

