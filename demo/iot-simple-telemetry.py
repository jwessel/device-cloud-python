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
from datetime import datetime

head, tail = os.path.split(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, head)

import device_cloud as iot

running = True
sending_telemetry = False

# Return status once the cloud responds
cloud_response = False

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

    # set an out parameter with the current state of the alarm
    # Note: completion variables DO NOT need to be defined in the
    # thing definiton in the cloud.
    p = {}

    sending_telemetry = not sending_telemetry
    if sending_telemetry:
        client.alarm_publish("telemetry_alarm", 0)
        p['alarm_state'] = "ON"
    else:
        client.alarm_publish("telemetry_alarm", 1)
        p['alarm_state'] = "OFF"

    # publish an event log
    msgstr = "Telemetry {} ".format(p['alarm_state'])
    client.info(msgstr)
    client.event_publish(msgstr)

    return (iot.STATUS_SUCCESS, "", p)

def quit_me():
    """
    Quits application (callback)
    """
    global running
    running = False
    return (iot.STATUS_SUCCESS, "")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sighandler)

    # Parse command line arguments for easy customization
    parser = argparse.ArgumentParser(description="Demo app for Python HDC "
                                     "telemetry APIs")
    parser.add_argument("-i", "--app_id", help="Custom app id")
    parser.add_argument("-c", "--config_dir", help="Custom config directory")
    parser.add_argument("-f", "--config_file", help="Custom config file name "
                        "(in config directory)")
    args = parser.parse_args(sys.argv[1:])

    # Initialize client default called 'python-demo-app'
    app_id = "iot-simple-telemetry-py"
    if args.app_id:
        app_id = args.app_id
    client = iot.Client(app_id)

    # Use the demo-connect.cfg file inside the config directory
    # (Default would be python-demo-app-connect.cfg)
    config_file = "demo-iot-simple-telemetry.cfg"
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

    # Telemetry names (properties for numbers, attributes for strings)
    properties = ["property-1", "property-2"]
    attributes = ["attribute-1", "attribute-2"]

    # Connect to Cloud
    if client.connect(timeout=10) != iot.STATUS_SUCCESS:
        client.error("Failed")
        sys.exit(1)

    counter = 0
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

                # Randomly generate telemetry and attributes to send
                for p in properties:
                    read_complete = 0
                    value = round(random.random()*1000, 2)
                    client.info("Publishing Property: %s to %s", value, p)

                    # timestamps can be added.  The API will use the
                    # current time if it is not explicitly stated
                    # ts = datetime(2017, 01, 01,11,34,22,11)
                    # Recommend using utc timestamps.  The cloud
                    # expects utc when rendering overlays with alarms.
                    ts = datetime.utcnow()
                    status = client.telemetry_publish(p, value, cloud_response, timestamp=ts)
                    while read_complete == 0:
                        status, rvalue, timestamp = client.telemetry_read_last_sample(p)
                        if status == iot.STATUS_SUCCESS:
                            read_complete = 1
                        sleep(0.5)

                    client.info("Property read back from cloud:\n"
                        "\tname %s\n"
                        "\tstatus %s\n"
                        "\tvalue %s\n"
                        "\ttimestamp %s\n"
                        %( p,status, rvalue, timestamp))

                    # Log response from cloud
                    if cloud_response:
                        if status == iot.STATUS_SUCCESS:
                            client.log(iot.LOGINFO, "Telemetry Publish - SUCCESS")
                        else:
                            client.log(iot.LOGERROR, "Telemetry Publish - FAIL")

                for a in attributes:
                    read_complete = 0
                    value = "".join(random.choice("abcdefghijklmnopqrstuvwxyz")
                                    for x in range(20))
                    client.info("Publishing Attribute: %s to %s", value, a)
                    client.attribute_publish(a, value)
                    while read_complete == 0:
                        status, rvalue, timestamp = client.attribute_read_last_sample(a)
                        if status == iot.STATUS_SUCCESS:
                            read_complete = 1
                        sleep(0.5)

                    client.info("Attribute read back from cloud:\n"
                        "\tname %s\n"
                        "\tstatus %s\n"
                        "\tvalue %s\n"
                        "\ttimestamp %s\n"
                        %(p, status, rvalue, timestamp))


            # Reset counter after sending telemetry
            counter = 0

    client.disconnect(wait_for_replies=True)

