#!/usr/bin/env python
# -*- coding: utf-8 -*-

import atexit
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
import mod_monitor

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

def signal_handler(signum, frame):
    global loop
    global monitor

    loop = False

    if signum in [ signal.SIGINT, signal.SIGTERM ]:
        monitor.status.Shutdown()
        monitor.stop()

def create_pidfile():
    # create/write pidfile

    log.info("Writing PID file ...")

    try:
        fd = open(config.options.pid_file, "w")
        fd.write("%d" % (os.getpid()))
        fd.close()
    except Exception, e:
        log.fatal("Failed to write PID file: %s" % (str(e)))

    # register pidfile deletion
    atexit.register(remove_pidfile)

def remove_pidfile():
    log.info("Removing PID file ...")
    os.remove(config.options.pid_file)

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

    create_pidfile()

    config.show()
    mod_plugins.show()
    mod_drbd.show()

    mod_plugins.loadQuorum(config.quorum_plugin)
    mod_plugins.loadSwitcher(config.switcher_plugin)
    mod_plugins.loadNotifier(config.notifier_plugin)

    print

    signal.signal(signal.SIGINT,  signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    listener = mod_listener.Listener()
    pinger   = mod_pinger.Pinger()
    monitor  = mod_monitor.Monitor(listener, pinger)

    listener.setMonitor(monitor)
    pinger.setMonitor(monitor)

    monitor.start()

    while loop:
        time.sleep(.1)

if __name__ == '__main__':
    main()

