#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import signal
import sys
import threading
import time

import config
import mod_drbd
import mod_listener
import mod_pinger
import mod_plugins
import mod_services

import mod_logger
log = mod_logger.initlog("main")

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

class Monitor(threading.Thread):
    def __init__(self, listener, pinger):
        threading.Thread.__init__(self)

        self.listener = listener
        self.pinger   = pinger
        self.loop     = True
        self.status   = Status(self)

        self.quorum_ok = 0

    def run(self):
        log.info("Starting monitor")

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
                            log.info("We are currently master, the legitimate master is slave or not ready")

                        elif self.status.peer in [ "master" ]:
                            log.info("Oops, we have a split brain")
                            log.info("Disabling everything")
                            self.status.Disable()

                        elif self.status.peer in [ "enabling", "failback", "failover" ]:
                            log.info("Peer is transitioning to master")
                            self.status.Disable()

                        else:
                            log.info("Oops, peer state is wrong")

                elif self.status.state in [ "slave", "enabling", "failback", "failover" ]:
                    if config.role == "master":
                        if   self.status.peer in [ "starting", "waiting", "slave", "unknown" ]:
                            log.info("We are supposed to be master, peer is slave or not ready")
                            self.status.Enable()

                        elif self.status.peer in [ "disabling" ]:
                            log.info("We are supposed to be master, peer is transitioning to slave, wait for him to shutdown")

                        elif self.status.peer in [ "enabling" ]:
                            log.info("We are supposed to be master, peer is transitioning to master, wait for him to come up")

                        elif self.status.peer in [ "master" ]:
                            drbd_dunknown_resources     = list()
                            drbd_inconsistent_resources = list()
                            drbd_splitbrain_resources   = list()

                            for resource in mod_drbd.resources:
                                log.info("%s: %s/%s" % (resource.name, resource.getLocalDiskStatus(), resource.getPeerDiskStatus()))
                                if resource.getLocalDiskStatus() == "uptodate" and resource.getPeerDiskStatus() == "uptodate":
                                    # this resource is ok for failback
                                    pass
                                elif resource.getPeerDiskStatus() == "uptodate":
                                    drbd_inconsistent_resources.append("%s=%s" % (resource.name, resource.getConnectionStatus()))
                                elif resource.getPeerDiskStatus() == "dunknown":
                                    drbd_dunknown_resources.append("%s=%s" % (resource.name, resource.getConnectionStatus()))
                                else:
                                    drbd_splitbrain_resources.append("%s=%s" % (resource.name, resource.getConnectionStatus()))

                            if len(drbd_dunknown_resources):
                                log.info("We are supposed to be master, but DRBD resources have not synced their state : %s" % (drbd_dunknown_resources))

                            elif len(drbd_splitbrain_resources):
                                log.info("We are supposed to be master, but DRBD resources have unhandled split brain : %s" % (drbd_splitbrain_resources))
                                self.status.Shutdown()
                                self.stop()

                            elif len(drbd_inconsistent_resources):
                                log.info("We are supposed to be master, but DRBD resources are currently syncing : %s" % (drbd_inconsistent_resources))

                            else:
                                log.info("We are supposed to be master, peer is currently master, tell him to transition to slave")
                                self.status.NotifyMasterTransition()

                        else:
                            log.info("Oops, peer state is wrong")

                    else:
                        if self.status.pstate != "slave":
                            self.status.SetState("slave")

                elif self.status.state in [ "starting", "waiting", "disabling", "unknown" ]:
                    log.info("We are transitioning, wait for us to finish")

                elif self.status.state in [ "shutdown" ]:
                    log.info("We are shutting down ...")

                else:
                    log.info("Oops, our state is wrong")

            else:
                if not self.loop:
                    continue

                self.status.SetPeerState("unknown")

                if   self.status.state == "master":
                    if self.status.pstate != "master":
                        self.status.SetState("master")

                    if mod_plugins.quorum:
                        if mod_plugins.quorum.get():
                            log.info("We have enough quorum to remain master")
                        else:
                            log.info("We have not enough quorum to remain master")
                            self.status.Disable()

                elif self.status.state == "slave":
                    if mod_plugins.quorum:
                        if mod_plugins.quorum.get():
                            if self.quorum_ok < 3:
                                log.info("We have enough quorum to failover to us, but wait for few attempts")
                                self.quorum_ok += 1

                            else:
                                log.info("We have enough quorum to failover to us")
                                self.status.NotifyMasterTransition()
                                self.quorum_ok = 0
                        else:
                            log.info("We have not enough quorum to require failover to us")

                    elif not mod_plugins.quorum:
                        log.info("No quorum plugin defined, require failover to us")
                        self.status.NotifyMasterTransition()

                elif self.status.state in [ "failback", "failover" ]:
                    self.status.Enable()

                elif self.status.state in [ "starting", "waiting", "disabling", "enabling", "unknown" ]:
                    log.info("We are transitioning, wait for us to finish")

                elif self.status.state in [ "shutdown" ]:
                    log.info("We are shutting down ...")

                else:
                    log.info("Oops, our state is wrong")

        self.listener.stop()
        self.pinger.stop()

        log.info("Monitor stopped")

    def stop(self):
        log.info("Stopping monitor")

        self.loop = False

