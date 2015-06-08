#!/usr/bin/env python
# -*- coding: utf-8 *-*

import urllib
import json
import argparse
#import logging
import fnmatch
import nagiosplugin as np

"""Check the size of a given ActiveMQ Queue."""

#_log = logging.getLogger('nagiosplugin')

PREFIX = 'org.apache.activemq:'

def make_url(args, dest):
	return (
		(args.jolokia_url + ('' if args.jolokia_url[-1]=='/' else '/') + dest)
		if args.jolokia_url
		else ('http://'+args.user+':'+args.pwd
			+'@'+args.host+':'+str(args.port)
			+'/'+args.url_tail+'/'+dest)
	)

def query_url(args):
	return make_url(args, PREFIX + 'type=Broker,brokerName=localhost')

def queue_url(args, queue):
	return make_url(args, PREFIX + 'type=Broker,brokerName=localhost,destinationType=Queue,destinationName='+queue)

def topic_url(args, topic):
	return make_url(args, PREFIX + 'type=Broker,brokerName=localhost,destinationType=Topic,destinationName='+topic)

def health_url(args):
	return make_url(args, PREFIX + 'type=Broker,brokerName=localhost,service=Health')





def queuesize(args):

	class ActiveMqQueueSizeScalarContext(np.ScalarContext):
		def evaluate(self, metric, resource):
			if metric.value < 0:
				return self.result_cls(np.Critical, "FAIL", metric)
			return super(ActiveMqQueueSizeScalarContext, self).evaluate(metric, resource)
		def describe(self, metric):
			if metric.value < 0:
				return metric.name
			return super(ActiveMqQueueSizeScalarContext, self).describe(metric)

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
						if self.pattern and fnmatch.fnmatch(qJ['Name'], self.pattern) or not self.pattern:
							yield np.Metric('Queue Size of %s' % qJ['Name'],
														qJ['QueueSize'], min=0,
														context='size')
			except IOError as e:
				#_log.error('Network fetching FAILED. ' + str(e))
				yield np.Metric('Network fetching FAILED.', -1, context='size')
			except ValueError as e:
				#_log.error('Decoding Json FAILED. ' + str(e))
				yield np.Metric('Decoding Json FAILED.', -1, context='size')
			except KeyError as e:
				#_log.error('Loading Queue(s) FAILED. ' + str(e))
				yield np.Metric('Getting Queue(s) FAILED.', -1, context='size')

	class ActiveMqQueueSizeSummary(np.Summary):
		def ok(self, results):
			if len(results) > 1:
				lenQ = str(len(results))
				minQ = str(min(results, key=lambda r: r.metric.value).metric.value)
				avgQ = str(sum([r.metric.value for r in results]) / len(results))
				maxQ = str(max(results, key=lambda r: r.metric.value).metric.value)
				return 'Checked ' + lenQ + ' queues with lengths min/avg/max = ' + '/'.join([minQ,avgQ,maxQ])
			else:
				return super(ActiveMqQueueSizeSummary, self).ok(results)

	if args.queue:
		check = np.Check(
				ActiveMqQueueSize(args.queue), ## check ONE queue (or glob)
				ActiveMqScalarContext('size', args.warn, args.crit),
				ActiveMqQueueSizeSummary()
			)
		check.main()
	else:
		check = np.Check(
				ActiveMqQueueSize(), # check ALL queues
				ActiveMqQueueSizeScalarContext('size', args.warn, args.crit),
				ActiveMqQueueSizeSummary()
			)
		check.main()





def health(args):

	class ActiveMqHealthContext(np.Context):
		def evaluate(self, metric, resource):
			if metric.value == "Good":
				return self.result_cls(np.Ok, metric=metric)
			else:
				return self.result_cls(np.Warn, metric=metric)
		def describe(self, metric):
			return str(metric.value)

	class ActiveMqHealth(np.Resource):
		def probe(self):
			try:
				jsn = urllib.urlopen(health_url(args))
				resp = json.loads(jsn.read())
				status = resp['value']['CurrentStatus']
				return np.Metric('CurrentStatus', status, context='health')
			except IOError as e:
				return np.Metric('Network fetching FAILED.', -1, context='health')
			except ValueError as e:
				return np.Metric('Decoding Json FAILED.', -1, context='health')
			except KeyError as e:
				return np.Metric('Getting Values FAILED.', -1, context='health')

	check = np.Check(
			ActiveMqHealth(), ## check ONE queue
			ActiveMqHealthContext('health')
		)
	check.main()





def subscriber(args):

	class ActiveMqSubscriberContext(np.Context):

		def evaluate(self, metric, resource):
			if metric.value == None:
				return self.result_cls(np.Critical, metric=metric)
			else:
				if metric.value:
					return self.result_cls(np.Ok, metric=metric)
				else:
					return self.result_cls(np.Warn, metric=metric)
		def describe(self, metric):
			if metric.value == None:
				return 'Topic ' + args.topic + ' DOES NOT EXIST'
			return ('Client ' + args.clientId + ' is'
				    +(''if metric.value else ' NOT a')
			        +' subscriber of Topic ' + args.topic)

	class ActiveMqSubscriber(np.Resource):
		def probe(self):
			try:
				jsn = urllib.urlopen(topic_url(args, args.topic)) # get a Topic
				resp = json.loads(jsn.read()) # parse JSON

				if resp['status'] != 200: # None -> Topic doesn't exist
					return np.Metric('subscription', None, context='subscriber')

				subs = resp['value']['Subscriptions'] # Subscriptions for Topic

				def client_is_subscriber(clientId, subscription):
					vals = subscription['objectName'].split(',')
					correct_clientId = (lambda v:
										v.startswith('clientId=')
										and v.endswith('='+clientId))
					return any(map(correct_clientId, vals))

				# check if clientId is among the subscribers
				is_sub = any(map(lambda s: client_is_subscriber(args.clientId, s), subs))
				return np.Metric('subscription', is_sub, context='subscriber')

			except IOError as e:
				return np.Metric('Network fetching FAILED.', -1, context='subscriber')
			except ValueError as e:
				return np.Metric('Decoding Json FAILED.', -1, context='subscriber')
			except KeyError as e:
				return np.Metric('Getting Values FAILED.', -1, context='subscriber')

	check = np.Check(
			ActiveMqSubscriber(), ## check ONE queue
			ActiveMqSubscriberContext('subscriber')
		)
	check.main()





@np.guarded
def main():

	# Top-level Argument Parser & Subparsers Initialization
	parser = argparse.ArgumentParser(description = __doc__)
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
					Please be carful when setting this directly as this is not really checked.''')

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
	parser_queuesize.add_argument('-w', '--warn', metavar='WARN', type=int, default=10,
			help='Warning if Queue Size is greater. (default: %(default)s)')
	parser_queuesize.add_argument('-c', '--crit', metavar='CRIT', type=int, default=100,
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

	# Evaluate Arguments
	args = parser.parse_args()
	# call the determined function with the parsed arguments
	args.func(args)

if __name__ == '__main__':
	main()
