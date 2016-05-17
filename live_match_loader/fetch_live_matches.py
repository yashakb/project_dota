#!/usr/bin/env

import json
import argparse
import time
import hashlib
import datetime

import pylru
import dota2api
from requests.exceptions import HTTPError


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch live matches')
    parser.add_argument('--api-key', required=True)
    parser.add_argument('--interval', default=10, type=float)
    parser.add_argument('--output', default='live_league_games.jsonlines')
    args = parser.parse_args()
    
    api = dota2api.Dota2Api(args.api_key)
    cache = pylru.lrucache(10000)
    while True:
        
        try:
            games = api.makeRequest('GetLiveLeagueGames')['result']['games']
            request_timestamp = time.mktime(datetime.datetime.utcnow())
            
            output_lines = []
            for game in games:
                game_line = json.dumps(game, separators=(',', ':'))
                game_line_hash = int(hashlib.md5(game_line).hexdigest()[:8], 16)

                game['_timestamp'] = request_timestamp
                game_line = json.dumps(game, separators=(',', ':'))

                if game_line_hash not in cache:
                    cache[game_line_hash] = True
                    output_lines.append(game_line)
                    
            with open(args.output, 'a') as fout:
                for line in output_lines:
                    fout.write(line + '\n')
                    
            print datetime.datetime.now(), 'Fetched %d, saved %d' % (len(games), len(output_lines))
            
        except HTTPError as e:
            print e
            time.sleep(2)
            continue

        except KeyboardInterrupt:
            print 'Stopped'
            break

        except Exception as e:
            print 'Unknown exception:', e
            time.sleep(2)
            continue
            
        time.sleep(args.interval)
            