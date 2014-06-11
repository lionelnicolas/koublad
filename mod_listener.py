import SocketServer
import threading

import config

import logger
log = logger.initlog(__name__)

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

        self.server  = UdpPingServer()
        self.monitor = False

    def run(self):
        log.info("Starting listener")

        self.server.serve_forever()

        log.info("Listener stopped")

    def stop(self):
        log.info("Stopping listener")

        self.server.shutdown()

    def setMonitor(self, monitor):
        self.monitor = monitor

