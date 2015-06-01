#!/usr/bin/env python
# -*- coding: utf-8 *-*

import urllib
import json
import argparse
import nagiosplugin

"""Check the size of a given ActiveMQ Queue."""

username = 'admin'
password = 'admin'
host = 'localhost'
port = 8161
site = lambda: host+':'+str(port)+'/api/jolokia/read/'
packagePrefix = ''
defaultBrokerName = ''

def make_url(dest):
	return 'http://'+username+':'+password+'@'+site()+dest

def query_url():
	return make_url('org.apache.activemq:type=Broker,brokerName=localhost')

def queue_url(queue):
	return make_url('org.apache.activemq:type=Broker,brokerName=localhost,destinationType=Queue,destinationName='+queue)

def topic_url(topic):
	return make_url('org.apache.activemq:type=Broker,brokerName=localhost,destinationType=Topic,destinationName='+topic)




def queuesize():
	pass

def health():
	pass

def subscriber():
	pass




@nagiosplugin.guarded
def main():

	# Top-level Argument Parser & Subparsers Initialization
	parser = argparse.ArgumentParser(description = __doc__)
	credentials = parser.add_argument_group('Credentials')
	credentials.add_argument('-u', '--user', default='admin',
			help='Username for ActiveMQ admin account. (default: %(default)s)')
	credentials.add_argument('-p', '--pass', default='admin',
			help='Password for ActiveMQ admin account. (default: %(default)s)')
	connection = parser.add_argument_group('Connection')
	connection.add_argument('--host', default='localhost',
			help='ActiveMQ Server Hostname (default: %(default)s)')
	connection.add_argument('--port', type=int, default=8161,
			help='ActiveMQ Server Port (default: %(default)s)')
	subparsers = parser.add_subparsers()

	# Sub-Parser for queuesize
	parser_queuesize = subparsers.add_parser('queuesize', help='Check QueueSize')
	parser_queuesize.add_argument('-w', '--warn', metavar='WARN', type=int, default=100,
			help='Warning if Queue Size is greater. (default: %(default)s)')
	parser_queuesize.add_argument('-c', '--crit', metavar='CRIT', type=int, default=10,
			help='Critical if Queue Size is greater. (default: %(default)s)')
	parser_queuesize.add_argument('queue', default='',
			help='Name of the Queue that will be checked.')
	parser_queuesize.set_defaults(func=queuesize)

	# Sub-Parser for health
	parser_health = subparsers.add_parser('health', help='Check Health')
	parser_health.set_defaults(func=health)
	# no additional arguments necessary

	# Sub-Parser for subscriber
	parser_subscriber = subparsers.add_parser('subscriber', help='Check Subscriber')
	parser_subscriber.add_argument('--clientId', required=True)
	parser_subscriber.add_argument('--topic', required=True)
	parser_subscriber.set_defaults(func=subscriber)

	# Evaluate Arguments
	args = parser.parse_args()
	print args


if __name__ == '__main__':
	main()


