import sys

from setuptools import find_packages, setup

with open('runcommands/__init__.py') as fp:
    for line in fp:
        if line.startswith('__version__'):
            __version__ = line.split('=')[1].strip()[1:-1]

with open('README.rst') as fp:
    long_description = fp.read().strip()

install_requires = []

if sys.version_info[:2] < (3, 4):
    install_requires.append('enum34')

setup(
    name='runcommands',
    version=__version__,
    license='MIT',
    author='Wyatt Baldwin',
    author_email='self@wyattbaldwin.com',
    description='A simple command runner',
    long_description=long_description,
    url='https://bitbucket.org/wyatt/runcommands',
    packages=find_packages(),
    install_requires=install_requires,
    extras_require={
        'dev': [
            'coverage',
            'flake8',
        ],
        'paramiko': [
            'paramiko>=2.1.2',
        ]
    },
    entry_points={
        'console_scripts': [
            'run = runcommands.__main__:main',
            'runcmd = runcommands.__main__:main',
            'runcommand = runcommands.__main__:main',
            'runcommands = runcommands.__main__:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Build Tools',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
