from distutils.core import setup
setup(name='kvminstall',
      packages=['kvminstall'],
      install_requires=['PyYAML'],
      version='0.1.1',
      description='Python helper CLI for virt-install(1)',
      author='Jason Callaway',
      author_email='jason@jasoncallaway.com',
      license='Apache 2.0',
      url='https://github.com/jason-callaway/kvminstall',
      download_url='https://github.com/jason-callaway/kvminstall/tarball/0.1.1',
      keywords=['kvm', 'qemu', 'vm', 'virt-install'],
      classifiers=[
            'Development Status :: 3 - Alpha',
            'License :: OSI Approved :: Apache 2.0',
            'Programming Language :: Python :: 2.7',
      ],
      scripts=['bin/kvminstall'])
