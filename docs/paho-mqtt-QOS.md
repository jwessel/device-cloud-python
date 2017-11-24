Description
===========
This document will track information regarding QOS with the paho mqtt
class.

References:
  * https://www.eclipse.org/paho/clients/python/docs/
  * https://github.com/mqtt/mqtt.github.io/wiki/Differences-between-3.1.0-and-3.1.1

Assumptions
-----------
The Reader has a general understanding of MQTT and QOS.

Offline Behaviour
-----------------
The default QOS is 1.  When the application is offline, and telemetry
is send, the telemetry will be enqueued and saved until the
applicaiton is online.  Data will then be sent.  The sending of the
data is controlled by the paho client and the MQTT protocol.

QOS Test Diagram
-----------------
```
		      +--------+
	   +----------+ Cloud  |
	   |          +---+----+
	   |              | 
	   |              | 
	   |          +---+---+
	 Validate     | Proxy +-----+
	  REST        +---+--++     |
	   |              |         |
   +-------+---+      +---+---+     |
   | Controler +------+ App   |     |
   +--+----+---+      +-------+     |
      |    |                        |
      |    +------------------------+
      |
      |
  Results
```

Test Workflow
-------------
  * Test 1: baseline test
    * Controler sets up the configuration with proxy
    * Controler starts the proxy server
    * Controler starts, lauches the App
    * Controler tells App to send x samples
    * Controler validates via REST samples

  * Test 2: offline
    * Controler disables the proxy server
    * Controler tells App to send x samples
    * Controler enables the proxy server, App should send samples
    * Controler queries cloud via REST to get samples.  May have to poll
    until all messages are on deck in cloud
    * Controler reports status of test

  * Test 3: offline action
    * Controller disables proxy
    * Controller triggers action via REST
    * Controller enables proxy
    * Controler validates that action was executed successfully

  * Other tests:
    * Repeat with longer offline intervals
    * Repeat with random offline intervals
    * Repeat to discover max samples that can be enqueued
    successfully

Test Requirements
-----------------
  * The test will comprise a controler script and a test app
  * The test app will send telemetry and provide 2 actions/methods
  * Host machine requires a simple socks5 proxy (ssh is sufficient)
  * Configure test to use a proxy server
    e.g. ssh -D 9999 username@localhost
  * Controler script will toggle the proxy server on/off at random
  intervals during the test to simulate network problems
  * The duration of the outage will be random but the lower limit must
  be functional
  * The test app will send a random number (e.g. random.randrange(1,20)) of telemetry
  samples every second.
  * The number of samples and values will be tracked
  * The samples will be verified via REST request
  * Actions will be triggered when device is offline
  * Once online actions should trigger
  * Controller will validate

Questions we should be able to answer
-------------------------------------
  * What is the default QOS level?
  * How can I change the QOS level?
  * If my app continues to send telemetry when the device is offline,
  is any data lost?
  * How many samples can be queued when offline
  * If the app seg faults or exits, will the queue be lost?
  * Once the app goes online will all queued messages be sent out at
  once or in separate messages?
  * Is there a way to throttle the send rate of offline enqueued da	