class Status():
    def __init__(self, monitor):
        self.monitor = monitor
        self.pstate  = "unknown"
        self.state   = "starting"
        self.peer    = False

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
                log.info("Peer is down")

            elif newstate == "shutdown":
                log.info("Peer is shutting down")

            else:
                log.info("Peer state is now '%s'" % (newstate))


    def SetDead(self):
        log.info("Waiting for a while before handling events")

        self.SetState("waiting")
        time.sleep(config.initdead)
        self.SetState("slave")

        log.info("We are now slave")

    def NotifyMasterTransition(self):
        log.info("Notifying that we are transitioning to master")

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

        log.info("Transitioning to master")

        # Start DRBD resources
        for resource in mod_drbd.resources:
            log.info("Setting DRBD resource '%s' as primary" % (resource.name))

            if not resource.setPrimary():
                log.fatal("Failed to set DRBD resource role")

        # Start system services
        mod_services.start()

        # Acquire IP address
        if mod_plugins.switcher:
            if mod_plugins.switcher.activate():
                log.info("Failover switch activated")
            else:
                log.error("Failed to activate failover switch")

        self.SetState("master")

        log.info("We are now master")

    def Disable(self):
        if self.state == "slave":
            return

        log.info("Transitioning to slave")

        self.SetState("disabling")

        # Stop system services
        mod_services.stop()

        # Release IP address
        if mod_plugins.switcher:
            if mod_plugins.switcher.deactivate():
                log.info("Failover switch deactivated")
            else:
                log.error("Failed to deactivate failover switch")

        # Stop DRBD resources
        for resource in mod_drbd.resources:
            log.info("Setting DRBD resource '%s' as secondary" % (resource.name))

            if not resource.setSecondary():
                log.fatal("Failed to set DRBD resource role")

        self.SetState("slave")

        log.info("We are now slave")

    def Shutdown(self):
        log.info("Initiating shutdown ...")

        self.monitor.pinger.send("shutdown")
        self.Disable()

def signal_handler(signum, frame):
    global loop
    global monitor

    loop = False

    if signum in [ signal.SIGINT, signal.SIGTERM ]:
        monitor.status.Shutdown()
        monitor.stop()

def daemonize():
    # use double-fork to daemonize
    # see http://www.linuxjedi.co.uk/2014/02/why-use-double-fork-to-daemonize.html

    # do the initial fork
    if os.fork() > 0:
        # exit initial process
        sys.exit(0)

    # set the first fork to be the leader of a new session with no controlling terminals
    os.setsid()
    os.umask(0)

    # do the second fork
    if os.fork() > 0:
        # exit current session leader
        sys.exit(0)

    # current process is now a child of the 'init' process, so we can redirect all I/O descriptors to /dev/null
    fd_stdin  = open("/dev/null", "r")
    fd_stdout = open("/dev/null", "a+")
    fd_stderr = open("/dev/null", "a+")

    os.dup2(fd_stdin.fileno(),  sys.stdin.fileno())
    os.dup2(fd_stdout.fileno(), sys.stdout.fileno())
    os.dup2(fd_stderr.fileno(), sys.stderr.fileno())

def main():
    global loop
    global monitor

    config.parse()
    mod_drbd.load()

    if config.options.daemonize:
        daemonize()

    config.show()
    mod_plugins.show()
    mod_drbd.show()

    mod_plugins.loadQuorum(config.quorum_plugin)
    mod_plugins.loadSwitcher(config.switcher_plugin)
    print

    signal.signal(signal.SIGINT,  signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    listener = mod_listener.Listener()
    pinger   = mod_pinger.Pinger()
    monitor  = Monitor(listener, pinger)

    listener.setMonitor(monitor)
    pinger.setMonitor(monitor)

    monitor.start()

    while loop:
        time.sleep(.1)

if __name__ == '__main__':
    main()

