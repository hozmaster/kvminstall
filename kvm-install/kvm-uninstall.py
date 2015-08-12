#!/usr/bin/env python
"""Python helper for uninstalling VMs installed with virt-install(1)"""

import subprocess
import os
import platform
import argparse
import yaml
import re
import string
import random
import xml.etree.ElementTree as ET

__author__ = 'Jason Callaway'
__email__ = 'jason@jasoncallaway.com'
__license__ = 'Apache License Version 2.0'
__version__ = '0.1'
__status__ = 'alpha'

# TODO: add support for other platforms
SUPPORTED_PLATFORMS = ['rhel', 'centos', 'fedora']
CONFIG_PATH = os.path.expanduser('~') + '/.config/kvm-install/config.yaml'


class KVMUnInstall(object):

    def __init__(self, parsed_args):
        pass

if __name__ == "__main__":
    KVMUnInstall()