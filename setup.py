from distutils.core import setup
setup(
  name = 'kvm-install',
  packages = ['kvm-install'],
  install_requires = ['PyYAML'],
  version = '0.1',
  description = 'Python helper script for virt-install(1)',
  author = 'Jason Callaway',
  author_email = 'jason@jasoncallaway.com',
  url = 'https://github.com/jason-callaway/kvm-install',
  download_url = 'https://github.com/jason-callaway/kvm-install/tarball/0.1',
  keywords = ['kvm', 'qemu', 'vm', 'virt-install'],
  classifiers = [],
  scripts = ['bin/kvm-install'],
)
