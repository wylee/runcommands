import os
from setuptools import find_packages, setup

with open('runcommands/__init__.py') as fp:
    for line in fp:
        if line.startswith('__version__'):
            __version__ = line.split('=')[1].strip()[1:-1]

with open('README.rst') as fp:
    long_description = fp.read().strip()

console_scripts = [
    'runcommand = runcommands.__main__:main',
    'runcommands = runcommands.__main__:main',
    'runcommands-complete = runcommands.completion:complete.console_script',
]

if os.getenv('VIRTUAL_ENV'):
    console_scripts.append('run = runcommands.__main__:main')

install_release_console_script = os.getenv('RUNCOMMANDS_INSTALL_RELEASE_CONSOLE_SCRIPT') or ''
install_release_console_script = install_release_console_script.lower()
install_release_console_script = install_release_console_script in ('1', 'true', 'yes')
if install_release_console_script:
    console_scripts.append('release = runcommands.commands:release.console_script')

setup(
    name='runcommands',
    version=__version__,
    license='MIT',
    author='Wyatt Baldwin',
    author_email='self@wyattbaldwin.com',
    description='A simple command runner',
    long_description=long_description,
    keywords=['run', 'commands', 'console', 'scripts', 'terminal'],
    url='https://github.com/wylee/runcommands',
    python_requires='>=3.5',
    install_requires=[
        'Jinja2>=2.10',
        'PyYAML>=5.1',
    ],
    packages=find_packages(),
    include_package_data=True,
    extras_require={
        'dev': [
            'coverage',
            'flake8',
            'Sphinx',
        ],
        'tox': [
            'flake8',
            'tox',
        ],
    },
    entry_points={
        'console_scripts': console_scripts,
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Build Tools',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
)
