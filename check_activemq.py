#!/usr/bin/env python
# -*- coding: utf-8 *-*

""" Copyright 2015 predic8 GmbH, www.predic8.com

	Licensed under the Apache License, Version 2.0 (the "License");
	you may not use this file except in compliance with the License.
	You may obtain a copy of the License at

	http://www.apache.org/licenses/LICENSE-2.0

	Unless required by applicable law or agreed to in writing, software
	distributed under the License is distributed on an "AS IS" BASIS,
	WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
	See the License for the specific language governing permissions and
	limitations under the License.
"""

import urllib
import json
import argparse
import fnmatch
import nagiosplugin as np

"""Check the size of a given ActiveMQ Queue."""

PLUGIN_VERSION = "0.4.1"

PREFIX = 'org.apache.activemq:'

def make_url(args, dest):
	return (
		(args.jolokia_url + ('' if args.jolokia_url[-1] == '/' else '/') + dest)
		if args.jolokia_url
		else ('http://'+args.user+':'+args.pwd
			+'@'+args.host+':'+str(args.port)
			+'/'+args.url_tail+'/'+dest)
	)

def query_url(args, dest=''):
	return make_url(args, PREFIX + 'type=Broker,brokerName=localhost'+dest)

def queue_url(args, queue):
	return query_url(args, ',destinationType=Queue,destinationName='+urllib.quote(queue))

def topic_url(args, topic):
	return query_url(args, ',destinationType=Topic,destinationName='+urllib.quote(topic))

def health_url(args):
	return query_url(args, ',service=Health')





def queuesize(args):

	class ActiveMqQueueSizeContext(np.ScalarContext):
		def evaluate(self, metric, resource):
			if metric.value < 0:
				return self.result_cls(np.Unknown, metric=metric)
			return super(ActiveMqQueueSizeContext, self).evaluate(metric, resource)
		def describe(self, metric):
			if metric.value < 0:
				return 'ERROR: ' + metric.name
			return super(ActiveMqQueueSizeContext, self).describe(metric)

	class ActiveMqQueueSize(np.Resource):
		def __init__(self, pattern=None):
			self.pattern = pattern
		def probe(self):
			try:
				jsn = urllib.urlopen(query_url(args))
				resp = json.loads(jsn.read())
				for queue in resp['value']['Queues']:
						jsn = urllib.urlopen(make_url(args, queue['objectName']))
						qJ = json.loads(jsn.read())['value']
						if qJ['Name'].startswith('ActiveMQ'):
							continue # skip internal ActiveMQ queues
						if (self.pattern
								and fnmatch.fnmatch(qJ['Name'], self.pattern)
								or not self.pattern):
							yield np.Metric('Queue Size of %s' % qJ['Name'],
														qJ['QueueSize'], min=0,
														context='size')
			except IOError as e:
				yield np.Metric('Fetching network FAILED: ' + str(e), -1, context='size')
			except ValueError as e:
				yield np.Metric('Decoding Json FAILED: ' + str(e), -1, context='size')
			except KeyError as e:
				yield np.Metric('Getting Queue(s) FAILED: ' + str(e), -1, context='size')

	class ActiveMqQueueSizeSummary(np.Summary):
		def ok(self, results):
			if len(results) > 1:
				lenQ = str(len(results))
				minQ = str(min(results, key=lambda r: r.metric.value).metric.value)
				avgQ = str(sum([r.metric.value for r in results]) / len(results))
				maxQ = str(max(results, key=lambda r: r.metric.value).metric.value)
				return ('Checked ' + lenQ + ' queues with lengths min/avg/max = '
						+ '/'.join([minQ, avgQ, maxQ]))
			else:
				return super(ActiveMqQueueSizeSummary, self).ok(results)

	if args.queue:
		check = np.Check(
				ActiveMqQueueSize(args.queue), ## check ONE queue (or glob)
				ActiveMqQueueSizeContext('size', args.warn, args.crit),
				ActiveMqQueueSizeSummary()
			)
		check.main()
	else:
		check = np.Check(
				ActiveMqQueueSize(), # check ALL queues
				ActiveMqQueueSizeContext('size', args.warn, args.crit),
				ActiveMqQueueSizeSummary()
			)
		check.main()





def health(args):

	class ActiveMqHealthContext(np.Context):
		def evaluate(self, metric, resource):
			if metric.value < 0:
				return self.result_cls(np.Unknown, metric=metric)
			if metric.value == "Good":
				return self.result_cls(np.Ok, metric=metric)
			else:
				return self.result_cls(np.Warn, metric=metric)
		def describe(self, metric):
			if metric.value < 0:
				return 'ERROR: ' + metric.name
			return metric.name + ' ' + metric.value

	class ActiveMqHealth(np.Resource):
		def probe(self):
			try:
				jsn = urllib.urlopen(health_url(args))
				resp = json.loads(jsn.read())
				status = resp['value']['CurrentStatus']
				return np.Metric('CurrentStatus', status, context='health')
			except IOError as e:
				return np.Metric('Fetching network FAILED: ' + str(e), -1, context='health')
			except ValueError as e:
				return np.Metric('Decoding Json FAILED: ' + str(e), -1, context='health')
			except KeyError as e:
				return np.Metric('Getting Values FAILED: ' + str(e), -1, context='health')

	check = np.Check(
			ActiveMqHealth(), ## check ONE queue
			ActiveMqHealthContext('health')
		)
	check.main()





