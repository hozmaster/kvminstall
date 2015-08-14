#!/usr/bin/env python
"""Python helper for virt-install(1)"""

import os
import platform
import argparse
import re
import string
import random
import include_funcs
import yaml

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

        # Clone an LVM volume from the baseimage volume.
        command = ['lvcreate', '-s', from_lvm, '-L', size + 'G', '-n', name]
        try:
            self.funcs.run_command(command, self.config)
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

        # Copy the base image to our new file.
        command = ['cp', from_image, path + '/' + name + extension]
        try:
            self.funcs.run_command(command, self.config)
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
            domain = ''.join(set(string.hexdigits.lower()))
            new_hex = self.funcs.get_random(domain, 2)
            generated_mac = generated_mac.join(':' + new_hex)
        return self.config['mac'] + generated_mac

    def generate_ip(self):
        # We don't want to gernate an IP outside the DHCP range in the virsh
        # network.
        ip_start, ip_end = self.funcs.get_ip_range(self.config['virsh_netdumpxml'])
        start = re.sub('^\d{1,3}\.\d{1,3}\.\d{1,3}\.', '', ip_start)
        end = re.sub('^\d{1,3}\.\d{1,3}\.\d{1,3}\.', '', ip_end)
        # For now we only generate the last octect in an IPv4 address.
        # TODO: add support for generating other octets
        first_three_octets = re.sub('\.\d{1,3}$', '', ip_start)
        return first_three_octets + '.' + str(random.randint(int(start), int(end)))

    def setup_network(self):
        """Setup the virsh network settings for the VM"""

        # Dump the network config to an xml file for 1) easy parsing and
        # 2) backup just in case something goes sideways.
        self.funcs.net_dumpxml(self.config)

        # TODO: Add IPv6 support

        # First, find a new mac address
        try:
            mac_addresses = self.funcs.get_mac_addresses()
            new_mac = ''
            good_mac = False
            while good_mac is False:
                new_mac = self.generate_mac(self.config['mac'])
                if new_mac not in mac_addresses:
                    good_mac = True
                    if self.config.verbose is True:
                        print '  new mac found: ' + new_mac
        except Exception, e:
            raise Exception('setup_network failed ' +
                            'to generate a new mac address: ' + str(e))

        # Then find an IP address in range that doesn't already exist
        try:
            ip_addresses = self.funcs.get_ip_addresses()
            new_ip = ''
            good_ip = False
            while good_ip is False:
                new_ip = self.generate_ip()
                if new_ip not in ip_addresses:
                    good_ip = True
                    if self.config.verbose is True:
                        print '  new ip found: ' + new_ip
        except Exception, e:
            raise Exception('setup_network failed ' +
                            'to generate a new ip address: ' + str(e))

        # Record the new IP for other functions' use
        self.config['new_ip'] = new_ip

        # Now generate the virst net-update command.
        command = ['virsh',
                   'net-update',
                   self.config['network'],
                   'add-last',
                   'ip-dhcp-host']
        host_xml = '"<host mac=\'' + new_mac + '\' name=\'' + \
                   self.config['name'] + '.' + self.config['domain'] + \
                   '\' ip=\'' + new_ip + '\'/>"'
        command.append(host_xml)

        # We need to run virsh net-edit twice, once for the running config
        # (current), then again for the persistent config (config).
        # To be sure we're not talking to the same List object, we'll
        # initialize two new ones with the contents of command[].
        current_command = list(command)
        config_command = list(command)

        # Now, update the current config
        try:
            current_command.append('--current')
            self.funcs.run_command(current_command, self.config)
        except Exception, e:
            raise Exception('virsh net-update --current failed: ' + str(e))


        # First, update the persistent config
        try:
            config_command.append('--config')
            self.funcs.run_command(config_command, self.config)
        except Exception, e:
            raise Exception('virsh net-update --config failed: ' + str(e))

        # Now do the same for DNS
        # Lists are funny, so we're going to create a new one. Don't want
        # any elements left over from our old command[]
        command = list()
        command = ['virsh',
                   'net-update',
                   self.config['network'],
                   'add-last',
                   'dns-host']
        host_xml = '"<host ip=\'' + new_ip + '\'><hostname>' + \
                   self.config['name'] + '.' + self.config['domain'] + \
                   '</hostname></host>"'
        command.append(host_xml)

        print '+++ command: ' + ' '.join(command)

        config_command = list(command)
        current_command = list(command)

        # Now, update the current config
        try:
            current_command.append('--current')
            self.funcs.run_command(current_command, self.config)
        except Exception, e:
            raise Exception('virsh net-update --current failed: ' + str(e))


        # First, update the persistent config
        try:
            config_command.append('--config')
            self.funcs.run_command(config_command, self.config)
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
        if 'clone' in self.config:
            devpath = os.path.split(self.config['clone'])[0]
            command.append(['--disk',
                            'path=' + devpath + '/' + self.config['name']])
        else:
            imgpath = os.path.split(self.config['image'])[0]
            command.append(['--disk', 'path=' + imgpath + '/' +
                           self.config['name'] + '.img' +
                           ',size=' + str(self.config['disk']) +
                           ',format=qcow2'])
        try:
            self.funcs.run_command(command, self.config)
        except Exception, e:
            raise e

    def __init__(self, parsed_args):
        # TODO: put in environemnt checks, i.e., does virt-install exist, etc.

        # TODO: verify that we're running as root.

        # Load include_vars and funcs.
        include_vars_yaml = open('include_vars.yaml').read()
        self.vars = yaml.load(include_vars_yaml)
        self.funcs = include_funcs.KVMInstallFuncs(parsed_args)

        # Check to see if we're on a supported platform.
        if platform.dist()[0] not in self.vars['SUPPORTED_PLATFORMS']:
            raise Exception('unsupported platform: ' + platform.dist()[0])

        # This make my IDE happy
        self.config = {}

        # Set up our random string and temp directory
        domain = string.ascii_letters + string.digits
        random8 = self.funcs.get_random(domain, 8)
        stdout, stderr, virsh_netdumpxml = self.funcs.setup_tmp(random8)
        self.config['stdout'] = stdout
        self.config['stderr'] = stderr
        self.config['virsh_netdumpxml'] = virsh_netdumpxml

        # Parse the config file and build our config object
        if self.config.verbose is True:
            print ' parsing config file'
        if parsed_args.configfile is None:
            parsed_args.configfile = self.vars.DEFAULT_CONFIG
        self.config = self.funcs.parse_config(parsed_args)

        # If we have both a clone and image config directive, prefer LVM
        if 'clone' in self.config:
            if self.config.verbose is True:
                print ' setting up lvm'
            self.setup_lvm()
        else:
            if self.config.verbose is True:
                print ' setting up image'
            if 'image' in self.config:
                self.setup_image()
            else:
                raise Exception('you must specify either an LVM ' +
                                'or file base image with -c or -i')

        # Now set up the new network
        try:
            if self.config.verbose is True:
                print ' setting up network'
            self.setup_network()
        except Exception, e:
            raise Exception('setup network failed: ' + str(e))

        # Update /etc/hosts
        try:
            if self.config.verbose is True:
                print ' updating /etc/hosts'
            self.funcs.update_etchosts(self.config, 'add')
        except Exception, e:
            raise Exception('update /etc/hosts failed: ' + str(e))

        # Restart the dnsmasq service
        try:
            if self.config.verbose is True:
                print ' restarting dnsmasq'
            self.funcs.restart_dnsmasq()
        except Exception, e:
            raise Exception('restart dnsmasq failed: ' + str(e))

        # Finally, we can install the VM
        try:
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
                        help='specify an alternate config file, ' +
                             'default=~/.config/kvm-install/config.yaml')
    parser.add_argument('--verbose', dest='verbose', action='store_true',
                        help='verbose output')
    parser.add_argument('name',
                        help='name of the new virtual machine')
    parser.set_defaults(verbose=False)

    KVMInstall(parser.parse_args())
