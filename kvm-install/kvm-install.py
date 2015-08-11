#!/usr/bin/env python
"""Python helper script for virt-install(1)"""

import subprocess
import os
import platform
import argparse
import yaml
import xml.etree.ElementTree as ET

__author__ = 'Jason Callaway'
__email__ = 'jason@jasoncallaway.com'
__license__ = 'Apache License Version 2.0'
__version__ = '0.1'
__status__ = 'alpha'

SUPPORTED_PLATFORMS = ['rhel', 'centos', 'fedora']
CONFIG_PATH = '~/.config/kvm-install/config.yaml'

STDOUT_FILE = '/tmp/kvm-install_out.txt'
STDERR_FILE = '/tmp/kvm-install_err.txt'
VIRSH_NETDUMPXML_FILE = '/tmp/virsh-netdumpxml.xml'

class KVMInstall(object):

    def do_virtinstall(self):

    def restart_dnsmasq(self):

    def get_mac_addresses(self):
        network = self.config['network']

        # Determine which network we're talking about
        mac_prefix = self.config['mac']

        # Set up our stdout and stderr files
        stdout = open(VIRSH_NETDUMPXML_FILE, 'w')
        stderr = open(STDERR_FILE, 'a')

        command = ['virsh', 'net-dumpxml', network]
        exit_signal = subprocess.call(command, stdout=stdout, stderr=stderr)
        if exit_signal != 0:
            raise Exception('command failed with exit signal ' + str(exit_signal) + ': ' + ' '.join(command))
        stdout.close()
        stderr.close()

        # So far so good, let's go ahead and parse the xml file now
        tree = ET.parse(VIRSH_NETDUMPXML_FILE)
        ## left off here



    def setup_network(self):
        """Setup the virsh network settings for the VM"""

    def setup_lvm(self):
        """Setup the VMs root volume with LVM"""

        # Grab the config values we need
        from_lvm = self.config['clone']
        size = self.config['disk']
        name = self.config['name']

        # Setup our stdout and stderr files
        stdout = open(STDOUT_FILE, 'a')
        stderr = open(STDERR_FILE, 'a')

        command = ['lvcreate', '-s', from_lvm, '-L', size + 'G', '-n', name]
        exit_signal = subprocess.call(command, stdout=stdout, stderr=stderr)
        if exit_signal != 0:
            raise Exception('command failed with exit signal ' + str(exit_signal) + ': ' + ' '.join(command))
        stdout.close()
        stderr.close()

    def setup_image(self):
        """Setup the VMs root volume with an image file"""

        # Grab the config values we need
        from_image = self.config['image']
        path = os.path.split(from_image)[0]
        extension = os.path.splitext(from_image)[1]
        size = self.config['disk']
        name = self.config['name']

        # Setup our stdout and stderr files
        stdout = open(STDOUT_FILE, 'a')
        stderr = open(STDERR_FILE, 'a')

        command = ['cp', from_image, path + '/' + name + extension]
        exit_signal = subprocess.call(command, stdout=stdout, stderr=stderr)
        if exit_signal != 0:
            raise Exception('command failed with exit signal ' + str(exit_signal) + ': ' + ' '.join(command))
        stdout.close()
        stderr.close()

    def parse_config(self):
        """Parse home dir .config file"""
        config_path = self.args.configfile
        try:
            # If the config file exists, parse it
            if os.path.isfile(config_path):
                config_string = open(config_path).read()
                self.config = yaml.load(config_string)
            else:
                # Config file doesn't exist, let's create it
                if config_path == CONFIG_PATH:
                    os.makedirs(os.path.split(config_path)[0])
                    # And while we're at it, let's set some defaults
                    with open(config_path, 'w') as config_file:
                        config_file.write('---\nvcpus: 1\nram: 1024\n' +
                                          'disk: 10\ndomain: example.com\n' +
                                          'network: default\nmac: 5c:e0:c5:c4:26\n')
                    config_file.close()
                    # Then we parse it like normal
                    config_string = open(config_path).read()
                    self.config = yaml.load(config_string)
        except Exception, e:
            raise Exception('unable to read config file at ' + config_path +
                            'exception: ' + str(e))
        # Now iterate over the arguments to build the config
        for k in self.args.__dict__:
            if self.args.__dict__[k] is not None:
                self.config[k] = self.args.__dict__[k]

    def __init__(self, parsed_args):
        # This make my IDE happy
        self.config = {}

        # Check to see if we're on a supported platform.
        if platform.dist()[0] not in SUPPORTED_PLATFORMS:
            raise Exception('unsupported platform: ' + platform.dist()[0])

        # Grab the parsed command line arguments
        self.args = parsed_args

        # Parse the config file and build our config object
        if self.args.configfile is None:
            self.args.configfile = CONFIG_PATH
        self.parse_config()

        # If we have both a clond and image config directive, prefer LVM
        if self.config.has_key('clone'):
            self.setup_lvm()
        else:
            if self.config.has_key('image'):
                self.setup_image()
            else:
                raise Exception('you must specify either an LVM or file base image with -c or -i')


if __name__ == "__main__":
    # Note that we want all of the arguments to be parsed as Strings.
    # This makes building the virsh and virt-install commands easier.
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--clone',
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
    parser.add_argument('-f', '--configfile',
                        help='specify an alternate config file, default=~/.config/kvm-install/config.yaml')
    parser.add_argument('name',
                    help='name of the new virtual machine')
    args = parser.parse_args()
    KVMInstall(args)