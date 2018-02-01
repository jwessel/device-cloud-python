Websockets On Windows
=====================
There is a bug in the paho python module when using websockets as
transport.  The issue is that the connection drops when reading the
websocket on the device.  The issue is:

  * [Paho bug #268](https://github.com/eclipse/paho.mqtt.python/issues/268)

A fix is available, but not merged into the master branch yet.  To get
early access to the fix, the following fork of the repo can be used:

```
git clone https://github.com/element-82/paho.mqtt.python.git
cd paho.mqtt.python
pip install .
```

Using Websockets
----------------
The device-cloud-python API maps port 443 to a websocket connection to
the cloud.  Edit your existing iot-connect.cfg file and change the
port setting so that is using port 443, e.g.:

```
    "port": 443,
```

Alternatively, the generate_config.py script can be rerun, and when prompted for a
port, enter 443.

Once this change has been made, websockets will be used for transport
to the cloud.
