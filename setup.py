from setuptools import setup, find_packages
import codecs
from softlab import __version__

# prepare description
description = 'toolkit to build software-defined laboratory'
long_description = description
with codecs.open('README.rst', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='softlab',
    version=__version__,
    description=description,
    long_description=long_description,
    author='Edward',
    requires=[],
    packages=find_packages(include=['softlab', 'softlab.*']),
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Topic :: Software Developemnt :: Libraries',
        'Topic :: Software Defined Laboratory',
    ],
)
