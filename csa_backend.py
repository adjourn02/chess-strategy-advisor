# Chess Strategy Advisor Backend
# CSE6242 - Fall 2024

import pandas
from flask import Flask, jsonify, request
import numpy as np
import pandas as pd
from scipy.stats import norm, t
from scipy.interpolate import splrep, BSpline
from csa_lib import *
app = Flask(__name__)

def invert_classification(classification: str) -> str:
    """
    Flips Strength <-> Weakness to correct for the player perspective
    :param classification: Strength, Weakness, or Not-significant
    :return: flipped classification
    """

    if classification == 'Weakness':
        return 'Strength'
    elif classification == 'Strength':
        return 'Weakness'
    else:
        return classification

def smooth_ev_plot(ev_data: dict, x_min: int = 7, x_max: int = 50, s: float = 5.0) -> list:
    """
    Applies BSpline smoothing to the expected score by move data.
    :param ev_data: dict containing the raw data. ev_data[num_moves] = (ev, num_data_points)
    :param x_min: minimum x value in the output data
    :param x_max: maximum x value in the output data
    :param s: smoothing factor for BSpline
    :return: list containing the smoothed waveform
    """

    if len(ev_data) < 5:
        return []

    x = np.zeros(len(ev_data))
    y = np.zeros(len(ev_data))
    for i, (k, v) in enumerate(ev_data.items()):
        x[i] = int(k)
        y[i] = v[0]

    tck_s = splrep(x, y, s=s)
    x_new = np.arange(x_min, x_max, 1)

    # clip values to [0.0 : 1.0]
    y_new = BSpline(*tck_s)(x_new).clip(0.0, 1.0)
    datapoints = zip(x_new.tolist(), y_new.tolist())

    return list(datapoints)


def compare_strategy_single_opponent(df: pandas.DataFrame) -> dict:
    """
    Analyzes the strategy between the player and a single opponent. Applies a two-sample Bernoulli proportions test
    between the player and the opponent's expected score for a given move.
    :param df: dataframe with the columns: ev_player, ev_opponent, count_player, count_opponent
    :return:
    """
    df['difference'] = df['ev_player'] - df['ev_opponent']

    df['pooled_var_est'] = ((df['ev_player'] * df['count_player']) + (df['ev_opponent'] * df['count_opponent'])) / \
        (df['count_player'] + df['count_opponent'])

    df['denominator'] = df['pooled_var_est'] * (1 - df['pooled_var_est']) * (1.0 / df['count_player'] + 1.0 / df['count_opponent'])
    df['Zo'] = df['difference'].abs() / (df['denominator'].pow(0.5))

    df['confidence'] = df.apply(lambda x: norm.cdf(x['Zo']), axis=1)

    # Replace any NaN in 'confidence' with 0
    df['confidence'].fillna(0, inplace=True)

    #print(df.head())
    df_sum = df[['opening', 'difference', 'confidence']].sort_values(by='difference', ascending=False)
    #print(df_sum.head())

    return df_sum.to_dict('records')


