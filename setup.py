#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import os
import _vars

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
    "ln -sf /usr/share/koublad/koublad.py /usr/sbin/koublad\n"

PRE_UNINSTALL = \
    "#!/bin/sh\n" \
    "\n" \
    "rm -f /usr/sbin/koublad\n" \
    "\n" \
    "# on Debian family distributions, we need to remove *.pyc and *.pyo files\n" \
    "if [ -f /etc/debian_version ]; then\n" \
    "\tfind /usr/share/koublad -type f -name '*.py[co]' -delete\n" \
    "fi\n"

STDEB_CFG = \
    "[DEFAULT]\n" \
    "Package: %s\n" % (_vars.PACKAGE)

setup(
    name               = _vars.PACKAGE,
    version            = _vars.VERSION,
    description        = "A failover handler for master-slave clusters",
    long_description   = "Koublad is a small daemon which runs on two different servers (nodes) to handle high\n"
                         "availability on a master/slave cluster, and performs failover actions if needed.\n"
                         "\n"
                         "Each instance monitors UDP pings to detect that the other node is alive. If it's not the case,\n"
                         "the instance can ping a third party to check its connectivity (sort of a dummy quorum-based\n"
                         "implementation).",
    author             = "Lionel Nicolas",
    author_email       = "lionel.nicolas@nividic.org",
    url                = "https://github.com/lionelnicolas/koublad",
    license            = "GPLv3",
    data_files         = [
        ( "/etc",                                [ "koublad.conf" ]),
        ( "/usr/share/koublad",                  glob.glob("./mod_*.py") + [ "config.py", "koublad.py", "_vars.py" ] ),
        ( "/usr/share/koublad/plugins/quorum",   glob.glob("./plugins/quorum/*.py")),
        ( "/usr/share/koublad/plugins/switcher", glob.glob("./plugins/switcher/*.py")),
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

