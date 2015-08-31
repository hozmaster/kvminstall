#!/usr/bin/env python
"""Common functions for kvminstall, kvm-uninsall, and kvm-reset"""

import subprocess
import os
import yaml
import random
import xml.etree.ElementTree as ET

__author__ = 'Jason Callaway'
__email__ = 'jason@jasoncallaway.com'
__license__ = 'Apache License Version 2.0'
__version__ = '0.1'
__status__ = 'alpha'

# TODO: add support for other platforms


class KVMInstallFuncs(object):

    def setup_tmp(self, random8):
        # Set up our temp directories and return the path names to the
        # STDOUT and STDERR files as well as the virsh net-dumpxml file.
        tmpdir = '/tmp/kvminstall-' + random8
        try:
            os.makedirs(tmpdir)
        except Exception, e:
            raise e
        stdout = tmpdir + '/stdout.txt'
        stderr = tmpdir + '/stderr.txt'
        virsh_netdumpxml = tmpdir + '/netdump.xml'

        return stdout, stderr, virsh_netdumpxml

    def get_random(self, domain, length):
        return ''.join(random.SystemRandom().choice(domain)
                       for _ in range(length))

    def parse_config(self, args):
        """Parse home dir .config file"""

        # This function does three things. If the default_config file doesn't
        # exist, we create it. Once we create it, or if it already exists,
        # we load the config values and return them. Lastly, if the user
        # specified any command line args, we override the default_config with
        # those arguments.

        # Determine default_config location, or use the one specified by arg.
        package_directory = os.path.dirname(os.path.abspath(__file__))
        varsyaml = os.path.join(package_directory,
                                'include_vars.yaml')

        include_vars_yaml = open(varsyaml).read()
        include_vars = yaml.load(include_vars_yaml)
        if args.configfile is None:
            config_path = include_vars['default_config']
        else:
            config_path = args.configfile
        if args.verbose is True:
            print '  using config file: ' + config_path

        # If the config file doesn't exist, let's create and populate it.
        try:
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
            raise Exception('unable to create config file at ' +
                            config_path + ': ' + str(e))

        # Now read and parse it
        try:
            config_string = open(config_path).read()
            config = yaml.load(config_string)
        except Exception, e:
            raise Exception('unable to read config file at ' +
                            config_path + ': ' + str(e))

        # Now iterate over the arguments to build the config.
        # Remember, self.args is a Namespace.
        for k in args.__dict__:
            if args.__dict__[k] is not None:
                config[k] = args.__dict__[k]

        return config

    def run_command(self, command, config):
        """Run a shell command and output STDOUT and STDERR to the files
        defined in the config dict."""

        stdout = config['stdout']
        stderr = config['stderr']
        if config['verbose'] is True:
            print '  running command: ' + ' '.join(command)
            print '  stdout: ' + stdout
            print '  stderr: ' + stderr
        out = open(stdout, 'a')
        err = open(stderr, 'a')
        # In order to run with shell=True we have to pass subprocess a string.
        # There's probably a cleaner way to do this, but when I first wrote
        # this function I was using shell=False, which makes subprocess.call
        # expect a list.
        # So we'll join the elements of the command List.
        exit_signal = subprocess.call(' '.join(command),
                                      stdout=out,
                                      stderr=err,
                                      shell=True)
        if exit_signal != 0:
            raise Exception('command failed with exit signal ' +
                            str(exit_signal) + ': ' + ' '.join(command))
        out.close()
        err.close()

    def net_dumpxml(self, config):
        """Run a virsh net-dumpxml on the specified network."""

        network = config['network']
        xml = config['virsh_netdumpxml']
        # This is ugly. We're using shell redirection to write the output
        # to our xml file. Need to make this suck less.
        command = ['virsh', 'net-dumpxml', network, '>', xml]
        try:
            self.run_command(command, config)
        except Exception, e:
            raise e

    def get_etree_elements(self, xmlfile, element):
        """Parse XML and return a list of elements."""

        tree = ET.parse(xmlfile)
        l = []
        for elem in tree.getiterator():
            if elem.get(element) is not None:
                l.append(elem.get(element))
        return l

    def get_mac_addresses(self, config):
        return self.get_etree_elements(config['virsh_netdumpxml'], 'mac')

    def get_ip_addresses(self, config):
        return self.get_etree_elements(config['virsh_netdumpxml'], 'ip')

    def get_ip_range(self, xmlfile):
        """Find the DHCP range in an XML file and return the floor and ceiling
        IP values."""

        # Note: currently only looks at the last octet, or class C addresses.
        # TODO add support for class A and B ranges.
        tree = ET.parse(xmlfile)
        root = tree.getroot()
        start = root.find('ip').find('dhcp').find('range').get('start')
        end = root.find('ip').find('dhcp').find('range').get('end')
        return [start, end]

    def update_etchosts(self, config, action):
        """Read /etc/hosts, truncate it, then re-write it with the new
        values."""

        # TODO add locking.
        if action == 'add':
            try:
                etchosts = open('/etc/hosts', 'r+')
                hosts = etchosts.read()
                hosts = hosts + config['new_ip'] + '\t' + \
                        config['name'] + '.' + config['domain'] + ' ' + \
                        config['name'] + '\n'
                etchosts.seek(0)
                etchosts.truncate()
                etchosts.write(hosts)
                etchosts.close()
            except Exception, e:
                raise e
        # TODO: add delete action

    def restart_dnsmasq(self, config):
        """Restart the dnsmasq service."""

        # TODO currently only supports systemd, add upstart support
        command = ['systemctl', 'restart', 'dnsmasq.service']
        try:
            self.run_command(command, config)
        except Exception, e:
            raise e

    def __init__(self):
        pass
