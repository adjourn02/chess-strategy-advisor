import sys
import re
import csv
import requests
from collections import defaultdict
from datetime import datetime
from game_analysis import GameAnalysis
from csa_lib import *

# constants used to configure the script
MAX_GAME_COUNT_PER_PLAYER = 500
MIN_NUMBER_MOVES_PER_GAME = 7
MAX_HISTORY_IN_YEARS = 3

# regex patterns used to extract data from game objects
pat_id = re.compile(r'https:.*\/(\d+)', re.IGNORECASE)
pat_eco = re.compile(r'https:.*\/(\S+)$', re.IGNORECASE)
pat_clk = re.compile(r'\s+{[^}]*}\s+(\d+\.\.\.\s)?', re.IGNORECASE)
pat_eco_code = re.compile(r'\[ECO \"([A-E]\d{2})\"\]', re.IGNORECASE)
pat_moves = re.compile(r'^(1\.\s.*)$', re.IGNORECASE + re.MULTILINE)
pat_move_idx = re.compile(r'(\d+)\.')
pat_result = re.compile(r'\[Result \"(.{3,7})\"]', re.IGNORECASE)
pat_tournament = re.compile(r'https:.*\/tournament\/(.*)$', re.IGNORECASE)
pat_year_month = re.compile(r'https:.*\/games\/(\d{4})\/(\d{2})', re.IGNORECASE)

# variable used to store summary stats
total_number_games = 0
total_number_of_draws = 0
total_number_players = 0
total_moves_significantly_pos = {'player_castle': 0, 'player_en_passant' : 0, 'opponents_castle' : 0, 'opponents_en_passant' : 0}
total_moves_significantly_neg = {'player_castle': 0, 'player_en_passant' : 0, 'opponents_castle' : 0, 'opponents_en_passant' : 0}

def format_player_data(in_player:dict) -> dict:
    """
    Returns only the username and rating
    :param in_player: dict of player attributes
    :return: dict with only the player's username and rating
    """
    return {
        'username': in_player['username'],
        'rating': in_player['rating'],
    }

def extract_match(pat, text, default_value = None) -> str:
    """
    Extracts the matched value in text for regex pattern pat
    :param pat: regex pattern
    :param text: text to match
    :param default_value: if specified return this value if a match is not found
    :return: returns the match if found, default_value is specified and not found, text otherwise
    """
    m1 = re.search(pat, text)
    if m1 is None:
        assert default_value is not None, f'ERROR parsing: {text}'
        result = default_value
    else:
        result = m1.group(1)

    return result

def format_game_data(in_data:dict) -> dict:
    """
    Formats and reduces the size of game data
    :param in_data: dict formated per: https://www.chess.com/news/view/published-data-api#pubapi-endpoint-games
    :return: dict
    """

    # some games do not contain, skip them because there is nothing to analyze
    if 'pgn' not in in_data.keys():
        return {'num_moves': 0, 'moves': ''}

    # extract the moves from the pgn
    moves = extract_match(pat_moves, in_data['pgn'], '')

    # remove the {[%clk 0:00:59.9]} 1... data
    moves = re.sub(pat_clk, ' ', moves)

    # number of moves is the number of cases that match " \d+\."
    m1 = re.findall(pat_move_idx, moves)
    num_moves = len(m1)

    out_data = {
        'id': int(extract_match(pat_id, in_data['url'])),
        'white': format_player_data(in_data['white']),
        'black': format_player_data(in_data['black']),
        'eco_code': extract_match(pat_eco_code, in_data['pgn']),
        'moves': moves,
        'result': extract_match(pat_result, in_data['pgn']),
        'num_moves': num_moves,
    }
    return out_data

