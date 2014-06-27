#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import logging.handlers
import signal
import os
import re
import sys
import config


log_levels = { 'debug':logging.DEBUG,
              'info':logging.INFO,
              'warning':logging.WARNING,
              'critical': logging.CRITICAL }

syslog_facilities = { 'auth':logging.handlers.SysLogHandler.LOG_AUTH,
                      'authpriv':logging.handlers.SysLogHandler.LOG_AUTHPRIV,
                      'cron':logging.handlers.SysLogHandler.LOG_CRON,
                      'daemon':logging.handlers.SysLogHandler.LOG_DAEMON,
                      'ftp':logging.handlers.SysLogHandler.LOG_FTP,
                      'kern':logging.handlers.SysLogHandler.LOG_KERN,
                      'lpr':logging.handlers.SysLogHandler.LOG_LPR,
                      'mail':logging.handlers.SysLogHandler.LOG_MAIL,
                      'news':logging.handlers.SysLogHandler.LOG_NEWS,
                      'syslog':logging.handlers.SysLogHandler.LOG_SYSLOG,
                      'user':logging.handlers.SysLogHandler.LOG_USER,
                      'uucp':logging.handlers.SysLogHandler.LOG_UUCP,
                      'local0':logging.handlers.SysLogHandler.LOG_LOCAL0,
                      'local1':logging.handlers.SysLogHandler.LOG_LOCAL1,
                      'local2':logging.handlers.SysLogHandler.LOG_LOCAL2,
                      'local3':logging.handlers.SysLogHandler.LOG_LOCAL3,
                      'local4':logging.handlers.SysLogHandler.LOG_LOCAL4,
                      'local5':logging.handlers.SysLogHandler.LOG_LOCAL5,
                      'local6':logging.handlers.SysLogHandler.LOG_LOCAL6,
                      'local7':logging.handlers.SysLogHandler.LOG_LOCAL7 }


def critical_with_shutdown(self, msg, *args, **kwargs):
    if logging.CRITICAL >= self.getEffectiveLevel():
        apply(self._log, (logging.CRITICAL, msg, args), kwargs)

    # we've got a critical error, shutdown ...
    os.kill(os.getpid(), signal.SIGTERM)

logging.Logger.critical = critical_with_shutdown
logging.Logger.fatal    = logging.Logger.critical

def initlog(name):
    name = re.sub("^mod_",      "", name)
    name = re.sub("^quorum_",   "", name)
    name = re.sub("^switcher_", "", name)
    name = re.sub("^notifier_", "", name)

    return logging.getLogger(name)

logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.CRITICAL)
stream_formatter = logging.Formatter("%(asctime)s.%(msecs)03d - %(name)-8s - %(levelname)-8s - %(message)s", datefmt="%H:%M:%S")
stream_handler.setFormatter(stream_formatter)
logger.addHandler(stream_handler)


def configMainLogger():
    logger = logging.getLogger()

    smaller_lvl=logging.CRITICAL
    for i in (log_levels[config.syslog_level], log_levels[config.filelog_level], log_levels[config.verbosity]):
        if i < smaller_lvl: smaller_lvl=i
    logger.setLevel(smaller_lvl)

    file_formatter   = logging.Formatter("%(asctime)s - %(name)-8s - %(levelname)-8s - %(message)s")
    stream_formatter = logging.Formatter("%(asctime)s.%(msecs)03d - %(name)-8s - %(levelname)-8s - %(message)s", datefmt="%H:%M:%S")
    syslog_formatter = logging.Formatter("failover: %(name)-8s - %(levelname)-8s - %(message)s")

    file_handler = logging.FileHandler(config.filelog_filename)
    file_handler.setLevel(log_levels[config.filelog_level])
    file_handler.setFormatter(file_formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_levels[config.verbosity])
    stream_handler.setFormatter(stream_formatter)

    syslog_handler = logging.handlers.SysLogHandler(address="/dev/log", facility=syslog_facilities[config.syslog_facility])
    syslog_handler.setLevel(log_levels[config.syslog_level])
    syslog_handler.setFormatter(syslog_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.addHandler(syslog_handler)

