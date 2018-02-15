#!/usr/bin/env python

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

"""
Simple app that demonstrates the telemetry APIs in the HDC Python library
"""

import argparse
import errno
import random
import signal
import sys
import os
from time import sleep
from datetime import datetime, timedelta

# cadvisor
import requests
import json

# Set in /etc/hosts as something like 192.168.42.100
cadvisor_hostname = 'oci-cadvisor.cube.lan'
cadvisor_port = '8080'
cadvisor_base = 'http://%s:%s/api/v1.2' % (cadvisor_hostname, cadvisor_port)
#
# For machine metrics
machine_stats = ['num_cores',
                 'cpu_frequency_khz',
                 'memory_capacity',
                 'machine_id',
                 'system_uuid',
                 'boot_id']
# Other machine fields:
#     filesystems, disk_map, network_devices
#     topology, cloud_provider, instance_type

# For containers metrics
hdc_timestamp_format = '%Y-%m-%dT%H:%M:%S.%f'

id_appcontainer = '/cube-desktop'

head, tail = os.path.split(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, head)

import device_cloud as iot

running = True
sending_telemetry = False

# Second intervals between telemetry
TELEMINTERVAL = 4

def sighandler(signum, frame):
    """
    Signal handler for exiting app
    """
    global running
    if signum == signal.SIGINT:
        print("Received SIGINT, stopping application...")
        running = False

def toggle_telem():
    """
    Turns Telemetry on or off (callback)
    """
    global sending_telemetry
    sending_telemetry = not sending_telemetry
    if sending_telemetry:
        client.alarm_publish("alarm_1", 0)
    else:
        client.alarm_publish("alarm_1", 1)
    msgstr = "{} sending telemetry".format("Now" if sending_telemetry else \
                                           "No longer")
    client.info(msgstr)
    client.event_publish(msgstr)
    return (iot.STATUS_SUCCESS, "Turned On" if sending_telemetry \
            else "Turned Off")

def calculate_cpu_usage(prev_ts, prev_value, curr_ts, curr_value):
    if (prev_ts is None):
        return None

    if (curr_ts < prev_ts):
        client.log(iot.LOGWARNING, "Current timestamp is older than previous timestamp.")
        return None

    # Convert from nanoseconds to microseconds
    y_delta = (curr_value - prev_value) / 1000

    # Calculate delta in microseconds
    x_delta = curr_ts - prev_ts

    # Ignore small time deltas
    if (x_delta <= 100*timedelta(milliseconds=1)):
       client.log(iot.LOGWARNING, "Ignoring sample, time delta is too small")
       return None

    x_delta_us = (x_delta.seconds * 1000000) + x_delta.microseconds

    result = (y_delta / x_delta_us)
    return result


def quit_me():
    """
    Quits application (callback)
    """
    global running
    running = False
    return (iot.STATUS_SUCCESS, "")

def publish_attribute(name, value):
    client.log(iot.LOGINFO, "Publishing %s to %s", value, name)
    client.attribute_publish(name, value)

def publish_telemetry(name, value, timestamp=None):
    if type(timestamp) is datetime:
        client.log(iot.LOGINFO, "Publishing %s to %s at %s", value, name, timestamp)
        client.telemetry_publish(name, value, timestamp)
    else:
        client.log(iot.LOGINFO, "Publishing %s to %s", value, name)
        client.telemetry_publish(name, value)

def process_attributes(attributes):
    # Get Machine metrics
    r = requests.get('%s/machine' % cadvisor_base)

    machine_json = r.json()

    for key in machine_stats:
        if key in machine_json:
            attributes[key] = machine_json[key]
            publish_attribute(key, attributes[key])

    return attributes


def process_properties(attributes, properties):
    # Get Container metrics
    r = requests.get('%s/containers' % cadvisor_base)

    containers = r.json()
