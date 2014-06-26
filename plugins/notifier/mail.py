#!/usr/bin/env python
# -*- coding: utf-8 -*-

import config
import email.mime.text
import smtplib

import mod_logger
log = mod_logger.initlog(__name__)

DEFAULT_PORT = {
    "none": 25,
    "ssl":  465,
    "tls":  587,
}

config_checks = {
    "server":     { "type": "str",  "default": "localhost",         "check": False },
    "port":       { "type": "int",  "default": False,               "check": False },
    "sender":     { "type": "str",  "default": "koublad@localhost", "check": False },
    "recipients": { "type": "list", "default": False,               "check": "checkNonEmptyList(value)" },
    "encryption": { "type": "str",  "default": "none",              "check": "in ['none', 'ssl', 'tls']" },
    "username":   { "type": "str",  "default": False,               "check": False },
    "password":   { "type": "str",  "default": False,               "check": False },
}

config_optional = [
    "port",
    "username",
    "password",
]

def send_email(subject, body, timeout=5):
    global server
    global port
    global sender
    global recipients
    global encryption
    global username
    global password

    if not port:
        port = DEFAULT_PORT[encryption]

    try:
        if   encryption in [ "none", "tls" ]:
            smtpserver = smtplib.SMTP(server, port, timeout=timeout)
        elif encryption in [ "ssl" ]:
            smtpserver = smtplib.SMTP_SSL(server, port, timeout=timeout)
        else:
            return False

    except Exception, e:
        log.error("Failed to establish connection with SMTP server: %s", e)
        return False

    msg = email.mime.text.MIMEText(body)
    msg.set_charset("utf-8")

    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = ', '.join(recipients)

    # set to 1 if you want SMTP protocol debugging
    smtpserver.set_debuglevel(0)

    try:
        smtpserver.ehlo()

        if encryption == "tls":
            smtpserver.starttls()
            smtpserver.ehlo()

        if username and password:
            smtpserver.login(username, password)

        smtpserver.sendmail(sender, recipients, msg.as_string())
        smtpserver.quit()

    except smtplib.SMTPSenderRefused:
        log.error("Sender address refused")
        return False

    except smtplib.SMTPRecipientsRefused:
        log.error("All recipient addresses refused")
        return False

    except smtplib.SMTPAuthenticationError, e:
        log.error("Failed to authenticate to STMP server: %s", e)
        return False

    except smtplib.SMTPException, e:
        log.error("Unhandled SMTP exception: %s", e)
        return False

    except Exception, e:
        log.error("Unhandled exception: %s", e)
        return False

    return True


### PLUGIN INTERFACE ###

# function called by monitor to notify an activate action
def activate():
    return True

# function called by monitor to notify a deactivate action
def deactivate():
    return True

# function used to send a custom notification
def event(msg):
    return True

### END OF PLUGIN INTERFACE ###


# read configuration
config_dict = config.defaultVariables(config_checks)
config_dict = config.parseConfigurationFile(config.config_file, config_checks, config_optional, config_dict, plugin_name=__name__)

# set variable globaly for easier access
server     = config_dict['server']
port       = config_dict['port']
sender     = config_dict['sender']
recipients = config_dict['recipients']
encryption = config_dict['encryption']
username   = config_dict['username']
password   = config_dict['password']

log.info("Plugin '%s' loaded" % (__name__))
config.show(config_dict)