def subscriber(args):
	""" In the subscriber module there are several error codes that are used internally.
	    -1   Miscellaneous Error (network, json, key value)
	    -2   Topic Name is invalid / doesn't exist
	    -3   Topic has no Subscribers
	    -4   Client ID is invalid / doesn't exist
	    True/False aren't error codes, but the result whether clientId is an
	    active subscriber of topic.
	"""

	class ActiveMqSubscriberContext(np.Context):
		def evaluate(self, metric, resource):
			if metric.value == -1: # Network or JSON Error
				return self.result_cls(np.Unknown, metric=metric)
			elif metric.value == -2: # Topic doesn't exist
				return self.result_cls(np.Critical, metric=metric)
			elif metric.value == -3: # Topic has no subscribers
				return self.result_cls(np.Critical, metric=metric)
			elif metric.value == -4: # Client invalid
				return self.result_cls(np.Critical, metric=metric)
			elif metric.value == True:
				return self.result_cls(np.Ok, metric=metric)
			elif metric.value == False:
				return self.result_cls(np.Warn, metric=metric)
			else: ###
				return self.result_cls(np.Critical, metric=metric)
		def describe(self, metric):
			if metric.value == -1:
				return 'ERROR: ' + metric.name
			elif metric.value == -2:
				return 'Topic ' + args.topic + ' IS INVALID / DOES NOT EXIST'
			elif metric.value == -3:
				return 'Topic ' + args.topic + ' HAS NO SUBSCRIBERS'
			elif metric.value == -4:
				return 'Subscriber ID ' + args.clientId + ' IS INVALID / DOES NOT EXIST'
			return ('Client ' + args.clientId + ' is an '
			        +('active'if metric.value==True else 'INACTIVE')
			        +' subscriber of Topic ' + args.topic)

	class ActiveMqSubscriber(np.Resource):
		def probe(self):
			try:
				jsn = urllib.urlopen(topic_url(args, args.topic)) # get a Topic
				resp = json.loads(jsn.read()) # parse JSON

				if resp['status'] != 200: # None -> Topic doesn't exist
					return np.Metric('subscription', -2, context='subscriber')

				subs = resp['value']['Subscriptions'] # Subscriptions for Topic

				def client_is_active_subscriber(clientId, subscription):
					subUrl = make_url(args, urllib.quote(subscription['objectName']))
					jsn = urllib.urlopen(subUrl) # get the subscription
					subResp = json.loads(jsn.read()) # parse JSON

					if subResp['value']['DestinationName'] != args.topic: # should always hold
						return -2 # Topic is invalid / doesn't exist
					if subResp['value']['ClientId'] != args.clientId: # subscriber ID check
						return -4 # clientId invalid
					return subResp['value']['Active'] # subscribtion active?

				# check if clientId is among the subscribers
				analyze = [client_is_active_subscriber(args.clientId, s) for s in subs]
				if not analyze:
					return np.Metric('subscription', -3, context='subscriber')
				if -2 in analyze: # should never occur, just for safety
					return np.Metric('subscription', -2, context='subscriber')
				elif True in analyze: # active subscriber
					return np.Metric('subscription', True, context='subscriber')
				elif False in analyze: # INACTIVE subscriber
					return np.Metric('subscription', False, context='subscriber')
				elif -4 in analyze: # all clients failed
					return np.Metric('subscription', -4, context='subscriber')

			except IOError as e:
				return np.Metric('Fetching network FAILED: ' + str(e), -1, context='subscriber')
			except ValueError as e:
				return np.Metric('Decoding Json FAILED: ' + str(e), -1, context='subscriber')
			except KeyError as e:
				return np.Metric('Getting Values FAILED: ' + str(e), -1, context='subscriber')

	check = np.Check(
			ActiveMqSubscriber(),
			ActiveMqSubscriberContext('subscriber')
		)
	check.main()





