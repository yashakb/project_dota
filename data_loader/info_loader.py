import sys
import argparse
import logging
import json
import time

import pylru
import pika
from requests.exceptions import RequestException

import dota2api

class InfoLoader(object):
    def __init__(self, api_key, host, username, password, queue):
        self.init_api(api_key)
        self.queue = queue
        self.channel, self.connection = self.init_channel(username, password, host, queue)
        self.init_cache(100000)
        self.load_heroes('data/heroes.json')
        self.load_skills()
        self.load_modes()

    def __del__(self):
        try:
            self.connection.close()
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

    def init_cache(self, size):
        self.cache = pylru.lrucache(size)

    def load_heroes(self, filename):
        logging.debug('loading heroes from ' + filename)
        with open(filename, 'r') as thefile:
            self.heroes = json.load(thefile)['heroes']

    def load_skills(self):
        self.player_skills = [(1, 'Normal'), (2, 'High'), (3, 'Very High')]

    def load_modes(self):
        self.game_modes = [2, 22]

    def publish_message(self, message):
        self.channel.basic_publish(exchange='', 
            routing_key=self.queue,
            body=message,
            properties=pika.BasicProperties(delivery_mode = 2))

    def load_info(self, skill, hero, mode):
        last_id = None
        matches = []
        while True:
            response = None
            if last_id == None:
                for trial in xrange(100):
                    try:
                        response = self.api.getMatchHistory(skill=skill, 
                            hero_id=hero, 
                            min_players=10, 
                            game_mode=mode,
                            matches_requested=100)
                        break
                    except RequestException as e:
                        logging.error('RequestException handled:')
                        logging.error(e)
                        logging.info('sleep for 2')
                        self.connection.sleep(2)
            else:
                for trial in xrange(100):
                    try:
                        response = self.api.getMatchHistory(skill=skill, 
                            hero_id=hero, 
                            min_players=10, 
                            game_mode=mode,
                            matches_requested=100, 
                            start_at_match_id=last_id)
                        break
                    except RequestException:
                        logging.error('RequestException handled:')
                        logging.error(e)
                        logging.info('sleep for 2')
                        self.connection.sleep(2)
            response = response['result']
            if response['status'] != 1:
                raise Exception('Status indicates error')
            n, remaining = response['num_results'], response['results_remaining']
            if n == 0:
                break
            last_id = response['matches'][-1]['match_id']
            matches.extend(response['matches'])
            if remaining == 0:
                break
        matches = filter(lambda match: match['lobby_type'] == 7, matches)
        matches = filter(lambda match: match['match_id'] not in self.cache, matches)
        for match in matches:
            self.cache[match['match_id']] = True
        return matches

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
    parser.add_argument('--queue', help='queue name', default='dota_info')
    parser.add_argument('--username', help='username', default='test')
    parser.add_argument('--password', help='password', default='test')
    args = parser.parse_args()

    # run
    while True:
        try:
            loader = InfoLoader(api_key=args.api_key, host=args.host,
                username=args.username, password=args.password, queue=args.queue)
            for hero in loader.heroes:
                for skill in loader.player_skills:
                    for mode in loader.game_modes:
                        logging.info('seeking for hero:%d, skill:%d, mode:%d' % (hero['id'], skill[0], mode))
                        matches = loader.load_info(skill[0], hero['id'], mode)
                        for match in matches:
                            message = {
                                'skill': skill, 
                                'match_id': match['match_id'],
                            }
                            payload = json.dumps(message, separators=(',', ':'))
                            loader.publish_message(payload)
        except Exception as e:
            logging.error(e)
            pass

if __name__ == '__main__':
    main()
