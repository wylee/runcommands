import os
from setuptools import find_packages, setup


def as_bool(value):
    # Convert env var to bool
    if not isinstance(value, str):
        return value
    return value.lower() in ('1', 'true', 'yes')


with open('runcommands/__init__.py') as fp:
    for line in fp:
        if line.startswith('__version__'):
            __version__ = line.split('=')[1].strip()[1:-1]

with open('README.rst') as fp:
    long_description = fp.read().strip()

# Install run, runcommand, and runcommands main console scripts by default
default_aliases = 'run runcommand runcommands'
script_names = os.getenv('RUNCOMMANDS_CONSOLE_SCRIPTS', default_aliases).split()
script_path = 'runcommands.__main__:main'
console_scripts = ['{name} = {path}'.format(name=name, path=script_path) for name in script_names]

# Install runcommands-complete completion console script by default
install_complete_console_script = os.getenv('RUNCOMMANDS_INSTALL_COMPLETION_CONSOLE_SCRIPTS', True)
if as_bool(install_complete_console_script):
    console_scripts.extend((
        'runcommands-complete = runcommands.completion:complete.console_script',
        'runcommands-complete-base-command = '
        'runcommands.completion:complete_base_command.console_script',
    ))

# The release console script is *not* installed by default
install_release_console_script = os.getenv('RUNCOMMANDS_INSTALL_RELEASE_CONSOLE_SCRIPT', False)
if as_bool(install_release_console_script):
    console_scripts.append('make-release = runcommands.commands:release.console_script')

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
            'tox',
            'twine',
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
