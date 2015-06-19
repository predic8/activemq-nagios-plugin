# activemq-nagios-plugin
Nagios Plugins for Monitoring the Apache ActiveMQ Broker.

This is a Nagios Plugin for monitoring ActiveMQ message brokers. The plugin is written in Python.
It can be configured through various command line parameters and has 4 different modes.

## Requirements (tested with):
- Python 2.7
- nagiosplugin 1.2.2

nagiosplugin is a Python Framework designed for Nagios Plugins written in Python.
It can be installed via ```pip```.

## Installation

- A working Nagios Installation is required.
- Change directory to the folder where your nagios plugins are stored.
- Download script:
 - ```wget https://raw.githubusercontent.com/predic8/activemq-nagios-plugin/master/check_activemq.py```
- Install nagiosplugin for Python:
 - ```pip install nagiosplugin``` (systemwide, execute as root)
 - ```pip install --user nagiosplugin``` (for the current user)

## Command line options:
- Run ```./check_activemq.py -h``` to see the full (and up to date) help
- ```--host``` specifies the Hostname
- ```--port``` specifies the Port
- ```--user``` specifies the Username
- ```--pwd``` specifies the Password

## Operation Modes

#### queuesize - check the size of one or more Queues
- Additional parameters:
 - ```-w WARN``` specifies the Warning threshold (default 10)
 - ```-c CRIT``` specifies the Critical threshold (default 100)
 - ```QUEUE``` - specify queue name to check (see additional explanations below)
- If queuesize is called with NO queue paramter then ALL queues are checkes (excluding queues whose name starts with 'ActiveMQ')
- If queuesize is called WITH a queue then this explicit queue name is checked
 - A given queue name can also contain shell-like wildcards like ```*``` and ```?```

#### health - check the overall Health of the broker
 - This mode just checks if the current status of the ```Health``` service is "Good"

#### subscriber
- Additional parameters:
 - ```--cliendId``` specifies a client ID
 - ```--topic``` specifies a topic of the ActiveMQ Broker
 - This mode checks if the specified clientId is a subscriber of the specified topic and raises a Warning if this isn't the case.
 - This mode returns Critical if the given Topic does not exist.

## Examples
- Check the queue size of the queue TEST
 - ```./check_activemq.py queuesize TEST```
- Check the queue sizes of all queues starting with TEST
 - ```./check_activemq.py queuesize "TEST*"```
- Check the overall Health of the ActiveMQ Broker
 - ```./check_activemq.py health```
- Check that ```Spongebob``` is a subscriber of ```BikiniBottom```
 - ```./check_activemq.py subscriber --clientId Spongebob --topic BikiniBottom```
