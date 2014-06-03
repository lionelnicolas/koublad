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

import config
import plugins

STATES = [
	"starting",
	"waiting",
	"failback",
	"failover",
	"enabling",
	"master",
	"disabling",
	"slave",
	"unknown",
]

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

class ClientHandler(SocketServer.BaseRequestHandler):
	def handle(self):
		self.data, self.sock = self.request

		self.server.last_udp_data = self.data
		self.server.got_remote_ping.set()

class UdpPingServer(SocketServer.UDPServer):
	def __init__(self):
		SocketServer.UDPServer.__init__(self, ("0.0.0.0", config.port), ClientHandler)

		self.last_udp_data       = "unknown"
		self.got_remote_ping     = threading.Event()
		self.allow_reuse_address = True

		self.got_remote_ping.clear()

class Listener(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)

		self.server = UdpPingServer()

	def run(self):
		log("Starting listener")

		self.server.serve_forever()

		log("Listener stopped")

	def stop(self):
		log("Stopping listener")

		self.server.shutdown()

class Pinger(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)

		self.loop   = True
		self.sock   = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.wakeup = threading.Event()

	def run(self):
		log("Starting pinger")

		global monitor

		while self.loop:
			self.send(monitor.status.state)
			self.wakeup.wait(config.interval)
			self.wakeup.clear()

		log("Pinger stopped")

	def stop(self):
		log("Stopping pinger")

		self.loop = False

	def wake(self):
		self.wakeup.set()

	def send(self, data):
		self.sock.sendto(data, (config.peer_host, config.peer_port))

class Monitor(threading.Thread):
	def __init__(self, listener, pinger):
		threading.Thread.__init__(self)

		self.listener = listener
		self.pinger   = pinger
		self.loop     = True
		self.status   = Status(self)

	def run(self):
		log("Starting monitor")

		self.listener.start()
		self.pinger.start()

		self.status.SetDead()
		# TODO: get current "real" state (DRBD, services ???)

		while self.loop:
			if self.listener.server.got_remote_ping.wait(config.timeout):
				self.listener.server.got_remote_ping.clear()

				if not self.loop:
					continue

				self.status.SetPeerState(self.listener.server.last_udp_data)

				if self.status.state == "master":
					if config.role == "master":
						if self.status.pstate != "master":
							self.status.SetState("master")

					else:
						if   self.status.peer in [ "starting", "waiting", "disabling", "slave", "unknown" ]:
							log("We are currently master, the legitimate master is slave or not ready")

						elif self.status.peer in [ "master" ]:
							log("Oops, we have a split brain")

						elif self.status.peer in [ "enabling", "failback", "failover" ]:
							log("Peer is transitioning to master")
							self.status.Disable()

						else:
							log("Oops, peer state is wrong")

				elif self.status.state in [ "slave", "enabling", "failback", "failover" ]:
					if config.role == "master":
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
						self.status.SetState("master")

				elif self.status.state == "slave":
					if config.role == "master":
						self.status.NotifyMasterTransition()

					elif plugins.quorum:
						if plugins.quorum.get():
							log("We have enough quorum to failover to us")
							self.status.NotifyMasterTransition()
						else:
							log("We have not enough quorum to require failover to us")

					elif not plugins.quorum:
						log("No quorum plugin defined, require failover to us")
						self.status.NotifyMasterTransition()

				elif self.status.state in [ "failback", "failover" ]:
					self.status.Enable()

				elif self.status.state in [ "starting", "waiting", "disabling", "enabling", "unknown" ]:
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
	def __init__(self, monitor):
		self.monitor = monitor
		self.pstate  = "unknown"
		self.state   = "starting"
		self.peer    = False

	def Show(self):
		sys.stdout.write("state:%-9s peer:%-9s -- " % (self.state, self.peer))

	def SetState(self, newstate, immediate=False):
		self.pstate = self.state
		self.state  = newstate

		self.monitor.pinger.wake()

		# Instantly send the new state to peer, without waiting for pinger mainloop
		if immediate:
			self.monitor.pinger.send(newstate)

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
		time.sleep(config.initdead)
		self.SetState("slave")

		log("We are now slave")

	def NotifyMasterTransition(self):
		log("Notifying that we are transitioning to master")

		if config.role == "master":
			self.SetState("failback", immediate=True)
			time.sleep(0.5)

		elif config.role == "slave":
			self.SetState("failover", immediate=True)
			time.sleep(0.5)

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

	config.show()
	plugins.show()

	plugins.loadQuorum(config.quorum_plugin)
	plugins.loadSwitcher(config.switcher_plugin)
	print

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)

	listener = Listener()
	pinger   = Pinger()
	monitor  = Monitor(listener, pinger)

	monitor.start()

	while loop:
		time.sleep(.1)

if __name__ == '__main__':
	main()