if __name__ == "__main__":

    # get games collection from the player_history database
    mydb = get_mongodb('player_history')
    games_collection = mydb[player_data_collection_name]
    tournaments_collection = mydb[tournaments_collection_name]
    print(mydb.list_collection_names())

    players_info = [] # list of players being explored in the current round
    players_examined = [] # list of players that have been explored
    current_time = datetime.now()

    # build a look-up table of ECO code to fields
    eco_lut = {}
    with open('./data/eco_code_table.csv') as csvfile:
        r = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in r:
            eco_lut[row[0]] = {
                'name': row[1],
                'moves': row[2],
                'short_name': row[3]
            }

    ga = GameAnalysis()

    for tournament in tournaments_collection.find():

        # retrieve information about the target tournament
        url = tournament['url'].replace('https://www.chess.com/tournament', ' https://api.chess.com/pub/tournament')
        players_info = tournament['players']

        print(f'Exploring tournament {tournament["name"]} with {len(players_info)} registered players')

        for player_info in players_info:

            player = player_info['player']
            # check if the player is already in the collection, if so skip them
            if games_collection.count_documents({'username': player}) > 0:
                print(f'Skipping player {player}')
                continue

            print(f'Examining player {player}')
            players_examined.append(player.lower())

            # get the history of games for the player, which is grouped by month
            url = f'https://api.chess.com/pub/player/{player}/stats'
            r = requests.get(url, headers=get_request_header())

            assert r.status_code == 200, f'Failed to retrieve stats for player {player}, status code: {r.status_code}'
            data = r.json()

            player_stats = {
                'rating': {player_info['rating']},  # rating of the player
                'rd': -1,  # Glick RD of the player
                'timeout_percent': -1,  # timeout percentage in the last 90 days
                'win': 'UNKNOWN',  # total wins for the user
                'loss': 'UNKNOWN',  # total losses for the user
                'draw': 'UNKNOWN',  # total draws for the user
                'time_per_move': 'UNKNOWN',  # average time per move of the user
            }

            dat = None
            if tournament_type in data.keys():
                dat = data[tournament_type]
            elif 'chess_rapid' in data.keys():
                dat = data['chess_rapid']
            elif 'chess_bullet' in data.keys():
                dat = data['chess_bullet']
            elif 'chess_blitz' in data.keys():
                dat = data['chess_blitz']
            else:
                assert False, f'Stats for {player} not found: {data}'

            if 'last' in dat.keys():
                player_stats['rating'] = dat['last'].get('rating')
                player_stats['rd'] = dat['last'].get('rd')

            if 'record' in dat.keys():
                player_stats['timeout_percent'] = dat['record'].get('timeout_percent')
                player_stats['win'] = dat['record'].get('win')
                player_stats['loss'] = dat['record'].get('loss')
                player_stats['draw'] = dat['record'].get('draw')
                player_stats['time_per_move'] = dat['record'].get('time_per_move')

            # get the history of games for the player, which is grouped by month
            url = f'https://api.chess.com/pub/player/{player}/games/archives'
            r = requests.get(url, headers=get_request_header())

            if r.status_code == 200:  # success
                data = r.json()
                archives = data['archives']

                # declare objects that will be used to capture the player data
                games = []
                opening_stats = {}
                expected_value = {}
                total_value_by_moves = defaultdict(float)
                count_value_by_move = defaultdict(int)

                start_pos = ['white', 'black']
                for start in start_pos:
                    opening_stats[start] = defaultdict(int)
                    expected_value[start] = defaultdict(float)

                # iterate over the monthly archives, starting with the most recent
                for i, url in reversed(list(enumerate(archives))):

                    m = re.match(pat_year_month, url)
                    assert m is not None, f'ERROR extracting year and month from: {url}'
                    time_delta = current_time - datetime(int(m.group(1)), int(m.group(2)), 1)
                    if time_delta.days > (365 * MAX_HISTORY_IN_YEARS):
                        print(f'Reached max history of {MAX_HISTORY_IN_YEARS} years for player {player}')
                        break

                    print(f'Examining {url}')
                    r = requests.get(url, headers=get_request_header())
                    if r.status_code == 200:  # success
                        data = r.json()

                        for game in data['games']:
                            # check that the rules for this game match our target and initial_setup is empty (std chess)
                            #   if not ignore this game
                            if (game['rules'] == tournament_rules) and (len(game['initial_setup']) == 0):

                                # formatted_game is a more compact version of game
                                formated_game = format_game_data(game)

                                # skip games that don't have the minimum number of moves
                                if formated_game['num_moves'] < MIN_NUMBER_MOVES_PER_GAME:
                                    continue

                                # get the short name for the ECO code from the LUT
                                short_name = eco_lut[formated_game['eco_code']]['short_name']

                                # determine if the target player played as white or black
                                if player.lower() == game['white']['username'].lower():
                                    played_as = 'white'
                                elif player.lower() == game['black']['username'].lower():
                                    played_as = 'black'
                                else:
                                    assert False, f'Unrecognized player {player}'

                                # tally values that will be used to generate summary stats
                                game_value = get_game_value(played_as, formated_game['result'])
                                opening_stats[played_as][short_name] += 1
                                expected_value[played_as][short_name] += game_value
                                total_value_by_moves[formated_game['num_moves']] += game_value
                                count_value_by_move[formated_game['num_moves']] += 1

                                # push the formatted_game to the end of the list
                                games.append(formated_game)

                                # update summary stats
                                total_number_games += 1

                                if formated_game['result'] == '1/2-1/2':
                                    total_number_of_draws += 1

                            # stop when we've hit the desired number of games
                            if len(games) >= MAX_GAME_COUNT_PER_PLAYER:
                                break

                    # stop when we've hit the desired number of games
                    if len(games) >= MAX_GAME_COUNT_PER_PLAYER:
                        break

                # calculate summary stats for the target player
                sorted_summary = {}
                for start in start_pos:
                    # total number of games played
                    total = sum(opening_stats[start].values())

                    # calculate the fraction of the total for each opening type and the expected value
                    opening_summary = {}
                    for key in opening_stats[start].keys():
                        opening_summary[key] = (
                                                float(opening_stats[start][key]) / total,
                                                expected_value[start][key] / opening_stats[start][key],
                                                opening_stats[start][key],
                                                )

                    # sort by how often the player used each opening
                    sorted_summary[start] = dict(sorted(opening_summary.items(), key=lambda v: (-v[1][0], v[0])))

                # calculate the expected value by move, then sort it by move number
                expected_value_by_move = {}
                for key in count_value_by_move.keys():
                    expected_value_by_move[int(key)] = (total_value_by_moves[key] / count_value_by_move[key], count_value_by_move[key])
                expected_value_by_move = dict(sorted(expected_value_by_move.items(), key=lambda v: v[0]))

                # convert the move number to a str to make mongodb happy
                expected_value_by_move = { str(key): expected_value_by_move[key] for key in expected_value_by_move.keys()}

                outcome_impact, score_impact = ga.analyze_games(player, games)

                # build a dict with data on the player
                mydict = {'username': player,
                          #'games': games,
                          'stats': player_stats,
                          'openings_as_white': sorted_summary['white'],
                          'openings_as_black': sorted_summary['black'],
                          'expected_value_by_num_moves': expected_value_by_move,
                          'plays_by_outcome': outcome_impact,
                          'plays_by_score': score_impact,
                }
                total_number_players += 1
                if outcome_impact['results_available']:
                    for key in total_moves_significantly_pos.keys():
                        if outcome_impact['analysis'][key]['p-value'] < 0.05:
                            if outcome_impact['analysis'][key]['coefficient'] > 0.0:
                                total_moves_significantly_pos[key] += 1
                            else:
                                total_moves_significantly_neg[key] += 1

                # push the player data to MongoDB
                x = games_collection.insert_one(mydict)
                print(f'Player: {player} has {len(games)} games, inserted at {x.inserted_id}')
            else:
                print(f'Error retrieve game data for player: {player}')

    print(f'Processed {total_number_games} games. There were {total_number_of_draws} draws')
    print(f'Total number of players: {total_number_players}')
    print(f'Significantly positive move stats:')
    print(total_moves_significantly_pos)
    print(f'Significantly negative move stats:')
    print(total_moves_significantly_neg)
    sys.exit()