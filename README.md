# ActiveMQ Nagios Plugin
Monitor Apache ActiveMQ's health, queuesizes and subscribers. The plugin makes use of the Jolokia REST interface.


## Requirements (tested with):
- ActiveMQ starting from version 5.8
- Python 2.7
- nagiosplugin 1.2.2

nagiosplugin is a Python Framework designed for Nagios Plugins written in Python.
It can be installed via ```pip```.


## Supported ActiveMQ Versions
The plugin queries ActiveMQ using the new REST based [Jolokia](https://jolokia.org/) interface.

### ActiveMQ < 5.8
To use this plugin with an ActiveMQ version earlier than 5.8 you have too add Jolokia support manually.

### ActiveMQ < 5.9.1
With version 5.9.1 of ActiveMQ, the Hawtio console was removed.
If you run a version of ActiveMQ that still includes Hawtio,
you need to supply the ```--url-tail "hawtio/jolokia/read"``` parameter to the plugin.

For releases without Hawtio, this paramter can be omitted and defaults to ```api/jolokia/read```.


## Installation

1. Navigate to the folder where your nagios plugins are stored e.g.:
 - ```cd /usr/lib/nagios/plugins/```
- Download the plugin script:
 - ```wget https://raw.githubusercontent.com/predic8/activemq-nagios-plugin/master/check_activemq.py```
- Install nagiosplugin for Python:
 - ```pip install nagiosplugin``` (systemwide, execute as root) or
 - ```pip install --user nagiosplugin``` (for the current user)


## Command line options:
- Run ```./check_activemq.py -h``` to see the full (and up to date) help
- ```--host``` specifies the Hostname of the ActiveMQ broker
- ```--port``` specifies the Port
- ```--user``` specifies the Username of ActiveMQ's Web Console
- ```--pwd``` specifies the Password


## Checks

This Plugin currently support 4 different checks listed below.
All checks return UNKNOWN if the broker isn't reachable on the network.

#### queuesize
- Check the size of one or more Queues.
- Additional parameters:
 - ```-w WARN``` specifies the Warning threshold (default 10)
 - ```-c CRIT``` specifies the Critical threshold (default 100)
 - ```QUEUE``` - specify queue name to check (see additional explanations below)
- If queuesize is called with NO queue parameter then ALL queues are checked (excluding queues whose name start with 'ActiveMQ').
- If queuesize is called WITH a queue then this explicit queue name is checked.
 - A given queue name can also contain shell-like wildcards like ```*``` and ```?```

#### health
- Checks the overall health of the broker.
- Returns OK or WARN.

#### subscriber
- Checks if the specified clientId is a subscriber of the specified topic and raises a Warning if this isn't the case.
- Additional parameters:
 - ```--clientId``` specifies a client ID
 - ```--topic``` specifies a topic of the ActiveMQ Broker
- Returns CRITICAL if the given Topic does not exist / has no subscribers / the clientId is invalid.
- Returns WARN if the given `clientId` is an inactive Subscriber.

#### exists
- Checks if a Queue or a Topic with the specified `name` exists.
- Additional parameters:
 - ```--name``` specifies a Queue or Topic name
- Returns Critical if no Queue or Topic with the given `name` exist.

#### subscriber_pending
- Checks the `Pending Queue Size` and the `clientId` for a given `subscription`.
- Additional parameters:
 - ```--subscription``` specifies the name of a subscription
 - ```--clientId``` specifies a client ID
- Returns Critical if `clientId` is not the Client Id of the given subscription.

#### dlq
- Check if there are new messages in a DLQ (Dead Letter Queue).
- Additional parameters:
 - ```--prefix PREFIX``` - specify DLQ prefix, all queues with a matching prefix will be checked (default 'ActiveMQ.DLQ.')
- Returns Unknown if no Queues with the specified PREFIX were found.
- Returns Critical if one of the Queues with a matching prefix contains more messages
  since the last check.
- This mode saves it's state in the file
  ``$HOME/.cache/activemq-nagios-plugin/dlq-cache.json``
- Note (this might lead to confusion): When the plugin yields a message for
  a specific queue (e.g. ``'No additional messages in ActiveMQ.DLQ.Test'=0``)
  the `=0` means that there are `0` additional messages since the last check,
  it does NOT mean that there are `0` messages in the queue. (Use `queuesize`
  if you want to check this.)


## Examples. Check
- the queue size of the queue TEST
 - ```./check_activemq.py queuesize TEST```
- the queue sizes of all queues starting with TEST
 - ```./check_activemq.py -w 30 -c 100 queuesize "TEST*"```
- the overall health of the ActiveMQ Broker
 - ```./check_activemq.py health```
- that ```Spongebob``` is a subscriber of ```BikiniBottom```
 - ```./check_activemq.py subscriber --clientId Spongebob --topic BikiniBottom```
- if a queue or a topic with a given name exists
 - ```./check_activemq.py exists --name someQueueName```
 - ```./check_activemq.py exists --name someTopicName```
- if there are new messages in the Dead Letter Queue
 - ```./check_activemq.py dlq --prefix 'DLQ.''```
