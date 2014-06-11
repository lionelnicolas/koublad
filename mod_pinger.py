import socket
import threading

import config

import logger
log = logger.initlog(__name__)

class Pinger(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

        self.loop    = True
        self.sock    = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.wakeup  = threading.Event()
        self.monitor = False

    def run(self):
        log.info("Starting pinger")

        while self.loop:
            self.send(self.monitor.status.state)
            self.wakeup.wait(config.interval)
            self.wakeup.clear()

        log.info("Pinger stopped")

    def stop(self):
        log.info("Stopping pinger")

        self.loop = False

    def wake(self):
        self.wakeup.set()

    def send(self, data):
        try:
            self.sock.sendto(data, (config.peer_host, config.peer_port))
        except Exception, e:
            log.info("Failed to send data (%s)" % (e))

    def setMonitor(self, monitor):
        self.monitor = monitor

