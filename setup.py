#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob

from distutils.core import setup

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
)

