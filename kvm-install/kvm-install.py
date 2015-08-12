#!/usr/bin/env python
"""Python helper for virt-install(1)"""

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


class KVMInstall(object):
    def setup_tmp(self, random8):
        self.tmpdir = '/tmp/kvm-install-' + random8
        try:
            os.makedirs(self.tmpdir)
        except Exception, e:
            raise e
        self.stdout = self.tmpdir + '/stdout.txt'
        self.stderr = self.tmpdir + '/stderr.txt'
        self.virsh_netdumpxml = self.tmpdir + '/netdump.xml'

    def get_random(self, domain, length):
        return ''.join(random.SystemRandom().choice(domain) for _ in range(length))

    def parse_config(self):
        """Parse home dir .config file"""

        if self.args.configfile is None:
            config_path = CONFIG_PATH
        else:
            config_path = self.args.configfile
        if self.args.verbose is True:
            print '  using config file: ' + config_path
        try:
            # If the config file doesn't exist, let's create and populate it
            if not os.path.isfile(config_path):
                os.makedirs(os.path.split(config_path)[0])
                with open(config_path, 'w') as config_file:
                    config_file.write('---\n' +
                                      'vcpus: 1\n' +
                                      'ram: 1024\n' +
                                      'disk: 10\n' +
                                      'domain: example.com\n' +
                                      'network: default\n' +
                                      'mac: 5c:e0:c5:c4:26\n' +
                                      'type: linux\n' +
                                      'variant: rhel7\n')
        except Exception, e:
            raise Exception('unable to create config file at ' + config_path + ': ' + str(e))

        try:
            # Now read and parse it
            config_string = open(config_path).read()
            self.config = yaml.load(config_string)
        except Exception, e:
            raise Exception('unable to read config file at ' + config_path + ': ' + str(e))

        # Now iterate over the arguments to build the config.
        # Remember, self.args is a Namespace.
        for k in self.args.__dict__:
            if self.args.__dict__[k] is not None:
                self.config[k] = self.args.__dict__[k]

    def run_command(self, command, stdout, stderr):
        if self.args.verbose is True:
            print '  running command: ' + ' '.join(command)
            print '  stdout: ' + stdout
            print '  stderr: ' + stderr
        out = open(stdout, 'a')
        err = open(stderr, 'a')
        exit_signal = subprocess.call(' '.join(command), stdout=out, stderr=err, shell=True)
        if exit_signal != 0:
            raise Exception('command failed with exit signal ' + str(exit_signal) + ': ' + ' '.join(command))
        out.close()
        err.close()

    def setup_lvm(self):
        """Setup the VMs root volume with LVM"""

        # Grab the config values we need
        from_lvm = self.config['clone']
        size = self.config['disk']
        name = self.config['name']

        command = ['lvcreate', '-s', from_lvm, '-L', size + 'G', '-n', name]
        try:
            self.run_command(command, self.stdout, self.stderr)
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

    def net_dumpxml(self, network):
        network = self.config['network']
        command = ['virsh', 'net-dumpxml', network]
        try:
            self.run_command(command, self.virsh_netdumpxml, self.stderr)
        except Exception, e:
            raise e

    def get_etree_elements(self, xmlfile, element):
        tree = ET.parse(xmlfile)
        l = []
        for elem in tree.getiterator():
            if elem.get(element) is not None:
                l.append(elem.get(element))
        return l

    def get_mac_addresses(self):
        return self.get_etree_elements(self.virsh_netdumpxml, 'mac')

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

    def get_ip_addresses(self):
        return self.get_etree_elements(self.virsh_netdumpxml, 'ip')

    def get_ip_range(self, xmlfile):
        tree = ET.parse(xmlfile)
        root = tree.getroot()
        start = root.find('ip').find('dhcp').find('range').get('start')
        end = root.find('ip').find('dhcp').find('range').get('end')
        return [start, end]

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
                    if self.args.verbose is True:
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
                    if self.args.verbose is True:
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

    def update_etchosts(self):
        try:
            etchosts = open('/etc/hosts', 'r+')
            hosts = etchosts.read()
            hosts = hosts + self.config['new_ip'] + '\t' + self.config['name'] + '.' + self.config['domain'] + ' ' + \
                    self.config['name'] + '\n'
            etchosts.seek(0)
            etchosts.truncate()
            etchosts.write(hosts)
            etchosts.close()
        except Exception, e:
            raise e

    def restart_dnsmasq(self):
        command = ['systemctl', 'restart', 'dnsmasq.service']
        try:
            self.run_command(command, self.stdout, self.stderr)
        except Exception, e:
            raise e

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

        # This make my IDE happy
        self.config = {}

        # Set up our random string and temp directory
        random8 = self.get_random(string.ascii_letters + string.digits, 8)
        self.setup_tmp(random8)

        # Check to see if we're on a supported platform.
        if platform.dist()[0] not in SUPPORTED_PLATFORMS:
            raise Exception('unsupported platform: ' + platform.dist()[0])

        # Parse the config file and build our config object
        if self.args.verbose is True:
            print ' parsing config file'
        if self.args.configfile is None:
            self.args.configfile = CONFIG_PATH
        self.parse_config()

        # If we have both a clone and image config directive, prefer LVM
        if self.config.has_key('clone'):
            if self.args.verbose is True:
                print ' setting up lvm'
            self.setup_lvm()
        else:
            if self.args.verbose is True:
                print ' setting up image'
            if self.config.has_key('image'):
                self.setup_image()
            else:
                raise Exception('you must specify either an LVM or file base image with -c or -i')

        try:
            # Now set up the new network
            if self.args.verbose is True:
                print ' setting up network'
            self.setup_network()
        except Exception, e:
            raise Exception('setup network failed: ' + str(e))

        try:
            # Update /etc/hosts
            if self.args.verbose is True:
                print ' updating /etc/hosts'
            self.update_etchosts()
        except Exception, e:
            raise Exception('update /etc/hosts failed: ' + str(e))

        try:
            # Restart the dnsmasq service
            if self.args.verbose is True:
                print ' restarting dnsmasq'
            self.restart_dnsmasq()
        except Exception, e:
            raise Exception('restart dnsmasq failed: ' + str(e))

        try:
            # Finally, we can install the VM
            if self.args.verbose is True:
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