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


