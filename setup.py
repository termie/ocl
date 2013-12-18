try:
    from setuptools import setup
except:
    from distutils.core import setup

config = dict(
    name='ocl',
    version='0.1.0',
    url='https://github.com/termie/ocl',
    description='The Allspark for OpenStack',
    author='Andy Smith',
    author_email='github@anarkystic.com',
    install_requires=['requests', 'jsonschema', 'warlock', 'pyyaml'],
    packages=['ocl'],
    entry_points={
        'console_scripts': [
            'ocl = ocl.cli:main',
        ],
        'ocl.api.plugins': [
            'discovery = ocl.discovery:register',
            'glance = ocl.service.glance:register',
            'nova = ocl.service.nova:register',
            'keystone = ocl.service.keystone:register',
        ]
    },
)

setup(**config)
