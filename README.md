# Chess Strategy Advisor
Chess Strategy Advisor (CSA) is a web based tool to help a player prepare for an upcoming tournament on Chess.com. It analyzes opponents in the tournament as a group, looking for common patterns of weaknesses to exploit and strengths to avoid. Specifically, it looks at the opening moves, how opponents perform in long versus short games and how well they play special moves (Castle and En Passant).

CSA is written in Python and uses the Flask framework. MongoDB is used as the backend database for storing tournament data, player information, and precomputed strengths and weakness for each player. It's architected in three major components: front end, back end and supporting scripts. The front end defines the UI and handles web requests from the user via their browser. The backend handles requests for tournament, player and strategy information from the front end, retrieves raw data from MongoDB and aggregates it before returning it to the front end. The front and backend are architectured so they can be run on separate servers for scalability, but they can also be run from a single machine. The supporting scripts are used to query Chess.com through the public API and scraping their webpage, precompute strengths and weaknesses for each player then push the data to MongoDB. The supporting scripts are intended to be run asynchronously and would need to be run on a regular basis to keep the database on MongoDB up to date.

## Installation
1. Install Python 3.11 or higher. Installation files and instructions are available at https://www.python.org
2. Install the required packages from a terminal with the command: pip install -r requirements.txt

## Execution
1. From a terminal start the backend with the command: python csa_backend.py
2. From a different terminal start the frontend with the command: python app.py
3. From a web browser (Chrome in light mode is recommended) open the page: http://127.0.0.1:8000
4. Select the target tournament then click submit.
5. Select the player you want to analyze strategies for then click submit.

## Demo Video
Link: https://youtu.be/-W8HC-8hX5k

## Troubleshooting
User interface is not visible: make sure your browser is in light mode.

## How the database is generated (provided for reference)
NOTE: This is NOT required to run CSA. The database has already been generated and the credentials to access it are embedded in the source code for CSA so it does not need to be re-generated to use CSA.
1. Follow the instructions to install Stockfisk at https://stockfishchess.org/download/. Version 17 was used to generate the current database on MongoDB.
2. From a terminal set the environment variable STOCKFISH_PATH to the path of Stockfish executable. (for example on macOS: export STOCKFISH_PATH=/opt/homebrew/bin/stockfish)
3. Then from the same terminal run the command: python retrieve_tournaments.py (this will take several minutes to run)
4. Then from the same terminal run the command: python retrieve_player_game_history.py (this will take a day or more to run depending on the speed of your machine)

## Paper
The study's paper can be found on https://drive.google.com/file/d/1I_ndoT6L7sVo8AN_Un9e9n9_WopFye4k/view?usp=sharing.

## Poster Presentation
Poster: https://drive.google.com/file/d/1I_ndoT6L7sVo8AN_Un9e9n9_WopFye4k/view?usp=sharing <br>
Video: https://youtu.be/BifRWbYc8EU

## Landing Page
Player selects tournament and username
<br><br>
![index](index.png)

## Strategy Page
Figure below shows Elo ratings of a group of opponents (left plot), how they play special moves (left plot, on hover), and performance in long versus short term games (right plot).
<br><br>
![elo](elo.png)
<br><br>
Figure below shows opening strategies when playing white (left plot) or black (right plot). Strategies in red hues are not recommended while in blue hues are recommended.
<br><br>
![strategy](strategy.png)
