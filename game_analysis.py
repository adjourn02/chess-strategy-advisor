import io
import os
import chess.engine
import chess.pgn
import pandas as pd
import numpy as np
import logging
from csa_lib import get_game_value
from statsmodels.genmod.generalized_linear_model import GLM
from statsmodels.genmod import families
from scipy.stats import ttest_1samp


class GameAnalysis:
    def __init__(self, debug = False):
        # delay to evaluate to the position of moves
        self.NUM_MOVES_DELAY = 3
        self.CONFIDENCE_LEVEL = 0.90
        self.MAX_ANALYSE_TIME = 0.10

        self.engine = chess.engine.SimpleEngine.popen_uci(os.getenv('STOCKFISH_PATH'))
        self.debug = debug

        logging.getLogger("chess.pgn").setLevel(logging.CRITICAL)


    @staticmethod
    def relative_score(current, baseline):
        """
        Returns the relative score between current and baseline, mates are considered 100k centipawns
        :param current: POVScore object for the current board position
        :param baseline: POVScore object when the snapshot was taken
        :return:
        """
        if current.is_mate():
            delta = 1000
        else:
            delta = current.relative.cp - baseline.relative.cp
        return delta

    def analyze_games(self, target_player: str, games: list) -> tuple:

        if self.debug:
            print(f'Processing player {target_player}')

        players = ['player', 'opponents']
        special_moves = ['castle', 'en_passant']
        colors = [chess.WHITE, chess.BLACK]
        move_utility = {move: {player: [] for player in players} for move in special_moves}

        game_stats = pd.DataFrame(columns=['Score',
                                           'Elo_Diff',
                                           'player_castle',
                                           'player_en_passant',
                                           'opponents_castle',
                                           'opponents_en_passant'])

        for i, game_data in enumerate(games):

            if self.debug:
                print(f'  Processing game: {i}')

            if game_data['white']['username'].lower() == target_player:
                target_is = chess.WHITE
                target_elo = game_data['white']['rating']
                score = get_game_value('white', game_data['result'])
                opponent_elo = game_data['black']['rating']
            elif game_data['black']['username'].lower() == target_player:
                target_is = chess.BLACK
                target_elo = game_data['black']['rating']
                score = get_game_value('black', game_data['result'])
                opponent_elo = game_data['white']['rating']
            else:
                assert False, f'Cannot find {target_player} in the game: {game_data}'

            opponent_is = not target_player

            # build a chess board for each game
            pgn = io.StringIO(game_data['moves'])
            game = chess.pgn.read_game(pgn)

            # ignore games that couldn't be parsed correctly
            if len(game.errors) > 0:
                print(f'  Game {i} could not be parsed.')
                for error in game.errors:
                    print(f'    {error}')
                continue

            # initial data structures to track moves and scores
            invalid_game = False
            baseline_score = {move: {color: None for color in colors} for move in special_moves}
            move_counter = {move: {color: -self.NUM_MOVES_DELAY for color in colors} for move in special_moves}

            board = game.board()

            for move in game.mainline_moves():
                move_is = 'white' if board.turn == chess.WHITE else 'black'
                move_number = board.fullmove_number

                # target or opponent, used to track the strength and weaknesses of each player
                move_player = 'player' if board.turn == target_is else 'opponents'

                for label in special_moves:
                    if ((label == 'castle' and board.is_castling(move)) or
                            (label == 'en_passant' and board.is_en_passant(move))):

                        board_score = self.engine.analyse(board, chess.engine.Limit(time=self.MAX_ANALYSE_TIME)).get('score')

                        if board_score.is_mate():  # some games continue playing after mate, ignore the outcome
                            if self.debug:
                                print(f'  Invalid game {i}')
                            invalid_game = True
                            break

                        baseline_score[label][board.turn] = board_score
                        move_counter[label][board.turn] = move_number

                        if self.debug:
                            print(f'    {move_is} used {label} on move {move_number}: {baseline_score[label][board.turn]}')


                    if move_number == move_counter[label][board.turn] + self.NUM_MOVES_DELAY:
                        info = self.engine.analyse(board, chess.engine.Limit(time=self.MAX_ANALYSE_TIME)).get('score')
                        score_delta = self.relative_score(info, baseline_score[label][board.turn])
                        move_utility[label][move_player].append(score_delta)
                        if self.debug:
                            print(f'    {move_is} {label} score {info}, delta {score_delta} at move {move_number}')

                board.push(move)

            # ignore draws, there aren't that many of them
            if score != 0.5 and not invalid_game:
                elo_diff = target_elo - opponent_elo
                game_stats.loc[len(game_stats)] = [score,
                                                   elo_diff,
                                                   1 if move_counter['castle'][target_is] > 0 else 0,
                                                   1 if move_counter['en_passant'][target_is] > 0 else 0,
                                                   1 if move_counter['castle'][opponent_is] > 0 else 0,
                                                   1 if move_counter['en_passant'][opponent_is] > 0 else 0,
                                                   ]

        # cast the score as int so we can run multiclass logistic regression
        y = game_stats['Score'].astype('int')
        y_sum = y.sum()

        #outcome_impact = {f'{player}_{move}': 'Not-significant' for player in players for move in special_moves}
        outcome_impact = {
            'results_available': False,
            'analysis': {},
        }

        if y_sum >= 30 and (len(y) - y_sum) > 30:
            outcome_impact['results_available'] = True
            X = game_stats.loc[:, game_stats.columns != 'Score']

            # scale the elo_diff so it's 0 to 1
            min_elo_diff = X['Elo_Diff'].min()
            max_elo_diff = X['Elo_Diff'].max()
            X.loc[:, 'Elo_Diff'] = (X['Elo_Diff'] - min_elo_diff).multiply(1.0 / (max_elo_diff - min_elo_diff))

            res = GLM(
                y,
                X,
                family=families.Binomial(),
            ).fit(attach_wls=True, atol=1e-10)

            if self.debug:
                print(res.summary())

            for idx, val in res.pvalues.items():
                if idx != 'Elo_Diff':
                    classification = 'Not-significant'
                    if val < (1.0 - self.CONFIDENCE_LEVEL):
                        if 'player' in idx:
                            classification = 'Strength' if res.params[idx] > 0.0 else 'Weakness'
                        else:
                            classification = 'Strength' if res.params[idx] < 0.0 else 'Weakness'

                        if self.debug:
                            print(f'{idx}: {classification}')

                    outcome_impact['analysis'][idx] = {
                        'classification': classification,
                        'coefficient': res.params[idx],
                        'p-value': val,
                    }

        else:
            if self.debug:
                print(f'  Insufficient games to run logistic regression, {len(y)} games with {y_sum} wins')

        score_impact = {}

        for player in players:
            if self.debug:
                print(f'  Utility for {player}:')

            for move in special_moves:
                # print(f'    Move: {move}')
                # print(move_utility[move][player])
                stats = np.array(move_utility[move][player])
                classification = 'Not-significant'

                key = f'{player}_{move}'
                score_impact[key] = {
                    'results_available': False,
                    'analysis': {},
                }

                if stats.shape[0] >= 4:
                    score_impact[key]['results_available'] = True
                    result = ttest_1samp(stats, 0.0, alternative='two-sided')
                    if result.pvalue < (1.0 - self.CONFIDENCE_LEVEL):
                        if stats.mean() > 0:
                            classification = 'Strength'
                        else:
                            classification = 'Weakness'

                    success_rate = np.sum(stats > 0.0) / stats.shape[0]

                    score_impact[key]['analysis'] = {
                        'classification': classification,
                        'mean': stats.mean(),
                        'p-value': result.pvalue,
                    }

                    if self.debug:
                        print(f'    {move} success rate: {success_rate:.3f}, p-value: {result.pvalue:.3f},'
                              f'indication: {classification}')
                else:
                    if self.debug:
                        print(f'    Insufficient data points, {stats.shape[0]}, to report stats for {move}.')

        return outcome_impact, score_impact
