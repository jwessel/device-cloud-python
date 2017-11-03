#!/usr/bin/env python

"""
An app that:
 1. Starts up a proxy server
 2. Connects to cloud
 3. Turns off proxy
 4. Attempts to publish random values at random intervals to the cloud
 5. Reconnects proxy

"""

import sys, os
path = os.path.realpath(__file__)
while (os.path.basename(path) != "hdc-python"):
    path = os.path.dirname(path)
sys.path.insert(0, path)

import random
import pexpect
import socket
import device_cloud 
from time import sleep
from threading import Thread

if sys.version_info.major == 2:
    import queue as queue
else:
    import queue

queue = queue.Queue()
prop_name = "property"

def connect(username, password):
    """
     Start proxy server

    """
    call = ("ssh -N -D 9999 {}@localhost".format(username))
    child = pexpect.spawn(call, timeout=9999)
    queue.put(child)
    child.expect(["password: "])
    child.sendline(password)

def client_program(response, username, password):
    """
     Stop proxy, attempt to send telemetry, start proxy again

    """
    child = queue.get()
    child.terminate()  # Stop proxy
    data = int(response)
    while data > 0:
        value = round(random.random()*100, 2)
        client.info("Publishing %s to %s", value, prop_name)
        client.telemetry_publish(prop_name, value)
        data -= 1
        sleep(1)
        client_socket.send((str(value)).encode())

    # Start proxy again
    t = Thread(target=connect, args=(username, password,))
    t.start()
    sleep(1)
        
if __name__ == '__main__':

    # Connect to server socket
    try:
        client_socket = socket.socket()
        client_socket.connect(('localhost', 8080))
    except:
        sys.exit(1)

    # Start proxy
    username = client_socket.recv(1024).decode()
    password = client_socket.recv(1024).decode()
    t = Thread(target=connect, args=(username, password,))
    t.start()
    sleep(2)

    # Connect to cloud
    client = device_cloud.Client("qos_app")
    client.config.config_file = "test.cfg"
    client.initialize()
    client.log_level("CRITICAL")

    # Check connection
    if client.connect(timeout=10) != device_cloud.STATUS_SUCCESS:
        client_socket.send(("fail").encode())
        sys.exit(1) 
    client_socket.send(("connected").encode())

    while client.is_alive():
        response = client_socket.recv(1024).decode()
        if response == "close":
            break
        else:
            # Start test
            client_program(response, username, password)

    client.disconnect(wait_for_replies=True)

