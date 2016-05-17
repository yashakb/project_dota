import json
import urllib
import argparse
import os
import bz2
import time
from copy import deepcopy

import requests
import pandas as pd

def load_replay_urls(team_name):
    df = pd.read_csv(team_name + '.csv')
    urls = []
    for match_id in df['match_link/_text']:
        try:
            response = requests.get('https://yasp.co/matches/%d?json=1' % match_id)
            match_info = json.loads(response.content)
            urls.append({'match_id': match_id, 'replay_url': match_info['url']})
        except ValueError as e:
            print e
            print response.content
    pd.DataFrame(urls).to_csv('%s_replays/%s_replay_urls.csv' % (team_name, team_name))
    return urls

def main():
    parser = argparse.ArgumentParser(description='load replays', 
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--team_name', help='team name', required=True)
    parser.add_argument('--n_matches', help='number of matches to download', required=True)
    args = parser.parse_args()
    team_name = args.team_name
    n_matches = int(args.n_matches)
    os.system('mkdir %s_replays' % team_name)


    incomplete_urls = load_replay_urls(team_name)
    if n_matches > len(incomplete_urls):
        raise ValueError('we have only %d urls' % len(incomplete_urls))
    buf = []
    n_success = 0
    while n_success < n_matches:
        for match_url in incomplete_urls:
            try:    
                filepath = '%s_replays/%d.dem.bz2' % (team_name, match_url['match_id'])

                replay_file = urllib.URLopener()
                replay_file.retrieve(match_url['replay_url'], filepath)
                with open(filepath[:-4], 'wb') as the_file, bz2.BZ2File(filepath, 'rb') as compressed_f:
                    for data in iter(lambda : compressed_f.read(100 * 1024), b''):
                        the_file.write(data)    
                n_success += 1
                print 'loaded %d/%d' % (n_success, n_matches)
                if n_success == n_matches:
                    break
            except Exception as e:
                buf.append(match_url)
                print e
        incomplete_urls = deepcopy(buf)
        buf = []

if __name__ == "__main__":
    main()
