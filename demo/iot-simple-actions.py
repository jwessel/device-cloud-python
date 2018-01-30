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
Simple app that demonstrates the action APIs in the HDC Python library
"""

import argparse
import errno
import os
from os.path import abspath
import signal
import sys
from time import sleep

head, tail = os.path.split(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, head)

import device_cloud as iot
from device_cloud import osal

running = True

def sighandler(signum, frame):
    """
    Signal handler for exiting app
    """
    global running
    if signum == signal.SIGINT:
        print("Received SIGINT, stopping application...")
        running = False

def basic_action():
    """
    Simple action callback that takes no parameters.
    """
    print("I'm an action!")
    return (iot.STATUS_SUCCESS, "")

def send_event(client):
    """
    Simple action callback that takes one parameter, client, so it can send an
    event up to the cloud.
    """
    client.event_publish("I'm an action!")
    return (iot.STATUS_SUCCESS, "")

def parameter_action(client, params):
    """
    Action callback that takes two parameters, client and action params, that
    will print the message present in the "message" parameter send by the cloud
    when the action is executed.
    """
    message = params.get("message", "")
    print(message)


    # example on how to use out parameters.  Note: completion
    # variables DO NOT need to be defined in the thing definiton in
    # the cloud.
    p = {}
    p['response'] = "this is an example completion variable"
    p['response2'] = "Another completion variable"
    p['response3'] = "Yet another completion variable"

    return (iot.STATUS_SUCCESS, "", p)

def file_upload(client, params, user_data):
    """
    Callback for the "file_upload" method which uploads a file from the
    cloud to the local system. Wildcards in the file name are supported.
    """
    file_name = None
    if params:
        file_name = params.get("file_name")
        if "dest_name" in params:
            dest_name = params.get("dest_name")
        else:
            dest_name = None

        file_global = params.get("global", False)

    if file_name:
        if not file_name.startswith('~'):
            if not file_name.startswith('/'):
                file_name = abspath(os.path.join(user_data[0], "upload", \
                                    file_name))
            client.log(iot.LOGINFO, "Uploading {}".format(file_name))
            result = client.file_upload(file_name, upload_name=dest_name, \
                                        blocking=True, timeout=240, \
                                        file_global=file_global)
            if result == iot.STATUS_SUCCESS:
                message = ""
            else:
                message = iot.status_string(result)
        else:
            message = "Paths cannot use '~' to reference a home directory"
            result = iot.STATUS_BAD_PARAMETER
    else:
        result = iot.STATUS_BAD_PARAMETER
        message = "No file name given"

    return (result, message)

def advanced_action(client, params, user_data, request):
    """
    Action callback that takes four parameters that will take extra data
    (request_id) from the action execution request to send updates to the cloud.
    These updates appear in the thing's "mailbox" page.
    """
    client.action_progress_update(request.request_id, "I was invoked!")
    sleep(3)
    client.action_progress_update(request.request_id, "I waited for a bit!")
    return (iot.STATUS_SUCCESS, "")

def deregistered_action():
    """
    Callback for an action that gets immediately deregistered after
    registration. This should never get called; if it does it returns a failure
    to the cloud.
    """
    return (iot.STATUS_FAILURE, "This callback should not have been executed!!")

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
                                     "location APIs")
    parser.add_argument("-i", "--app_id", help="Custom app id")
    parser.add_argument("-c", "--config_dir", help="Custom config directory")
    parser.add_argument("-f", "--config_file", help="Custom config file name "
                        "(in config directory)")
    args = parser.parse_args(sys.argv[1:])

    # Initialize client default called 'python-demo-app'
    app_id = "iot-simple-actions-py"
    if args.app_id:
        app_id = args.app_id
    client = iot.Client(app_id)

    # Use the demo-connect.cfg file inside the config directory
    # (Default would be python-demo-app-connect.cfg)
    config_file = "demo-iot-simple-actions.cfg"
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
    client.action_register_callback("basic_action", basic_action)
    client.action_register_callback("send_event", send_event)
    client.action_register_callback("print_message", parameter_action)
    client.action_register_callback("file_upload", file_upload, ".")
    client.action_register_callback("advanced_action", advanced_action)
    client.action_register_callback("deregistered_action", deregistered_action)
    if osal.POSIX:
        client.action_register_command("command_action", "./action.sh")
    elif osal.WIN32:
        client.action_register_command("command_action", ".\\action.bat")
    client.action_register_callback("quit", quit_me)

    # Connect to Cloud
    if client.connect(timeout=10) != iot.STATUS_SUCCESS:
        client.error("Failed")
        sys.exit(1)

    # Deregister a previously registered action
    client.action_deregister("deregistered_action")

    while running and client.is_alive():

        # Wrap sleep with an exception handler to fix SIGINT handling on Windows
        try:
            sleep(1)
        except IOError as err:
            if err.errno != errno.EINTR:
                raise

    client.disconnect(wait_for_replies=True)

