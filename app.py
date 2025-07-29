# Chess Strategy Advisor Frontend
# CSE6242 - Fall 2024

from flask import Flask, render_template, request, redirect, url_for
import requests

## declare global variables
tournament_id = ""
player_name = ""
players_data = []
opponent_all = []
elo_opponent_all = []

app = Flask(__name__)

## index page
@app.route("/", methods=["GET", "POST"])
def index():
    ## declare global variables
    global tournament_id
    global players_data
    global player_name

    ## load tournament URLs
    tournament_data = requests.get('http://127.0.0.1:5000/tournaments').json()
    tournament_names = [t["name"] for t in tournament_data]

    if request.method == "POST":
        ## show players in tournament
        if "tournament_name" in request.form:
            ## get tournament name
            tournament_name = request.form.get("tournament_name")

            ## get tournament URL
            tournament_url = None
            for tournament in tournament_data:
                if tournament['name'] == tournament_name:
                    tournament_url = tournament['url']
            tournament_id = tournament_url.split('/')[-1]

            ## get tournament ID
            json_data = requests.get(f'http://127.0.0.1:5000/tournaments/{tournament_id}/players').json()
            players_data = json_data['players']
            player_names = [p['player'] for p in players_data]

            return render_template('index.html',
                                   tournament_name=tournament_name,
                                   tournament_names=tournament_names,
                                   names=player_names)

        ## show opponent stats and strategies
        elif "player_name" in request.form:
            ## get chosen player
            player_name = request.form.get("player_name")

            return redirect(url_for('player', player_name=player_name))

    return render_template('index.html', tournament_names=tournament_names)

## recommended player strategies page
@app.route("/player/<player_name>", methods=["GET","POST"])
def player(player_name):
    ## declare global variables
    global opponent_all
    global elo_opponent_all

    ## get all oppoenents
    opponent_all = {'opponent_list': [p['player'] for p in players_data if p['player'] != player_name]}
    elo_opponent_all = sorted([(p['player'], p['rating']) for p in players_data],
                         key=lambda x: x[1])

    return render_template('opponent_info.html', player_name=player_name)

@app.route('/data', methods=["GET"])
def data():
    global elo_opponent_all

    ## define data to pass to D3
    strategy_data_dict = {'opponents':[],
                          'all_smoothed_values': None,
                          'player_smoothed_values':None,
                          'top10_smoothed_values': None,
                          'bot10_smoothed_values': None}

    ## get opponents info
    for i, opponent_name in enumerate(opponent_all['opponent_list']):
        opp_strategy_data = requests.get(f"http://127.0.0.1:5000/recommended-strategies/{player_name}/{opponent_name}").json()
        if i == 0:
            strategy_data_dict['player_smoothed_values'] = opp_strategy_data['player_smoothed_values']
        strategy_data_dict['opponents'].append(opp_strategy_data)

    ## get smoothed values for all opponents
    smoothed_vals = requests.get(f"http://127.0.0.1:5000/tournaments/{tournament_id}/opponent-game-lengths/{player_name}").json()
    strategy_data_dict['all_smoothed_values'] = smoothed_vals

    ## get elo of all opponents
    elo_opponent_all = sorted([(p['username'], p['rating']) for p in strategy_data_dict['opponents']], key=lambda x: x[1])

    ## get EV for top10 and bottom10 opponents
    elo_opp_top10 = {'opponent_list': [p[0] for p in elo_opponent_all[-10:]]}
    elo_opp_bot10 = {'opponent_list': [p[0] for p in elo_opponent_all[:10]]}

    strategy_data_dict['top10_smoothed_values'] = \
        (requests.post(f'http://127.0.0.1:5000/tournaments/{tournament_id}/opponent-game-lengths/{player_name}',
        json=elo_opp_top10).json())

    strategy_data_dict['bot10_smoothed_values'] = \
        (requests.post(f'http://127.0.0.1:5000/tournaments/{tournament_id}/opponent-game-lengths/{player_name}',
        json=elo_opp_bot10).json())

    return strategy_data_dict

@app.route('/strategy', methods=["GET"])
def recommended_strategy():
    opening_strategy_dict = {'agg_strategy': None,
                             'top25_agg_strategy': None,
                             'top10_agg_strategy': None,
                             'bot10_agg_strategy': None}

    strategy_data = requests.get(f"http://127.0.0.1:5000/tournaments/{tournament_id}/recommended-strategies/{player_name}").json()

    opening_strategy_dict['agg_strategy'] = strategy_data

    if len(elo_opponent_all) >= 25:
        elo_opp_top25 = {'opponent_list': [p[0] for p in elo_opponent_all[-25:]]}
        elo_opp_top10 = {'opponent_list': [p[0] for p in elo_opponent_all[-10:]]}
        elo_opp_bot10 = {'opponent_list': [p[0] for p in elo_opponent_all[:10]]}
    elif len(elo_opponent_all) >= 10 or len(elo_opponent_all) < 25:
        elo_opp_top25 = {'opponent_list': [p[0] for p in elo_opponent_all]}
        elo_opp_top10 = {'opponent_list': [p[0] for p in elo_opponent_all[-10:]]}
        elo_opp_bot10 = {'opponent_list': [p[0] for p in elo_opponent_all[:10]]}
    else:
        elo_opp_top25 = {'opponent_list': [p[0] for p in elo_opponent_all]}
        elo_opp_top10 = {'opponent_list': [p[0] for p in elo_opponent_all]}
        elo_opp_bot10 = {'opponent_list': [p[0] for p in elo_opponent_all]}

    opening_strategy_dict['top10_agg_strategy'] = (requests.post(f'http://127.0.0.1:5000/tournaments/{tournament_id}/recommended-strategies/{player_name}',
                           json=elo_opp_top10).json())
    opening_strategy_dict['bot10_agg_strategy'] = (requests.post(f'http://127.0.0.1:5000/tournaments/{tournament_id}/recommended-strategies/{player_name}',
                           json=elo_opp_bot10).json())
    opening_strategy_dict['top25_agg_strategy'] = (requests.post(f'http://127.0.0.1:5000/tournaments/{tournament_id}/recommended-strategies/{player_name}',
                           json=elo_opp_top25).json())

    return opening_strategy_dict

if __name__ == '__main__':
    app.run(port=8000)