import os
import chess
import pymongo
import certifi

player_data_collection_name = 'player_data_v3'
tournaments_collection_name = 'tournaments_v3'
tournament_rules = 'chess'
tournament_time_class = 'daily'
tournament_type = f'{tournament_rules}_{tournament_time_class}'

def extend_tournament_url(tournament_id:str) -> str:
    if 'https://www.chess.com' not in tournament_id:
        tournament_url = 'https://www.chess.com/tournament/' + tournament_id
    else:
        tournament_url = tournament_id

    return tournament_url

def get_request_header():
    header = {'User-Agent': 'dkarr7@gatech.edu'}
    return header

def get_mongodb(database: str):
    """
    Get a MongoDB connection for database
    :param database:
    :return:
    """
    mongo_srv = f'mongodb+srv://dkarr7:UPb1hdBOGnwjmBZd' \
                '@cluster0.vy6kp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
    client = pymongo.MongoClient(mongo_srv, tlsCAFile=certifi.where())
    return client[database]

def get_game_value(player:str, result:str) -> float:
    """
    Returns the value of the game for the player: 1 if they won, 0.5 for a draw and 0 for a loss
    :param player: 'white' or 'black'
    :param result: '1-0' for white win or '0-1' for black win or '1/2-1/2' for draw
    :return: 1.0 if player won, 0.5 for a draw and 0 for a loss
    """
    if result == '1-0':
        score = 1.0
    elif result == '0-1':
        score = 0.0
    elif result == '1/2-1/2':
        score = 0.5
    else:
        assert False, f'ERROR: unrecognized result {result}'

    if player == 'white':
        value = score
    elif player == 'black':
        value = 1.0 - score
    else:
        assert False, f'ERROR: unrecognized player {player}'

    return value

def get_color(color:chess.Color) -> str:
    """
    Returns 'white' if color is chess.WHITE, 'black' otherwise
    :param color: chess.WHITE or chess.BLACK
    :return: str
    """
    if color == chess.WHITE:
        return 'white'
    else:
        return 'black'