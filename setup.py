from setuptools import find_packages, setup

with open('runcommands/__init__.py') as fp:
    for line in fp:
        if line.startswith('__version__'):
            __version__ = line.split('=')[1].strip()[1:-1]

with open('README.rst') as fp:
    long_description = fp.read().strip()

setup(
    name='runcommands',
    version=__version__,
    license='MIT',
    author='Wyatt Baldwin',
    author_email='self@wyattbaldwin.com',
    description='A simple command runner',
    long_description=long_description,
    keywords='commands',
    url='https://github.com/wylee/runcommands',
    install_requires=[
        'Jinja2>=2.10',
        'PyYAML>=3.12',
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
        'console_scripts': [
            'run = runcommands.__main__:main',
            'runcmd = runcommands.__main__:main',
            'runcommand = runcommands.__main__:main',
            'runcommands = runcommands.__main__:main',
            'runcommands-complete = runcommands.completion:complete.console_script',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Build Tools',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)
