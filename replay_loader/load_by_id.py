import json
import urllib
import argparse
import os
import bz2
import time
from copy import deepcopy

import requests
import pandas as pd

def get_url(match_id):
    try:
        response = requests.get('https://yasp.co/matches/%s?json=1' % match_id)
        match_info = json.loads(response.content)
        url = match_info['url']
    except ValueError as e:
        print e
        print response.content
    return url

def main():
    parser = argparse.ArgumentParser(description='load single replay by match id', 
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--match_id', help='match id', required=True)
    args = parser.parse_args()
    match_id = args.match_id

    url = get_url(match_id)
    filepath = '%s.dem.bz2' % (match_id)
    replay_file = urllib.URLopener()
    replay_file.retrieve(url, filepath)
    with open(filepath[:-4], 'wb') as the_file, bz2.BZ2File(filepath, 'rb') as compressed_f:
        for data in iter(lambda : compressed_f.read(100 * 1024), b''):
            the_file.write(data)

if __name__ == "__main__":
    main()
