#!/usr/bin/env python

"""
A script that tests the device_cloud agent when network problems are encountered.
This is done by first executing an application which attempts to publish telemetry
while disconnected and then reconnects to the cloud. The script then checks the cloud
for the values.
If QoS is set to 0, there should be no values published when the app reconnects.
If QoS is set to 1, all values should be found in the cloud.
In the Cloud there must be a thing definition with a property "property".

"""

import socket
import subprocess
import datetime
import random
import getpass
import json
import os
import sys
import requests
from time import sleep
from threading import Thread

if sys.version_info.major == 2:
    input = raw_input
    import queue as queue
else:
    import queue

pycommand = "python"
if sys.version_info.major == 3 and sys.platform.startswith("linux"):
    pycommand = "python3"

queue = queue.Queue()
varray = []

cloud = "core-api.hdcstg.net"
app_file = "qos_app.py"
app = pycommand+" "+app_file
prop_name = "property"

def connect():
    """
     Create server socket and accept connections

    """
    try:
        socket.setdefaulttimeout(60)
        server_socket = socket.socket()
        server_socket.bind(('localhost', 8080))
        server_socket.listen(2)
        conn, address = server_socket.accept() 
        print ("Connected by {}".format(address))
        queue.put(conn)
    except:
        print ("Could not connect. Exiting.")
        sys.exit()

def server_program(conn):
    """
     Run the test within the app

    """
    counter = random.randint(2, 6) # Number of rounds of connection loss
    print ("Doing {} rounds of tests..".format(counter))
    while (counter > 0):
        dur = random.randint(2, 10) # Number of publishes per round
        conn.send(str(dur).encode())
        print ("**Testing Connection Loss** - Sending {} values".format(dur))

        while dur > 0:
            sys.stdout.write("%i \r" % dur)
            sys.stdout.flush()
            value = float(conn.recv(1024).decode())
            varray.extend([value])
            dur -= 1
        counter -= 1

def quit_app():
    """
     Close server socket and terminate app

    """
    conn.send(("close").encode())
    sleep(2)
    app.terminate()
    app.wait()
    conn.close()

def validate(varray, session_id, thing_key):
    """
     Check that all attempted values have been published
     Based off of the validate script

    """
    t = datetime.datetime.utcnow()
    end_time = t.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    prop = None
    values = 0
    amount = len(varray)
    print ("Total values = {}".format(amount))
    for i in range(10): #Try 10 times
        prop_info = properties(session_id, thing_key, end_time)
        if (prop_info["success"] == True) and prop_info["params"]: 
           values = prop_info["params"]["values"]
           if values:
               for v in values:
                   value = v["value"]
                   time = v["ts"]
                   time = datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
                   if value in varray:
                       print ("Found a match for {} at {}".format(value, time))
                       varray.remove(value)
               if varray:
                   print ("ERROR: Not all values have been published!")
                   if i == 1:
                       break
                   print ("Trying again in 30 second..")
                   sleep(30) 
               else:
                   break
           else:
               print ("No published values found!")
               if i == 1:
                   break
               print ("Trying again in 30 second..")
               sleep(30)   
        else:
            print ("ERROR: Property or published values not found in Cloud!")
            if i == 1:
                break
            print ("Trying again in 30 second..")
            sleep(30)
    if varray:
        print ("\n{} value(s) were not published: \n{}".format(len(varray), varray))
    else:
        print ("\nAll {} values have been succesfully published!".format(amount))

def properties(session_id, thing_key, end_time):
    """
     Get published properties within time frame

    """
    data_params = {"thingKey":thing_key,"key":prop_name,"start":start_time,"end":end_time}
    data = {"cmd":{"command":"property.history","params":data_params}}
    return _send(data, session_id)

def get_session(username, password):
    """
     Start Session

    """
    data_params = {"username":username,"password":password}
    data = {"auth":{"command":"api.authenticate","params":data_params}}
    return _send(data)

def _send(data, session_id=None):
    """
     Send requests
     From the validate script

    """
    headers = None
    if session_id:
        headers = {"sessionId":session_id}
    datastr = json.dumps(data)
    r = requests.post("https://"+cloud+"/api", headers=headers, data=datastr)
    if r.status_code == 200:
        try:
            rjson = r.json()
            if "auth" in rjson:
                ret = rjson["auth"]
            elif "cmd" in rjson:
                ret = rjson["cmd"]
            return ret
        except Exception as error:
            print (error)
    return {"success":False, "content":r.content,"status_code":r.status_code}


if __name__ == '__main__':

    t = datetime.datetime.utcnow()
    start_time = datetime.date.strftime(t, "%Y-%m-%dT%H:%M:%S.%fZ")

    # Start session 
    session_id = ""
    print ("Cloud: {}".format(cloud))
    user = input("Cloud Username: ")
    pw = getpass.getpass("Cloud Password:")
    session_info = get_session(user, pw)

    # Get session_id
    if session_info["success"] == True:
        session_id = session_info["params"]["sessionId"]
    if not session_id:
        print ("Failed to get session id.")
        sys.exit(1)

    # Get device_id
    if os.path.isfile("device_id"):
        with open("device_id", "r") as did:
            device_id = did.read().strip()
        thing_key = device_id + "-qos_app"
    else:
        print ("Failed to find device id.")
        sys.exit(1)

    #Connect to socket
    threading = Thread(target=connect)
    threading.start()
    print ("Waiting for Connection..")

    # Start app
    app = subprocess.Popen("exec " + app, stdout=subprocess.PIPE, shell=True)

    conn = queue.get()
    username = input("Device Username: ") #For proxy
    conn.send(username.encode())
    password = getpass.getpass("Device Password:") #For proxy
    conn.send(password.encode())

    # Check connection
    stat = conn.recv(1024).decode()
    if stat == "fail":
        print ("\nFailed to connect.")
        quit_app()

    # Run test
    else:
        server_program(conn)
        sleep(2)
        quit_app()
        validate(varray, session_id, thing_key)

    sys.exit(1)

