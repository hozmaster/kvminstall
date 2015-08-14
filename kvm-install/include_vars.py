#!/usr/bin/env python
"""Common variables for kvm-install, kvm-uninsall, and kvm-reset"""

import os

__author__ = 'Jason Callaway'
__email__ = 'jason@jasoncallaway.com'
__license__ = 'Apache License Version 2.0'
__version__ = '0.1'
__status__ = 'alpha'

class KVMInstallVars(object):

    def __init__(self):
        # TODO: add support for other platforms
        self.SUPPORTED_PLATFORMS = ['rhel', 'centos', 'fedora']
        self.CONFIG_PATH = os.path.expanduser('~') + \
                           '/.config/kvm-install/config.yaml'