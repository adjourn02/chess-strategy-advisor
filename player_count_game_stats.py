from csa_lib import *

if __name__ == "__main__":

    # get games collection from the player_history database
    mydb = get_mongodb('player_history')
    col = player_data_collection_name
    player_data = mydb[col]

    total_num_players = 0
    total_num_games = 0

    for player in player_data.find(projection=['username', 'openings_as_white', 'openings_as_black']):
        num_games = 0
        total_num_players += 1

        for opening in player['openings_as_white'].keys():
            num_games += player['openings_as_white'][opening][2]

        for opening in player['openings_as_black'].keys():
            num_games += player['openings_as_black'][opening][2]

        total_num_games += num_games
        print(f'{player["username"]} played {num_games}')

    print(f'{total_num_games} games analyzed from {total_num_players} players')
