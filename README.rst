kvminstall
==========

Python CLI helper for virt-install(1)

Installation
------------

If you haven't already, install KVM.::

    yum groupinstall Virtualization

Use pip to install.::

    pip install kvminstall

This will automatically install the utility into your PATH.

Usage
-----

::

    usage: kvminstall [-h] [-c CLONE] [-i IMAGE] [-v VCPUS] [-r RAM] [-d DISK]
                          [-D DOMAIN] [-N NETWORK] [--type TYPE]
                          [--variant VARIANT] [-f CONFIGFILE]
                          name
    
    positional arguments:
      name                  name of the new virtual machine
    
    optional arguments:
      -h, --help            show this help message and exit
      -c CLONE, --clone CLONE
                            name of the source logical volume to be cloned
      -i IMAGE, --image IMAGE
                            image file to duplicate
      -v VCPUS, --vcpus VCPUS
                            number of virtual CPUs
      -r RAM, --ram RAM     amount of RAM in MB
      -d DISK, --disk DISK  disk size in GB
      -D DOMAIN, --domain DOMAIN
                            domainname for dhcp / dnsmasq
      -N NETWORK, --network NETWORK
                            libvirt network
      -I IPADDRESS, --ipaddress IPADDRESS
                            specify the 4th octet of the IP address

      --type TYPE           os type, i.e., linux
      --variant VARIANT     os variant, i.e., rhel7
      -f CONFIGFILE, --configfile CONFIGFILE
                            specify an alternate config file, default=~/.config
                        /kvm-install/config.yaml

Example
-------

Assume that you have a pre-built base image with an LVM backend in the libvirt_lvm VG.::

    kvminstall -c /dev/libvirt_lvm/rhel71base examplevm


