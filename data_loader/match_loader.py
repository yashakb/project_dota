import sys
import argparse
import logging
import json
import time

import psutil
import pika
from requests.exceptions import RequestException

import dota2api

class MatchLoader(object):
    def __init__(self, api_key, host, username, password, input_queue, output_queue):
        self.init_api(api_key)
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.input_channel, self.input_connection = self.init_channel(username, password, host, input_queue)
        self.output_channel, self.output_connection = self.init_channel(username, password, host, output_queue)
        self.fresh_ids = set()

    def __del__(self):
        try:
            self.input_connection.close()
            self.output_connection.close()
        except AttributeError:
            pass

    def init_api(self, api_key):
        logging.info('initializing api with api key ' + api_key)
        self.api = dota2api.Dota2Api(api_key)

    def init_channel(self, username, password, host_name, queue_name):
        logging.info('initializing channel')
        logging.info('username: ' + username)
        logging.info('password: ' + password)
        logging.info('host: ' + host_name)
        logging.info('queue: ' + queue_name)
        creds = pika.credentials.PlainCredentials(username=username, password=password)
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=host_name, credentials=creds))
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        return channel, connection

    def publish_message(self, message):
        self.output_channel.basic_publish(exchange='', 
            routing_key=self.output_queue,
            body=message,
            properties=pika.BasicProperties(delivery_mode = 2))

    def load_match(self, match_id):
        logging.debug('loading match %d' % match_id)
        match = None
        for trial in xrange(100):
            try:
                match = self.api.getMatchDetails(match_id)['result']
                break
            except RequestException as e:
                logging.error('RequestException handled:')
                logging.error(e)
                logging.info('sleep for 2')
                self.input_connection.sleep(2)
        freshness = time.time() - match['start_time']
        if freshness < 2 * 60 * 60:
            sleep_time = 2 * 60 * 60 - freshness
            logging.debug('sleep for %d seconds' % sleep_time)
            self.input_connection.sleep(sleep_time)
            return self.load_match(match_id)
        return match

    def run(self):
        def callback(ch, method, properties, body):
            body = json.loads(body)
            match = self.load_match(body['match_id'])
            if match != None:
                try:
                    match['skill'] = body['skill']
                    self.publish_message(json.dumps(match))
                except KeyError:
                    logging.error(json.dumps(body))
            opened_files()
            ch.basic_ack(delivery_tag = method.delivery_tag)

        self.input_channel.basic_qos(prefetch_count=10)
        self.input_channel.basic_consume(callback, queue=self.input_queue)
        self.input_channel.start_consuming()

def opened_files():
    for p in psutil.process_iter():
        try:
            if 'python' in p.name().lower():
                logging.debug("opened_files:")
                logging.debug(p.open_files())
        except (psutil.ZombieProcess, psutil.AccessDenied):
            pass

def main():
    # logging init
    logging.basicConfig(format='[%(asctime)s] %(levelname)s %(message)s', 
        datefmt='%Y-%m-%d %H:%M:%S', 
        level=logging.DEBUG)

    # parse arguments
    parser = argparse.ArgumentParser(description='start loading recent matches using steam api',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--api_key', help='api key', required=True)
    parser.add_argument('--host', help='rabbitmq host name', default='romovpa.dev.ydf.yandex.net')
    parser.add_argument('--input_queue', help='input queue name', default='dota_info')
    parser.add_argument('--output_queue', help='output queue name', default='dota_matches')
    parser.add_argument('--username', help='username', default='test')
    parser.add_argument('--password', help='password', default='test')
    args = parser.parse_args()

    while True:
        try:
            # loader init 
            loader = MatchLoader(api_key=args.api_key, host=args.host,
                username=args.username, password=args.password,
                input_queue=args.input_queue, output_queue=args.output_queue)

            loader.run()    
        except Exception as e:
            logging.error(e)
            pass
    
if __name__ == '__main__':
    main()