def analyze_single_opponent(player_username: str, opponent_username: str, min_games: str = 3) -> dict:
    """
    :param player_username: Chess.com username of the target player
    :param opponent_username: Chess.com username of the opponent player
    :param min_games: Minimum number of games played for opening move analysis
    :returns player_info: dict with information about the player
    """

    results = {
        'username': opponent_username,
        'rating': -1,  # rating of the player
        'rd': -1,  # Glick RD of the player
        'timeout_percent': -1,  # timeout percentage in the last 90 days
        'win': 'UNKNOWN',  # total wins for the user
        'loss': 'UNKNOWN',  # total losses for the user
        'draw': 'UNKNOWN',  # total draws for the user
        'time_per_move': 'UNKNOWN',  # average time per move of the user
        'move_analysis': {
            'Using Castling': 'Not-significant',
            'Using En Passant': 'Not-significant',
            'Against Castling': 'Not-significant',
            'Against En Passant': 'Not-significant',
        },
        'recommended_white': {},
        'recommended_black': {},
        'player_smoothed_values': [],
        'opponent_smoothed_values': [],
    }

    mydb = get_mongodb('player_history')
    history = mydb[player_data_collection_name]

    users = [user for user in history.find({'username': opponent_username})]

    if len(users) == 1:
        opponent = users[0]

        stats = opponent['stats']
        for key in ['rating', 'rd', 'timeout_percent', 'win', 'loss', 'draw', 'time_per_move']:
            results[key] = stats[key]

        analysis = opponent['plays_by_score']

        if analysis['player_castle']['results_available']:
            results['move_analysis']['Using Castling'] = \
                analysis['player_castle']['analysis']['classification']

        if analysis['player_en_passant']['results_available']:
            results['move_analysis']['Using En Passant'] = \
                analysis['player_en_passant']['analysis']['classification']

        if analysis['opponents_castle']['results_available']:
            results['move_analysis']['Against Castling'] = \
                invert_classification(analysis['opponents_castle']['analysis']['classification'])

        if analysis['opponents_en_passant']['results_available']:
            results['move_analysis']['Against En Passant'] = \
                invert_classification(analysis['opponents_en_passant']['analysis']['classification'])

        results['opponent_smoothed_values'] = smooth_ev_plot(opponent['expected_value_by_num_moves'])

        users = [user for user in history.find({'username': player_username})]
        if len(users) == 1:
            player = users[0]

            results['player_smoothed_values'] = smooth_ev_plot(player['expected_value_by_num_moves'])

    return results


def get_opponents_game_length(tournament_id='', player_name='', custom_opponent_list=None):
    """
    :param tournament_id: url-ID of the Chess.com tournament
    :param player_name: name of the player
    :param custom_opponent_list: List of custom opponents to analyze (optional)
    :returns smoothed_values: list of tuples with (move count, smoothed expected value) across move counts
    """

    # Connect to MongoDB and retrieve tournament and player data
    mydb = get_mongodb("player_history")
    players_collection = mydb[player_data_collection_name]

    # Use the provided custom opponent list if available, otherwise retrieve all opponents from the tournament
    if custom_opponent_list is None:
        other_players = retrieve_opponent_data(tournament_id, player_name)
    else:
        other_players = custom_opponent_list

    if isinstance(other_players, dict) and "error" in other_players:
        return other_players  # Return error if tournament is not found

    # Initialize a dictionary to accumulate expected values by move count
    ev_data = {}
    
    for opponent_name in other_players:
        opponent_data = players_collection.find_one({'username': opponent_name})
        if not opponent_data or 'expected_value_by_num_moves' not in opponent_data:
            continue  # Skip if opponent data is missing
        
        ev_by_moves = opponent_data['expected_value_by_num_moves']

        # Collect move counts and expected values
        for move_count_str, (expected_value, count) in ev_by_moves.items():
            move_count = int(move_count_str)  # Convert move count to integer
            if count > 0:
                if move_count not in ev_data:
                    ev_data[move_count] = (0, 0)  # Initialize (total_ev, total_count)
                total_ev, total_count = ev_data[move_count]
                ev_data[move_count] = (total_ev + expected_value * count, total_count + count)

    # Calculate the average expected value for each move count
    for move_count in ev_data:
        total_ev, total_count = ev_data[move_count]
        if total_count > 0:
            ev_data[move_count] = (total_ev / total_count, total_count)

    # Sort 'x' for spline
    ev_data = dict(sorted(ev_data.items()))

    smoothed_values = smooth_ev_plot(ev_data, 7, 50, 1)

    return smoothed_values


