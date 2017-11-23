'''
    Copyright (c) 2016-2017 Wind River Systems, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at:
    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software  distributed
    under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES
    OR CONDITIONS OF ANY KIND, either express or implied.
'''

from setuptools import setup
import sys

pyver = sys.version_info

if pyver < (2,7,9) or (pyver > (3,0,0) and pyver < (3,4,0)):
    print("Sorry, your Python version ({}.{}.{}) is not supported by device_cloud!".format(pyver[0], pyver[1], pyver[2]))
    sys.exit('Please upgrade to Python 2.7.9 or 3.4 and try again.')

setup(
    name='device_cloud',
    version='17.08.25',
    description='Python library for Wind River\'s Helix Device Cloud',
    author='Wind River Systems',
    author_email='',
    packages=['device_cloud','device_cloud._core','device_cloud.test'],
    install_requires=[
        'certifi',
        'paho-mqtt',
        'PySocks',
        'queues',
        'requests',
        'simplejson',
        'urllib3',
        'websocket',
        'websocket-client'
        ],
    maintainer='Paul Barrette',
    maintainer_email='paul.barrette@windriver.com',
    url='http://www.windriver.com/products/helix/',
    license='Apache License, Version 2.0',
    classifiers=[
        'Development Status :: 3 - Beta',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Operating System :: Microsoft :: Windows :: Windows 7',
        'Operating System :: Microsoft :: Windows :: Windows 10',
        'Operating System :: POSIX :: Linux',
        'Topic :: Software Development :: Libraries :: Python Modules'
        ]
    )