#               if 'subcontainers' in containers:
#                   print containers['subcontainers']
#                   for element in containers['subcontainers']:
#                   if 'name' in element:
#                       print("%s" % element['name'])
#               print


    if 'stats' in containers:
        for element in containers['stats']:
            curr = {}

            if 'timestamp' in element:
                client.log(iot.LOGINFO, "Current timestamp %s", element['timestamp'])
                # XXX Truncating nanosecond precision
                # Should we use numpy.datetime64?
                curr['timestamp'] = element['timestamp'][:26]

                if (curr['timestamp'][-1] == 'Z'):
                   client.log(iot.LOGWARNING, "timestamp ends in Z %s", curr['timestamp'])
                   curr['timestamp'] = curr['timestamp'][:-1]
            else:
                client.log(iot.LOGWARNING, "Skipping current stat as it has no timestamp.")
                return

            # Store metrics
            if 'cpu' in element and 'usage' in element['cpu']:
                for key in ('total','user','system'):
                    if key in element['cpu']['usage']:
                        curr['cpu_usage_%s' % key] = element['cpu']['usage'][key]
                if 'per_cpu_usage' in element['cpu']['usage']:
                    for i, item in enumerate(element['cpu']['usage']['per_cpu_usage']):
                        curr["cpu_usage_percpu_%d" % i] = item
                # print("%s" % element['cpu']['usage']['total'])
                # print json.dumps(element, sort_keys=True, indent=4, separators=(',', ': '))

            if 'memory' in element and 'usage' in element['memory']:
                curr['memory_usage'] = element['memory']['usage']

            if 'memory' in element and 'working_set' in element['memory']:
                curr['memory_workingset'] = element['memory']['working_set']

            if (properties is None):
                return curr

            prev_ts = datetime.strptime(properties['timestamp'], hdc_timestamp_format)
            curr_ts = datetime.strptime(curr['timestamp'], hdc_timestamp_format)

            if (curr_ts < prev_ts):
                client.log(iot.LOGWARNING, "Skipping current timestamp as it is older than previous timestamp.")
                return properties

            # Calculate rates of change

            # cpu_usage_x
            for key in ('total','user','system'):
                cpu_usage_x = calculate_cpu_usage(prev_ts,
                       properties['cpu_usage_%s' % key],
                       curr_ts,
                       curr['cpu_usage_%s' % key])

                if cpu_usage_x is None:
                    client.log(iot.LOGWARNING, "CPU Usage calculation returned None")
                else:
                    publish_telemetry('cpu_usage_%s' % key, str(cpu_usage_x), curr_ts)

            # memory
            for key in ('usage','workingset'):
                if "memory_%s" % key in curr:
                    publish_telemetry("memory_%s" % key, curr["memory_%s" % key], curr_ts)

            # cpu_usage_percpu
            for i in range(0, attributes['num_cores']):
                cpu_usage_percpu = calculate_cpu_usage(prev_ts,
                       properties["cpu_usage_percpu_%d" % i],
                       curr_ts,
                       curr["cpu_usage_percpu_%d" % i])

                if cpu_usage_percpu is None:
                    client.log(iot.LOGWARNING, "CPU Usage calculation returned None")
                else:
                    publish_telemetry("cpu_percpu_%d" % i, str(cpu_usage_percpu), curr_ts)
            return curr
    return properties

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sighandler)

    # Parse command line arguments for easy customization
    parser = argparse.ArgumentParser(description="Demo app for Python HDC "
                                     "telemetry APIs")
    parser.add_argument("-i", "--app_id", help="Custom app id")
    parser.add_argument("-c", "--config_dir", help="Custom config directory")
    parser.add_argument("-f", "--config_file", help="Custom config file name "
                        "(in config directory)")
    parser.add_argument("-l", "--log_file", help="Custom log file name ")
    parser.add_argument("-d", "--log_level", help="Custom log level ")
    parser.add_argument("-q", "--quiet", help="Suppress printing to stdout", action='store_true')
    args = parser.parse_args(sys.argv[1:])

    # Initialize client default called 'python-demo-app'
    app_id = "hdc-cadvisor-collector-app"
    if args.app_id:
        app_id = args.app_id
    client = iot.Client(app_id)

    # Use the specified file to output log information
    # Otherwise override use default
    # log_file = "hdc-cadvisor-collector.log"
    if args.log_file:
        client.config.log_file = args.log_file
    # client.config.log_file = log_file

    # Enable quiet mode
    if args.quiet:
        client.config.quiet = args.quiet

    # Use the specified log level
    log_level = "WARNING"
    if args.log_level:
        log_level = args.log_level
    client.config.log_level = log_level

    # Use the demo-connect.cfg file inside the config directory
    # (Default would be python-demo-app-connect.cfg)
    config_file = "hdc-cadvisor-collector.cfg"
    if args.config_file:
        config_file = args.config_file
    client.config.config_file = config_file

    # Look for device_id and demo-connect.cfg in this directory
    # (This is already default behaviour)
    config_dir = "."
    if args.config_dir:
        config_dir = args.config_dir
    client.config.config_dir = config_dir

    # Finish configuration and initialize client
    client.initialize()

    # Set action callbacks
    client.action_register_callback("toggle_telemetry", toggle_telem)
    client.action_register_callback("quit", quit_me)

    # Connect to Cloud
    if client.connect(timeout=10) != iot.STATUS_SUCCESS:
        client.error("Failed")
        sys.exit(1)

    attributes = {}
    attributes = process_attributes(attributes)

    counter = 0
    properties = None
    while running and client.is_alive():
        # Wrap sleep with an exception handler to fix SIGINT handling on Windows
        try:
            sleep(1)
        except IOError as err:
            if err.errno != errno.EINTR:
                raise
        counter += 1
        if counter >= TELEMINTERVAL:
            if sending_telemetry:
                properties = process_properties(attributes, properties)

            # Reset counter after sending telemetry
            counter = 0

    client.disconnect(wait_for_replies=True)

