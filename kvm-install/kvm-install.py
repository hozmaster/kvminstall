#!/usr/bin/env python
"""Python helper for virt-install(1)"""

import os
import platform
import argparse
import re
import string
import random
import include_funcs
import include_vars

__author__ = 'Jason Callaway'
__email__ = 'jason@jasoncallaway.com'
__license__ = 'Apache License Version 2.0'
__version__ = '0.1'
__status__ = 'alpha'

class KVMInstall(object):

    def setup_lvm(self):
        """Setup the VMs root volume with LVM"""

        # Grab the config values we need
        from_lvm = self.config['clone']
        size = self.config['disk']
        name = self.config['name']

        command = ['lvcreate', '-s', from_lvm, '-L', size + 'G', '-n', name]
        try:
            self.funcs.run_command(command, self.stdout, self.stderr)
        except Exception, e:
            raise e

    def setup_image(self):
        """Setup the VMs root volume with an image file"""

        # Grab the config values we need
        from_image = self.config['image']
        path = os.path.split(from_image)[0]
        extension = os.path.splitext(from_image)[1]
        size = self.config['disk']
        name = self.config['name']

        command = ['cp', from_image, path + '/' + name + extension]
        try:
            self.run_command(command, self.stdout, self.stderr)
        except Exception, e:
            raise e

    def generate_mac(self, prefix):
        generated_mac = ''
        # Determine how long our prefix is
        num_colons = prefix.count(':')
        # Add that number of hex substrings
        for _ in range(5 - num_colons):
            # This is a little big funky. I wanted to be sure we have only
            # a-f,0-9, but the string.hexdigits string includes a-f,A-F,
            # so we have to convert to lower case and strip out duplicates
            hex_domain = ''.join(set(string.hexdigits.lower()))
            print '+++ hex_domain: ' + hex_domain
            new_hex = self.get_random(hex_domain, 2)
            print '+++ new_hex: ' + new_hex
            generated_mac = generated_mac.join(':' + new_hex)
        print '+++ generated_mac: ' + generated_mac
        return self.config['mac'] + generated_mac

    def generate_ip(self):
        ip_start, ip_end = self.get_ip_range(self.virsh_netdumpxml)
        start = re.sub('^\d{1,3}\.\d{1,3}\.\d{1,3}\.', '', ip_start)
        end = re.sub('^\d{1,3}\.\d{1,3}\.\d{1,3}\.', '', ip_end)
        first_three_octets = re.sub('\.\d{1,3}$', '', ip_start)
        return first_three_octets + '.' + str(random.randint(int(start), int(end)))

    def setup_network(self):
        """Setup the virsh network settings for the VM"""

        self.net_dumpxml(self.config['network'])

        # TODO: Add IPv6 support

        try:
            # First, find a new mac address
            mac_addresses = self.get_mac_addresses()
            print '+++ mac_addresses: ' + ' '.join(mac_addresses)
            new_mac = ''
            good_mac = False
            while good_mac is False:
                new_mac = self.generate_mac(self.config['mac'])
                if new_mac not in mac_addresses:
                    good_mac = True
                    if self.config.verbose is True:
                        print '  new mac found: ' + new_mac
        except Exception, e:
            raise Exception('setup_network failed to generate a new mac address: ' + str(e))

        try:
            # Then find an IP address in range that doesn't already exist
            ip_addresses = self.get_ip_addresses()
            new_ip = ''
            good_ip = False
            while good_ip is False:
                new_ip = self.generate_ip()
                if new_ip not in ip_addresses:
                    good_ip = True
                    if self.config.verbose is True:
                        print '  new ip found: ' + new_ip
        except Exception, e:
            raise Exception('setup_network failed to generate a new ip address: ' + str(e))

        # Record the new IP for other functions' use
        self.config['new_ip'] = new_ip

        # Now generate the virst net-update command
        command = ['virsh',
                   'net-update',
                   self.config['network'],
                   'add-last',
                   'ip-dhcp-host']
        host_xml = '"<host mac=\'' + new_mac + '\' name=\'' + self.config['name'] + '.' + self.config['domain'] + \
                   '\' ip=\'' + new_ip + '\'/>"'
        command.append(host_xml)

        print '+++ command: ' + ' '.join(command)

        config_command = list(command)
        current_command = list(command)

        # Now, update the current config
        try:
            current_command.append('--current')
            self.run_command(current_command, self.stdout, self.stderr)
        except Exception, e:
            raise Exception('virsh net-update --current failed: ' + str(e))


        # First, update the persistent config
        try:
            config_command.append('--config')
            self.run_command(config_command, self.stdout, self.stderr)
        except Exception, e:
            raise Exception('virsh net-update --config failed: ' + str(e))

        # Now do the same for DNS
        command = list()
        command = ['virsh',
                   'net-update',
                   self.config['network'],
                   'add-last',
                   'dns-host']
        host_xml = '"<host ip=\'' + new_ip + '\'><hostname>' + self.config['name'] + '.' + self.config['domain'] + \
                   '</hostname></host>"'
        command.append(host_xml)

        print '+++ command: ' + ' '.join(command)

        config_command = list(command)
        current_command = list(command)

        # Now, update the current config
        try:
            current_command.append('--current')
            self.run_command(current_command, self.stdout, self.stderr)
        except Exception, e:
            raise Exception('virsh net-update --current failed: ' + str(e))


        # First, update the persistent config
        try:
            config_command.append('--config')
            self.run_command(config_command, self.stdout, self.stderr)
        except Exception, e:
            raise Exception('virsh net-update --config failed: ' + str(e))

    def do_virtinstall(self):
        command = ['virt-install',
                   '--noautoconsole',
                   '--hvm',
                   '--vnc',
                   '--name', self.config['name'],
                   '--vcpus', self.config['vcpus'],
                   '--ram', self.config['ram'],
                   '--network', self.config['network'],
                   '--os-type', self.config['type'],
                   '--os-variant', self.config['variant'],
                   '--boot', 'hd']
        if self.config.has_key('clone'):
            devpath = os.path.split(self.config['clone'])[0]
            command.append['--disk', 'path=' + devpath + '/' + self.config['name']]
        else:
            imgpath = os.path.split(self.config['image'])[0]
            command.append['--disk', 'path=' + imgpath + '/' + self.config['name'] + '.img' +
                           ',size=' + str(self.config['disk']) + ',format=qcow2']
        try:
            self.run_command(command, self.stdout, self.stderr)
        except Exception, e:
            raise e

    def __init__(self, parsed_args):
        # TODO: put in environemnt checks, i.e., does virt-install exist, etc.

        # Grab the parsed command line arguments
        self.args = parsed_args

        self.vars = include_vars.KVMInstallVars()
        self.funcs = include_funcs.KVMInstallFuncs(self.args)

        # This make my IDE happy
        self.config = {}

        # Set up our random string and temp directory
        random8 = self.funcs.get_random(string.ascii_letters + string.digits, 8)
        self.stdout, self.stderr, self.virsh_netdumpxml = self.funcs.setup_tmp(random8)

        # Check to see if we're on a supported platform.
        if platform.dist()[0] not in self.vars.SUPPORTED_PLATFORMS:
            raise Exception('unsupported platform: ' + platform.dist()[0])

        # Parse the config file and build our config object
        if self.config.verbose is True:
            print ' parsing config file'
        if self.args.configfile is None:
            self.args.configfile = self.vars.CONFIG_PATH
        self.config = self.funcs.parse_config(self.args)

        # If we have both a clone and image config directive, prefer LVM
        if self.config.has_key('clone'):
            if self.config.verbose is True:
                print ' setting up lvm'
            self.setup_lvm()
        else:
            if self.config.verbose is True:
                print ' setting up image'
            if self.config.has_key('image'):
                self.setup_image()
            else:
                raise Exception('you must specify either an LVM or file base image with -c or -i')

        try:
            # Now set up the new network
            if self.config.verbose is True:
                print ' setting up network'
            self.setup_network()
        except Exception, e:
            raise Exception('setup network failed: ' + str(e))

        try:
            # Update /etc/hosts
            if self.config.verbose is True:
                print ' updating /etc/hosts'
            self.funcs.update_etchosts()
        except Exception, e:
            raise Exception('update /etc/hosts failed: ' + str(e))

        try:
            # Restart the dnsmasq service
            if self.config.verbose is True:
                print ' restarting dnsmasq'
            self.funcs.restart_dnsmasq()
        except Exception, e:
            raise Exception('restart dnsmasq failed: ' + str(e))

        try:
            # Finally, we can install the VM
            if self.config.verbose is True:
                print ' doing virt-install'
            self.do_virtinstall()
        except Exception, e:
            raise Exception('virt-install failed: ' + str(e))

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
    parser.add_argument('--type',
                        help='os type, i.e., linux')
    parser.add_argument('--variant',
                        help='os variant, i.e., rhel7')
    parser.add_argument('-f', '--configfile',
                        help='specify an alternate config file, default=~/.config/kvm-install/config.yaml')
    parser.add_argument('--verbose', dest='verbose', action='store_true',
                        help='verbose output')
    parser.add_argument('name',
                        help='name of the new virtual machine')
    parser.set_defaults(verbose=False)
    args = parser.parse_args()
    KVMInstall(args)