def exists(args):

	class ActiveMqExistsContext(np.Context):
		def evaluate(self, metric, resource):
			if metric.value < 0:
				return self.result_cls(np.Unknown, metric=metric)
			if metric.value > 0:
				return self.result_cls(np.Ok, metric=metric)
			return self.result_cls(np.Critical, metric=metric)
		def describe(self, metric):
			if metric.value < 0:
				return 'ERROR: ' + metric.name
			if metric.value == 0:
				return 'Neither Queue nor Topic with name ' + args.name + ' were found!'
			if metric.value == 1:
				return 'Found Queue with name ' + args.name
			if metric.value == 2:
				return 'Found Topic with name ' + args.name
			return super(ActiveMqExistsScalarContext, self).describe(metric)

	class ActiveMqExists(np.Resource):
		def probe(self):
			try:
				jsnQ = urllib.urlopen(queue_url(args, args.name))
				respQ = json.loads(jsnQ.read())
				if respQ['status'] == 200:
					return np.Metric('exists', 1, context='exists')

				jsnT = urllib.urlopen(topic_url(args, args.name))
				respT = json.loads(jsnT.read())
				if respT['status'] == 200:
					return np.Metric('exists', 2, context='exists')

				return np.Metric('exists', 0, context='exists')

			except IOError as e:
				return np.Metric('Network fetching FAILED: ' + str(e), -1, context='exists')
			except ValueError as e:
				return np.Metric('Decoding Json FAILED: ' + str(e), -1, context='exists')
			except KeyError as e:
				return np.Metric('Getting Queue(s) FAILED: ' + str(e), -1, context='exists')

	check = np.Check(
				ActiveMqExists(),
				ActiveMqExistsContext('exists')
		)
	check.main()





@np.guarded
def main():

	# Top-level Argument Parser & Subparsers Initialization
	parser = argparse.ArgumentParser(description=__doc__)

	parser.add_argument('-v', '--version', action='version',
			help='Print version number',
			version=( '%(prog)s version ' + str(PLUGIN_VERSION) )
	)

	connection = parser.add_argument_group('Connection')
	connection.add_argument('--host', default='localhost',
			help='ActiveMQ Server Hostname (default: %(default)s)')
	connection.add_argument('--port', type=int, default=8161,
			help='ActiveMQ Server Port (default: %(default)s)')
	connection.add_argument('--url-tail',
			default='api/jolokia/read',
			#default='hawtio/jolokia/read',
			help='Jolokia URL tail part. (default: %(default)s)')
	connection.add_argument('-j', '--jolokia-url',
			help='''Override complete Jolokia URL.
					(Default: "http://USER:PWD@HOST:PORT/URLTAIL/").
					The parameters --user, --pwd, --host and --port are IGNORED
					if this paramter is specified!
					Please set this parameter carefully as it is not validated.''')

	credentials = parser.add_argument_group('Credentials')
	credentials.add_argument('-u', '--user', default='admin',
			help='Username for ActiveMQ admin account. (default: %(default)s)')
	credentials.add_argument('-p', '--pwd', default='admin',
			help='Password for ActiveMQ admin account. (default: %(default)s)')

	subparsers = parser.add_subparsers()

	# Sub-Parser for queuesize
	parser_queuesize = subparsers.add_parser('queuesize',
			help="""Check QueueSize: This mode checks the queue size of one
			        or more queues on the ActiveMQ server.
			        You can specify a queue name to check (even a pattern);
			        see description of the 'queue' paramter for details.""")
	parser_queuesize.add_argument('-w', '--warn',
			metavar='WARN', type=int, default=10,
			help='Warning if Queue Size is greater. (default: %(default)s)')
	parser_queuesize.add_argument('-c', '--crit',
			metavar='CRIT', type=int, default=100,
			help='Critical if Queue Size is greater. (default: %(default)s)')
	parser_queuesize.add_argument('queue', nargs='?',
			help='''Name of the Queue that will be checked.
			        If left empty, all Queues will be checked.
			        This also can be a Unix shell-style Wildcard
			        (much less powerful than a RegEx)
			        where * and ? can be used.''')
	parser_queuesize.set_defaults(func=queuesize)

	# Sub-Parser for health
	parser_health = subparsers.add_parser('health',
			help="""Check Health: This mode checks if the current status is 'Good'.""")
	# no additional arguments necessary
	parser_health.set_defaults(func=health)

	# Sub-Parser for subscriber
	parser_subscriber = subparsers.add_parser('subscriber',
			help="""Check Subscriber: This mode checks if the given 'clientId'
			        is a subscriber of the specified 'topic'.""")
	parser_subscriber.add_argument('--clientId', required=True,
			help='Client ID of the client that will be checked')
	parser_subscriber.add_argument('--topic', required=True,
			help='Name of the Topic that will be checked.')
	parser_subscriber.set_defaults(func=subscriber)

	# Sub-Parser for exists
	parser_exists = subparsers.add_parser('exists',
			help="""Check Exists: This mode checks if a Queue or Topic with the
			        given name exists.
			        If either a Queue or a Topic with this name exist,
					this mode yields OK.""")
	parser_exists.add_argument('--name', required=True,
			help='Name of the Queue or Topic that will be checked.')
	parser_exists.set_defaults(func=exists)

	# Evaluate Arguments
	args = parser.parse_args()
	# call the determined function with the parsed arguments
	args.func(args)

if __name__ == '__main__':
	main()
