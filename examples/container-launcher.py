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
import subprocess
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

def file_download(client, params, user_data):
    """
    Callback for the "file_download" method which downloads a file from the
    cloud to the local system.
    """
    file_name = None
    file_path = None
    result = None
    blocking = True
    timeout = 15
    message = "AWS provisioning completed"

    if params:
        file_name = params.get("file_name")
        file_path = params.get("file_path", "/install.tar.gz")

        if file_name and not file_path:
            file_path = abspath(os.path.join(user_data[0], "download",
                                             file_name))
        if file_path and not file_name:
            file_name = os.path.basename(file_path)
        if file_path.startswith('~'):
            result = iot.STATUS_BAD_PARAMETER
            message = "Paths cannot use '~' to reference a home directory"
        elif not os.path.isabs(file_path):
            file_path = abspath(os.path.join(user_data[0], "download",
                                             file_path))

        file_global = params.get("use_global_store", False)

    if result is None:
        if file_name and file_path:
            dir_path = os.path.dirname(file_path)
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path)
                except (OSError, IOError) as e:
                    result = iot.STATUS_IO_ERROR
                    message = ("Destination directory does not exist and could "
                               "not be created!")
                    client.error(message)
                    print(e)

            if result is None:
                client.log(iot.LOGINFO, "Downloading")
                result = client.file_download(file_name, file_path, \
                                              blocking=blocking, timeout=timeout, \
                                              file_global=file_global)
                if result != iot.STATUS_SUCCESS:
                    message = iot.status_string(result)

        else:
            result = iot.STATUS_BAD_PARAMETER
            message = "No file name or destination given"

    if result == iot.STATUS_SUCCESS:
        cmd = "/usr/bin/provision_gg"
        output = {}
        try:
            p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
            out, err = p.communicate()
            i = 0
            for line in out.split(os.linesep):
                i = i + 1
                output["%03d" % i] = line
        except Exception as e:
            print("Error in run_cmd: %s" % e)
        return (iot.STATUS_SUCCESS, "", output)

    return (result, message)

def run_cmd(client, params):
    """
    Action callback that takes two parameters, client and action params, that
    will print the message present in the "message" parameter send by the cloud
    when the action is executed.
    """
    cmd = params.get("cmd", "")
    output = {}
    if cmd:
        try:
            p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
            out, err = p.communicate()
            i = 0
            for line in out.split(os.linesep):
                i = i + 1
                output["%03d" % i] = line
        except Exception as e:
            print("Error in run_cmd: %s" % e)
    return (iot.STATUS_SUCCESS, "", output)

def deploy_cube_gg(client, params):
    """
    Action callback that takes two parameters, client and action params, that
    will print the message present in the "message" parameter send by the cloud
    when the action is executed.
    """
    cmd = "/usr/bin/install_cube_gg"
    output = {}
    if cmd:
        try:
            p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
            out, err = p.communicate()
            i = 0
            for line in out.split(os.linesep):
                i = i + 1
                output["%03d" % i] = line
        except Exception as e:
            print("Error in run_cmd: %s" % e)
    return (iot.STATUS_SUCCESS, "", output)

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

def list_containers(client, params, user_data, request):
    """
    Action callback that takes four parameters that will take extra data
    (request_id) from the action execution request to send updates to the cloud.
    These updates appear in the thing's "mailbox" page.
    """
    p = subprocess.Popen(['c3', 'list'], stdout=subprocess.PIPE)
    out, err = p.communicate()
    i = 0
    p = {}
    for line in out.split(os.linesep):
        i = i + 1
        p["%i" % i] = line
        #client.action_progress_update(request.request_id, line)
    return (iot.STATUS_SUCCESS, "", p)

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
    app_id = "container-launcher-py"
    if args.app_id:
        app_id = args.app_id
    client = iot.Client(app_id)

    # Use the demo-connect.cfg file inside the config directory
    # (Default would be python-demo-app-connect.cfg)
    config_file = "container-launcher.cfg"
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
    client.action_register_callback("deploy_cube_gg", deploy_cube_gg)
    client.action_register_callback("run_cmd", run_cmd)
    client.action_register_callback("print_message", parameter_action)
    client.action_register_callback("file_download", file_download, ".")
    client.action_register_callback("list_containers", list_containers)
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

