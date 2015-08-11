#!/usr/bin/env python
"""Python helper script for virt-install(1)"""

import subprocess
import os
import platform
import argparse
import yaml

__author__ = 'Jason Callaway'
__email__ = 'jason@jasoncallaway.com'
__license__ = 'Apache License Version 2.0'
__version__ = '0.1'
__status__ = 'alpha'

SUPPORTED_PLATFORMS = ['rhel', 'centos', 'fedora']
CONFIG_PATH = '~/.config/kvm-install/config.yaml'


class KVMInstall(object):

    def setup_lvm(self):
        """Setup the VMs root volume"""
        from_lvm = self.config['from']


    def parse_config(self):
        """Parse home dir .config file"""
        config_dict = {} # shut up the IDE errors
        config_path = self.args.configfile
        try:
            # If the config file exists, parse it
            if os.path.isfile(config_path):
                config_handle = open(config_path)
                config_string = config_handle.read()
                config_dict = yaml.load(config_string)
            else:
                # Config file doesn't exist, let's create it
                if config_path == CONFIG_PATH:
                    os.makedirs(os.path.split(config_path)[0])
                    # And while we're at it, let's set some defaults
                    with open(config_path, 'w') as config_file:
                        config_file.write('---\nvcpus: 1\nram: 1024\n' +
                                          'disk: 10\ndomain: example.com\n' +
                                          'network: default\n')
                    config_file.close()
                    # Then we parse it like normal
                    config_handle = open(config_path)
                    config_string = config_handle.read()
                    config_dict = yaml.load(config_string)
        except Exception, e:
            raise Exception('unable to read config file at ' + config_path +
                            'exception: ' + str(e))

    def __init__(self, parsed_args):
        # Check to see if we're on a supported platform.
        if platform.dist()[0] not in SUPPORTED_PLATFORMS:
            raise Exception('unsupported platform: ' + platform.dist()[0])

        # Grab the parsed command line arguments
        self.args = parsed_args

        # Parse the config file
        if self.args.configfile is None:
            self.args.configfile = CONFIG_PATH
        self.config = self.parse_config(self.args.configfile)




if __name__ == "__main__":
    # Note that we want all of the arguments to be parsed as Strings.
    # This makes building the virsh and virt-install commands easier.
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--from',
                        help='name of the source logical volume to be cloned')
    parser.add_argument('-i', '--image',
                        help='image file to duplicate')
    parser.add_argument('-v', '--vcpus',
                        help='number of virtual CPUs')
    parser.add_argument('-r', '--ram',
                        help='amount of RAM in MB')
    parser.add_argument('-d', '--disk',
                        help='disk size in GB')
    parser.add_argument('-D', '--domain',
                        help='domainname for dhcp / dnsmasq')
    parser.add_argument('-N', '--network',
                        help='libvirt network')
    parser.add_argument('-F', '--configfile',
                        help='specify an alternate config file, default=~/.config/kvm-install/config.yaml')
    parser.add_argument('name',
                    help='name of the new virtual machine')
    args = parser.parse_args()
    KVMInstall(args)