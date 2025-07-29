# Chess Strategy Advisor
Chess Strategy Advisor (CSA) is a web-based tool designed to help players prepare for upcoming tournaments on Chess.com. It analyzes opponents collectively, identifying common patterns in their weaknesses to exploit and strengths to avoid. Specifically, it evaluates opening strategies, performance in long versus short games, and proficiency with special moves such as castling and en passant.

CSA is developed in Python using the Flask framework. It leverages MongoDB as the backend database to store tournament data, player profiles, and precomputed assessments of each player’s strengths and weaknesses. The system is structured into three main components: the front end, the back end, and a set of supporting scripts.
- The front end defines the user interface and handles web interactions through the browser.
- The back end processes requests for tournament, player, and strategy information, retrieving raw data from MongoDB and aggregating it before returning results to the front end. The front and back ends are designed to be scalable, allowing deployment on separate servers, though they can also run on a single machine.
- The supporting scripts interact with the Chess.com public API and web pages to collect player data, compute strengths and weaknesses, and update the MongoDB database. These scripts are intended to run asynchronously and should be executed regularly to keep the data current.

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