# Helper function to extract and filter strategy data for a player
def extract_strategy_data(player_data, color, min_games):
    """
    :param player_data: dict of player's strategy data.
    :param color: color to retrieve strategies for ('white' or 'black').
    :param min_games: min number of games required for a strategy to be included.
    :return: df of filtered strategies with columns ['opening', 'ev', 'count'].
    """
    strategy_key = f'openings_as_{color}'
    strategy_list = [
        {'opening': opening, 'ev': values[1], 'count': values[2]}
        for opening, values in player_data.get(strategy_key, {}).items()
        if isinstance(values, (list, tuple)) and len(values) == 3 and values[2] >= min_games
    ]
    return pd.DataFrame(strategy_list)


def compare_strategies(player_df, opponent_df, color):
    """
    Compares player strategies to opponent strategies per opening using the specified statistical method.
    :param player_df: DataFrame of player's strategies with columns ['opening', 'player_ev', 'player_count'].
    :param opponent_df: DataFrame of opponent strategies with columns ['opening', 'color', 'ev_opponent', 'count_opponent'].
    :param color: Opponent's color to compare ('white' or 'black').
    :return: List of dicts with comparison metrics including 'opening', 'difference', 'confidence'.
    """
    # Filter opponent data for the specified color
    opponent_filtered = opponent_df[opponent_df['color'] == color]

    results = []

    # Iterate over each opening
    for _, player_row in player_df.iterrows():
        opening = player_row['opening']
        EV_p_o = player_row['player_ev']

        # Oopponent data for the same opening
        opponents_opening = opponent_filtered[opponent_filtered['opening'] == opening]
        if opponents_opening.empty:
            #print("Opponents Opening Empty")
            # No opponents for this opening, cannot compute variance
            continue
        
        # Differences
        D_o_p_a_list = [EV_p_o - opp_ev for opp_ev in opponents_opening['ev_opponent']]
        N_o_s = len(D_o_p_a_list)
        EV_a_o_mean = opponents_opening['ev_opponent'].mean()
        difference = EV_p_o - EV_a_o_mean

        if N_o_s < 2:
            # Not enough data to compute variance
            confidence = 0.5
        else:
            # Mean difference
            mean_difference = np.mean(D_o_p_a_list)

            # Variance of differences
            S2_o_p_s = np.var(D_o_p_a_list, ddof=1)

            # t-statistic
            t_stat = (mean_difference * np.sqrt(N_o_s)) / (np.sqrt(S2_o_p_s) + 1e-9)
            df = N_o_s - 1 

            # Calculate p-value
            if t_stat > 0:
                p_value = 1 - t.cdf(t_stat, df=df)
            elif t_stat < 0:
                p_value = t.cdf(t_stat, df=df)
            else:
                p_value = 0.5  # Neutral p-value for t_stat = 0

            # Confidence
            confidence = 1 - p_value

            # Max .99 for frontend display (remove 1.00 confidences)
            if (confidence >= .995):
                confidence = .99

        # Append the result for this opening
        results.append({
            'opening': opening,
            'difference': difference,
            'confidence': confidence
        })

    # Convert results to DataFrame and sort by difference
    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values(by='difference', ascending=False)

    # Return relevant columns sorted by difference
    return result_df.to_dict(orient='records')

# Helper function to retrieve tournament data and filter out the specified player.
def retrieve_opponent_data(tournament_id, player_name):
    """
    :param tournament_id: url-ID of the Chess.com tournament
    :param player_name: name of the player to exclude from the tournament players list
    :returns: a list of other players if successful, or an error dictionary if the tournament is not found
    """
    mydb = get_mongodb("player_history")
    tournaments_collection = mydb[tournaments_collection_name]
    
    # Retrieve the tournament
    tournament = tournaments_collection.find_one({'url': tournament_id})
    if not tournament:
        return {"error": "Tournament not found."}

    # Get tournament players and exclude the specified player
    tournament_players = tournament['players']
    other_players = [player['player'] for player in tournament_players if player['player'] != player_name]
    
    return other_players


