import sys
from bs4 import BeautifulSoup
import requests
from csa_lib import *

MAX_NUM_TOURNAMENTS = 50
MAX_NUM_PLAYERS_IN_TOURNAMENT = 150
MIN_NUMBER_PLAYERS_IN_TOURNAMENT = 5

def get_request_header() -> dict:
    """
    :return: header to auth with Chess.com
    """
    header = {'User-Agent': os.getenv('USER_AGENT')}
    return header

if __name__ == "__main__":

    # get games collection from the player_history database
    mydb = get_mongodb('player_history')
    my_collection = mydb[tournaments_collection_name]
    print(mydb.list_collection_names())

    page_num = 1
    tournaments = []

    while 0 < page_num <= 200: # algo should terminate on it's own but set a backstop of 200 to be safe

        # get the current page number
        url = f'https://www.chess.com/tournaments?&page={page_num}'
        r = requests.get(url)

        # check status code for response received
        assert r.status_code == 200, f'Get {url} failed'

        # make some soup
        soup = BeautifulSoup(r.content, "html.parser")

        # extract the tournament table data containers
        results = soup.find_all('div', class_='tournaments-table-full-td-container')

        tournaments_found = 0
        for result in results:
            tournaments_found += 1
            chess_icon = result.find('span', class_='chess-board')

            # the chess-board icon indicates the tournament has standard chess rules, ignore the rest
            if chess_icon is not None:
                link = result.find('a', class_='tournaments-table-full-td-link')
                tournaments.append(link['href'])

                title = result.find('div', class_='tournaments-table-tournament-title').text.strip()
                url = link['href']

                # retrieve data about the Tournament via the API
                api_url = url.replace('https://www.chess.com/tournament', ' https://api.chess.com/pub/tournament')
                r = requests.get(api_url, headers=get_request_header())

                assert r.status_code == 200, f'Error fetching Tournament data {api_url}, status code = {r.status_code}'
                data = r.json()
                players = [player['username'] for player in data['players']]

                if len(players) > MAX_NUM_PLAYERS_IN_TOURNAMENT:
                    print(f'Skipping tournament {title} because it has too many players.')
                    continue

                rules = data['settings']['rules']
                time_class = data['settings']['time_class']

                if rules != tournament_rules or time_class != tournament_time_class:
                    print(f'Skipping tournament {title} with {rules} rules and {time_class} time class.')
                    continue

                player_info = []
                for player in players:
                    player_url = f'https://api.chess.com/pub/player/{player}/stats'
                    r = requests.get(player_url, headers=get_request_header())

                    assert r.status_code == 200, f'Failed to retrieve stats for player {player}, status code: {r.status_code}'
                    data = r.json()

                    # ignore players without a profile
                    if tournament_type in data.keys():
                        dat = data[tournament_type]
                        player_info.append({'player': player, 'rating': dat['last'].get('rating')})

                if len(player_info) < MIN_NUMBER_PLAYERS_IN_TOURNAMENT:
                    print(f'Skipping tournament {title} because there are too few players.')
                    continue

                # check if the tournament is already in the database
                if my_collection.count_documents({'url': url}) == 0:
                    x = my_collection.insert_one({'name': title, 'url': url, 'players': player_info})
                    print(f'Tournament "{title}" inserted at {x.inserted_id}')

                    if my_collection.count_documents({}) >= MAX_NUM_TOURNAMENTS:
                        print(f'Stopping, reached the max number of tournaments to insert: {MAX_NUM_TOURNAMENTS}')
                        sys.exit(0)
                else:
                    print(f'Tournament {url} is already in the database')

        # check the next page if we found at least one tournament
        if tournaments_found > 0:
            page_num += 1
        else:
            page_num = 0 # exit the loop

    sys.exit()
