import pandas as pd
from csa_lib import *

def get_results(game:dict, type:str, oa_type:str = '') -> list:
    sa = game['plays_by_score']
    oa = game['plays_by_outcome']

    if len(oa_type) == 0:
        oa_type = type

    results = [
        None if not sa['player_castle']['results_available'] else sa['player_castle']['analysis'][type],
        None if not sa['player_en_passant']['results_available'] else sa['player_en_passant']['analysis'][type],
        None if not sa['opponents_castle']['results_available'] else sa['opponents_castle']['analysis'][type],
        None if not sa['opponents_en_passant']['results_available'] else sa['opponents_en_passant']['analysis'][type],
        None if not oa['results_available'] else oa['analysis']['player_castle'][oa_type],
        None if not oa['results_available'] else oa['analysis']['player_en_passant'][oa_type],
        None if not oa['results_available'] else oa['analysis']['opponents_castle'][oa_type],
        None if not oa['results_available'] else oa['analysis']['opponents_en_passant'][oa_type],
    ]
    return results

if __name__ == "__main__":

    # get games collection from the player_history database
    mydb = get_mongodb('player_history')
    col = player_data_collection_name
    games_collection = mydb[col]
    by_field = 'classification'

    summary = pd.DataFrame(columns=['username',
                                    'score_player_castle',
                                    'score_player_en_passant',
                                    'score_opponents_castle',
                                    'score_opponents_en_passant',
                                    'outcome_player_castle',
                                    'outcome_player_en_passant',
                                    'outcome_opponents_castle',
                                    'outcome_opponents_en_passant',
                                    ])

    for game in games_collection.find(projection=['username', 'plays_by_outcome', 'plays_by_score']):
        row = [game['username']]
        row.extend(get_results(game, type=by_field))
        summary.loc[len(summary)] = row

    summary.to_csv(f'./data/special_move_analysis_by_{by_field}_{col}.csv')
    print('Fin!')