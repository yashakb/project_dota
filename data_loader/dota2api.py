"""
Tools for accessing the Dota 2 match history web API
"""

from functools import wraps
import requests
import logging
import json
import time

BASE_URL = "http://api.steampowered.com/IDOTA2Match_570/"

class Dota2Api(object):
    def __init__(self, key):
        self.API_KEY = key
        self.logger = logging.getLogger("dota2api")

    def loadPage(self, url):
        self.logger.debug('GET %s' % url)
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response

    def makeRequest(self, name, version='V001', language='en_us', **kwargs):
        url = '%s%s/%s/' % (BASE_URL, name, version)
        url += '?'

        parameters = kwargs
        parameters['key'] = self.API_KEY
        tags = []
        for name, value in parameters.items():
            if value != None:
                tags.append('%s=%s' % (str(name), str(value)))
        url += '&'.join(tags)

        response = self.loadPage(url)
        return json.loads(response.content.decode('utf-8'))

    def getMatchHistory(self, **kwargs):
        """
        Used to get a list of matches played.

        Attribures:
        hero_id=<id>                   # Search for matches with a specific hero being played (hero ID, not name, see HEROES below)
        game_mode=<mode>               # Search for matches of a given mode (see below)
        skill=<skill>                  # 0 for any, 1 for normal, 2 for high, 3 for very high skill (default is 0)
        min_players=<count>            # the minimum number of players required in the match
        account_id=<id>                # Search for all matches for the given user (32-bit or 64-bit steam ID)
        league_id=<id>                 # matches for a particular league
        start_at_match_id=<id>         # Start the search at the indicated match id, descending
        matches_requested=<n>          # Maximum is 25 matches (default is 25)
        tournament_games_only=<string> # set to only show tournament games
        """
        return self.makeRequest('GetMatchHistory', **kwargs)

    def getMatchDetails(self, match_id):
        """
        Used to get detailed information about a specified match.

        Attributes:
        match_id=<id> # the match's ID
        """
        return self.makeRequest('GetMatchDetails', match_id=match_id)
