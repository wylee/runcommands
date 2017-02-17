import sys

from setuptools import find_packages, setup

with open('README.rst') as fp:
    long_description = fp.read().strip()

install_requires = []

if sys.version_info[:2] < (3, 4):
    install_requires.append('enum34')

setup(
    name='taskrunner',
    version='1.0.0.dev0',
    license='MIT',
    author='Wyatt Baldwin',
    author_email='self@wyattbaldwin.com',
    description='Task runner',
    long_description=long_description,
    url='https://bitbucket.org/wyatt/taskrunner',
    packages=find_packages(),
    install_requires=install_requires,
    extras_require={
        'dev': [
            'coverage',
            'flake8',
        ]
    },
    entry_points={
        'console_scripts': [
            'run = taskrunner.__main__:main',
            'runtask = taskrunner.__main__:main',
            'runtasks = taskrunner.__main__:main',
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
