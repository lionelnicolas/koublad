#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import os

from distutils.core import setup

def create_file(filepath, content, mode=0755):
    dirpath = os.path.dirname(filepath)

    if dirpath != '' and not os.path.isdir(dirpath):
        os.makedirs(dirpath, mode=0755)

    fd = open(filepath, "w")
    fd.write(content)
    fd.close()

    os.chmod(filepath, mode)

POST_INSTALL = \
    "#!/bin/sh\n" \
    "\n" \
    "ln -sf /usr/share/failover-manager/failover-manager.py /usr/sbin/failover-manager\n"

PRE_UNINSTALL = \
    "#!/bin/sh\n" \
    "\n" \
    "rm -f /usr/sbin/failover-manager\n"

STDEB_CFG = \
    "[DEFAULT]\n" \
    "Package: %s\n" % (_vars.PACKAGE)

setup(
    name               = "failover-manager",
    version            = "0.1.0",
    description        = "A failover handler for master-slave clusters",
    long_description   = "Failover Manager is a small daemon which runs on two different servers (nodes) to handle high\n"
                         "availability on a master/slave cluster, and performs failover actions if needed.\n"
                         "\n"
                         "Each instance monitors UDP pings to detect that the other node is alive. If it's not the case,\n"
                         "the instance can ping a third party to check its connectivity (sort of a dummy quorum-based\n"
                         "implementation).",
    author             = "Lionel Nicolas",
    author_email       = "lionel.nicolas@nividic.org",
    url                = "https://github.com/lionelnicolas/failover-manager",
    license            = "GPLv3",
    data_files         = [
        ( "/etc",                                         [ "failover.conf" ]),
        ( "/usr/share/failover-manager",                  glob.glob("./mod_*.py") + [ "config.py", "failover-manager.py"] ),
        ( "/usr/share/failover-manager/plugins/quorum",   glob.glob("./plugins/quorum/*.py")),
        ( "/usr/share/failover-manager/plugins/switcher", glob.glob("./plugins/switcher/*.py")),
    ],
    options = {
        'bdist_rpm': {
            'post_install':  create_file("post_install",  POST_INSTALL,  0755),
            'pre_uninstall': create_file("pre_uninstall", PRE_UNINSTALL, 0755),
        },
        'bdist_deb_fake': { # this options is never used by distutils/stdeb, calling create_file() will just create needed files in the right place
            'post_install':  create_file("debian/postinst", POST_INSTALL,  0755),
            'pre_uninstall': create_file("debian/prerm",    PRE_UNINSTALL, 0755),
            'stdeb_config':  create_file("stdeb.cfg",       STDEB_CFG,     0644),
        },
    },
)