def analyze_opponent_strategy(tournament_id='', player_name='', min_games=3, custom_opponent_list=None):
    """
    Analyzes strategies for a given player against a single opponent or a list of opponents.
    :param tournament_id: URL ID of the Chess.com tournament.Get-oppo
    :param player_name: Name of the player to analyze.
    :param min_games: Minimum number of games required for a strategy to be considered.
    :param custom_opponent_list: Optional list of opponents to include in the analysis.
    :return: Dictionary with recommended strategies for both colors.
    """
    strategies = {'recommended_white': [], 'recommended_black': []}

    # Connect to MongoDB and retrieve player data
    mydb = get_mongodb("player_history")
    players_collection = mydb[player_data_collection_name]

    # Use the custom opponent list if provided; otherwise, retrieve all opponents from the tournament
    if custom_opponent_list is None:
        other_players = retrieve_opponent_data(tournament_id, player_name)
    else:
        other_players = custom_opponent_list

    if isinstance(other_players, dict) and "error" in other_players:
        return other_players  # Return error if tournament is not found

    # Gather data for opponent strategies into a DataFrame
    opponent_data_list = []
    for opponent_name in other_players:
        opponent_data = players_collection.find_one({'username': opponent_name})
        if not opponent_data:
            continue

        # Extract strategies for each color
        for color, strategy_key in zip(['black', 'white'], ['openings_as_black', 'openings_as_white']):
            for opening, values in opponent_data.get(strategy_key, {}).items():
                if isinstance(values, (list, tuple)) and len(values) == 3:
                    ev, count = values[1], values[2]
                    opponent_data_list.append({
                        'opening': opening,
                        'color': color,
                        'ev_opponent': ev,
                        'count_opponent': count
                    })

    # Convert opponent data to DataFrame and filter by minimum game count
    opponent_df = pd.DataFrame(opponent_data_list)
    opponent_df = opponent_df[opponent_df['count_opponent'] >= min_games]

    # Retrieve player data and prepare for comparison
    player_data = players_collection.find_one({'username': player_name})
    if not player_data:
        return {"error": "Player data not found."}

    # Analyze and compare strategies for both colors using helper functions
    for color, opponent_color in [('white', 'black'), ('black', 'white')]:
        player_df = extract_strategy_data(player_data, color, min_games)
        player_df = player_df.rename(columns={'ev': 'player_ev', 'count': 'player_count'})

        if player_df.empty:
            strategies[f'recommended_{color}'] = []  # No strategies found for this color
            continue

        # Use the compare_strategies function for multiple opponents
        strategies[f'recommended_{color}'] = compare_strategies(player_df, opponent_df, opponent_color)

    return strategies


@app.route('/tournaments/<tournament_id>/recommended-strategies/<player_name>', methods=['GET', 'POST'])
def get_recommended_strategies(tournament_id, player_name):
    tournament_id = extend_tournament_url(tournament_id)

    # Check if a custom opponent list is provided via GET query parameters (e.g., ?opponents=playerB,playerC,playerD)
    custom_opponent_list = None
    if request.method == 'GET' and 'opponents' in request.args:
        custom_opponent_list = request.args.get('opponents').split(',')
        if not all(custom_opponent_list):  # Validate list content
            return jsonify({'error': 'Invalid opponent list provided'}), 400

    # Handle POST request to allow sending a custom list of opponents in the body
    elif request.method == 'POST':
        request_data = request.get_json()
        if 'opponent_list' not in request_data:
            return jsonify({'error': 'Missing opponent list in the request body'}), 400

        custom_opponent_list = request_data['opponent_list']
        if not isinstance(custom_opponent_list, list):
            return jsonify({'error': 'Opponent list must be an array'}), 400

    strategies = analyze_opponent_strategy(
        tournament_id=tournament_id,
        player_name=player_name,
        custom_opponent_list=custom_opponent_list
    )

    # Check for errors in the analysis result
    if isinstance(strategies, dict) and "error" in strategies:
        return jsonify(strategies), 404 

    # Return as JSON response
    return jsonify(strategies) 


