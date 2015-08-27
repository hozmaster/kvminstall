from distutils.core import setup
setup(name='kvminstall',
      packages=['kvminstall'],
      install_requires=['PyYAML'],
      version='0.1.2',
      description='Python helper CLI for virt-install(1)',
      author='Jason Callaway',
      author_email='jason@jasoncallaway.com',
      license='Apache 2.0',
      url='https://github.com/jason-callaway/kvminstall',
      download_url='https://github.com/jason-callaway/kvminstall/tarball/0.1.2',
      keywords=['kvm', 'qemu', 'vm', 'virt-install'],
      classifiers=[
            'Development Status :: 3 - Alpha',
            'License :: OSI Approved :: Apache Software License',
            'Programming Language :: Python :: 2.7',
      ],
      package_data={'kvminstall': ['include_vars.yaml']},
      scripts=['bin/kvminstall'])
