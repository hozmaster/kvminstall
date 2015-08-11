#!/usr/bin/env python
"""Python helper script for virt-install(1)"""

import sys
import os
import platform
import argparse
import yaml

__author__ = 'Jason Callaway'
__email__ = 'jason@jasoncallaway.com'
__license__ = 'Apache License Version 2.0'
__version__ = '0.1'
__status__ = 'alpha'

SUPPORTED_PLATFORMS = ['rhel', 'fedora']
CONFIG_PATH = '~/.config/kvm-install/config.yaml'

class KVMInstall:

    def parse_config(self, path):

    def __init__(self, parsed_args):
        if platform.dist()[0] not in SUPPORTED_PLATFORMS:
            raise Exception('unsupported platform: ' + platform.dist()[0])
        self.parsed_args = parsed_args


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('name',
                        help='name of the new virtual machine')
    parser.add_argument('-f', '--from',
                        help='name of the source logical volume to be cloned')
    parser.add_argument('-v', '--vcpus',
                        help='number of virtual CPUs')
    parser.add_argument('-r', '--ram',
                        help='amount of RAM in MB')
    args = parser.parse_args()
    KVMInstall(args)