@app.route('/recommended-strategies/<player_name>/<opponent_name>', methods=['GET'])
def get_recommended_strategies_opponent(player_name, opponent_name):
    """
    Analyses the best strategy for an individual opponent. Used for the drill-down view.
    :param player_name: Chess.com username of the player
    :param opponent_name: Chess.com username of the opponent
    :return: dict with the analysis
    """
    oppo_info = analyze_single_opponent(player_name, opponent_name)

    # If an error occurred, return an error response
    if isinstance(oppo_info, dict) and "error" in oppo_info:
        return jsonify(oppo_info), 404

    return jsonify(oppo_info)


@app.route('/tournaments/<tournament_id>/opponent-game-lengths/<player_name>', methods=['GET', 'POST'])
def get_opponents_game_lengths(tournament_id, player_name):
    tournament_id = extend_tournament_url(tournament_id)

    # Handle POST request to allow sending a custom list of opponents in the body
    custom_opponent_list = None
    if request.method == 'POST':
        request_data = request.get_json()
        if not request_data or 'opponent_list' not in request_data:
            return jsonify({'error': 'Missing or invalid opponent list in the request body'}), 400

        custom_opponent_list = request_data['opponent_list']
        if not isinstance(custom_opponent_list, list):
            return jsonify({'error': 'Opponent list must be an array'}), 400

    # Call the function to get smoothed expected values
    smoothed_values = get_opponents_game_length(
        tournament_id=tournament_id,
        player_name=player_name,
        custom_opponent_list=custom_opponent_list
    )

    # If an error occurred, return an error response
    if isinstance(smoothed_values, dict) and "error" in smoothed_values:
        return jsonify(smoothed_values), 404

    # Return the results as JSON
    return jsonify(smoothed_values)

@app.route('/tournaments', methods=['GET'])
def get_tournaments():
    # connect with MongoDB
    mydb = get_mongodb("player_history")
    tournaments_collection = mydb[tournaments_collection_name]

    tournaments = []
    for tournament in tournaments_collection.find():
        tournaments.append({'name': tournament['name'], 'url': tournament['url']})

    tournaments.sort(key=lambda x: x['url'])

    return jsonify(tournaments)

@app.route('/tournaments/<tournament_id>/players', methods=['GET'])
def get_players_in_tournament(tournament_id=''):
    """
    Retrieves the list of player usernames that are registered for the tournament.
    :param tournament_id: url-ID of the tournament
    :return: list of players in registered for the tournament
    """
    # connect with MongoDB
    mydb = get_mongodb("player_history")
    tournaments_collection = mydb[tournaments_collection_name]
    tournament_id = extend_tournament_url(tournament_id)

    tournaments = [t1 for t1 in tournaments_collection.find({'url': tournament_id})]

    if len(tournaments) == 1:

        players = tournaments[0]['players']
        players.sort(key=lambda player: player['player'])

        results = {
            'result': 'SUCCESS',
            'message': f'{len(tournaments)} tournaments found',
            'players': players,
        }
    else:
        results = {
            'result': 'FAILED',
            'message': f'{len(tournaments)} tournaments found',
            'players': []
        }

    return jsonify(results)


@app.route('/tournaments/<player_name>', methods=['GET'])
def get_tournaments_for_player(player_name=''):
    """
    Returns a list of tournament that the player has registered for.
    :param player_name: username of the target player
    :return: list of tournaments
    """
    # connect with MongoDB
    mydb = get_mongodb("player_history")
    tournaments_collection = mydb[tournaments_collection_name]

    tournaments = []
    for tournament in tournaments_collection.find({'players.player': player_name}):
        tournaments.append({'name': tournament['name'], 'url': tournament['url']})

    return jsonify(tournaments)


if __name__ == '__main__':
    print(f"Tournament Collection: {tournaments_collection_name}")
    print(f"Player History Collection: {player_data_collection_name}")
    app.run(debug=True)