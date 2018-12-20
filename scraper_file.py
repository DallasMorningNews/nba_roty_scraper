import csv
import json
import requests

import datetime
import math
import pprint
import re
import requests
import sys

from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from operator import itemgetter


SEASON = "2018-19"
YEAR = "2019"

time_ran = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

# headers info for requesting from the nba api
HEADERS = {
    'user-agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'),
    'referer': 'https://stats.nba.com/players/traditional/',
    'accept-language': 'he-IL,he;q=0.8,en-US;q=0.6,en;q=0.4',
    'cache-control': 'max-age=0'
    }

# base data dictionary. We'll iterate over the data from basketball-reference (BR)
# and parse the data for players and stats and add it to this dictionary
rookie_data = {
    "metrics": ["winshare", "per", "usg", "bpm", "mpg", "ppg", "rpg", "apg", "spg", "bpg"],
    "stats": [],
    "players": [],
    "updated": time_ran
}

# empty list to hold our team objects
standings = {
    YEAR: []
}

def get_standard_deviation(data, key):
    x = 0
    y = 0
    l = len(data)
    for obj in data:
        x = x + obj["metrics"][key]
        y = y + (obj["metrics"][key] ** 2)

    standard_deviation = math.sqrt((y - ((x ** 2) / l)) / (l - 1))
    return standard_deviation

def get_mean(data, key):
    x = 0;
    for obj in data:
        x = x + obj["metrics"][key]

    mean = x / len(data);
    return mean;

def set_stats(data):
    for metric in data["metrics"]:
        standard_dev = get_standard_deviation(data["players"], metric)
        mean = get_mean(data["players"], metric)

        target_metric = {
            "metric": metric,
            "standard_dev": standard_dev,
            "mean": mean,
        }

        data["stats"].append(target_metric)


# ------------------------------------------------------------------------------
# DEFINIING THE INITIAL PLAYER SET

# we define our inital set of players by hitting the NBA's api for rookie stats

def get_player_set():

    first_100 = requests.get("https://widgets.sports-reference.com/wg.fcgi?css=1&site=bbr&url=%2Fplay-index%2Fpsl_finder.cgi%3Frequest%3D1%26match%3Dsingle%26type%3Dtotals%26per_minute_base%3D36%26per_poss_base%3D100%26season_start%3D1%26season_end%3D1%26lg_id%3DNBA%26age_min%3D0%26age_max%3D99%26is_playoffs%3DN%26height_min%3D0%26height_max%3D99%26year_min%3D{0}%26year_max%3D{1}%26birth_country_is%3DY%26as_comp%3Dgt%26as_val%3D0%26pos_is_g%3DY%26pos_is_gf%3DY%26pos_is_f%3DY%26pos_is_fg%3DY%26pos_is_fc%3DY%26pos_is_c%3DY%26pos_is_cf%3DY%26qual%3Dpts_per_g_req%26c1stat%3Dper%26c1comp%3Dgt%26c1val%3D-100%26c2stat%3Dws%26c2comp%3Dgt%26c2val%3D-100%26c3stat%3Dbpm%26c3comp%3Dgt%26c3val%3D-100%26c4stat%3Dusg_pct%26c4comp%3Dgt%26order_by%3Dws&div=div_stats".format(YEAR, YEAR))
    first_100_content = BeautifulSoup(first_100.text, "html.parser")
    first_table = first_100_content.find("tbody")
    first_rows = first_table.findAll("tr")

    if len(first_rows) > 99:
        second_100 = requests.get("https://widgets.sports-reference.com/wg.fcgi?css=1&site=bbr&url=%2Fplay-index%2Fpsl_finder.cgi%3Frequest%3D1%26match%3Dsingle%26type%3Dtotals%26per_minute_base%3D36%26per_poss_base%3D100%26season_start%3D1%26season_end%3D1%26lg_id%3DNBA%26age_min%3D0%26age_max%3D99%26is_playoffs%3DN%26height_min%3D0%26height_max%3D99%26year_min%3D{0}%26year_max%3D{1}%26birth_country_is%3DY%26as_comp%3Dgt%26as_val%3D0%26pos_is_g%3DY%26pos_is_gf%3DY%26pos_is_f%3DY%26pos_is_fg%3DY%26pos_is_fc%3DY%26pos_is_c%3DY%26pos_is_cf%3DY%26qual%3Dpts_per_g_req%26c1stat%3Dper%26c1comp%3Dgt%26c1val%3D-100%26c2stat%3Dws%26c2comp%3Dgt%26c2val%3D-100%26c3stat%3Dbpm%26c3comp%3Dgt%26c3val%3D-100%26c4stat%3Dusg_pct%26c4comp%3Dgt%26order_by%3Dws&offset%3D100&div=div_stats".format(YEAR, YEAR))
        second_100_content = BeautifulSoup(second_100.text, "html.parser")
        second_table = second_100_content.find("tbody")
        second_rows = second_table.findAll("tr")

        all_br_rows = first_rows + second_rows
    else:
        all_br_rows = first_rows

    for row in all_br_rows:
        try:
            player_team = row.find("td", {"data-stat": "team_id"}).text
        except AttributeError:
            continue;

        # accounting for special cases where NBA's tricode for a team differs
        # slightly from basketball references'
        if player_team == "PHX":
            team_short = "PHO"
        elif player_team == "CHA" and int(YEAR) >= 2015:
            team_short = "CHO"
        elif player_team =="BKN":
            team_short = "BRK"
        else:
            team_short = player_team

        player_name = ''
        if row.find("td", {"data-stat": "player"}).text == 'Mohamed Bamba':
            player_name = 'Mo Bamba'
        else:
            player_name = row.find("td", {"data-stat": "player"}).text

        games = int(row.find("td", {"data-stat": "g"}).text)
        minutes = int(row.find("td", {"data-stat": "mp"}).text)
        points = int(row.find("td", {"data-stat": "pts"}).text)
        rebounds = int(row.find("td", {"data-stat": "trb"}).text)
        assists = int(row.find("td", {"data-stat": "ast"}).text)
        steals = int(row.find("td", {"data-stat": "stl"}).text)
        blocks = int(row.find("td", {"data-stat": "blk"}).text)
        rookie = {
            "player": player_name,
            "team": "", # this comes from basketball reference standings scrape later
            "team_short": player_team,
            "wins": 0,
            "team_games": 0, # this comes from basketball reference later
            "player_games": row.find("td", {"data-stat": "g"}).text,
            # advanced metrics get added via basketball reference later
            "metrics": {
                "winshare": float(row.find("td", {"data-stat": "ws"}).text),
                "per": float(row.find("td", {"data-stat": "per"}).text),
                "usg": float(row.find("td", {"data-stat": "usg_pct"}).text),
                "bpm": float(row.find("td", {"data-stat": "bpm"}).text),
                "mpg": round((minutes / games), 1),
                "ppg": round((points / games), 1), # this comes from nba scrape later
                "rpg": round((rebounds / games), 1), # this comes from nba scrape later
                "apg": round((assists / games), 1), # this comes from nba scrape later
                "spg": round((steals / games), 1), # this comes from nba scrape later
                "bpg": round((blocks / games), 1) # this comes from nba scrape later
            },
            # zscores get calculated later
            "zscores": {
                "winshare": 0,
                "per": 0,
                "usg": 0,
                "bpm": 0,
                "mpg": 0,
                "ppg": 0,
                "rpg": 0,
                "apg": 0,
                "spg": 0,
                "bpg": 0
            }
        }

        rookie_data["players"].append(rookie)



# ------------------------------------------------------------------------------
# GETTING THE NBA STANDINGS SO WE CAN GET TEAM GAMES AND WINS

# get the current nba standings so we can add in team games and team names to the
# player dictionaries later

def get_standings(year):
    # getting the expanded standings broken down into rows
    standings_request = requests.get("https://widgets.sports-reference.com/wg.fcgi?css=1&site=bbr&url=%2Fleagues%2FNBA_{0}_standings.html&div=div_expanded_standings".format(year))
    standings_content = BeautifulSoup(standings_request.text, "html.parser")
    standings_table = standings_content.find("table", {"id": "expanded_standings"})
    standings_rows = standings_table.find("tbody").findAll("tr")

    # for each row ...
    for row in standings_rows:
        try:
            # determine the team's record, wins and losses, wins games and team abbreviation
            record = row.find("td", {"data-stat": "Overall"}).text
            wins_losses = record.split("-")
            wins = int(wins_losses[0])
            games = int(wins_losses[0]) + int(wins_losses[1])
            link = row.find("td", {"data-stat": "team_name"}).find("a").get("href")
            split_link = link.split("teams/")
            team_short = split_link[1].split("/")[0]

            # create the team object
            team = {}
            team["team_name"] = row.find("td", {"data-stat": "team_name"}).text
            team["record"] = record
            team["wins"] = wins
            team["games"] = games
            team["short_name"] = team_short

            # append it to the standings list
            standings[year].append(team)
        except AttributeError:
            continue

# ------------------------------------------------------------------------------
# CROSS WALKING PLAYERS WITH TEAMS
# function matches players with long team names and total games played by team

def assign_games(players, standings):
    # iterate over the players
    for player in players:
        # pull that player's tricode from their dictionary
        player_team = player["team_short"]
        # finding the team with the matching tricode in the standings
        try:
            team = next((team for team in standings if team["short_name"] == player_team))
        except StopIteration:
            print("Alert!!!: ", player_team, player)
        # assign long team name and team games to player
        player["team"] = team["team_name"]
        player["team_games"] = team["games"]


def get_traditional_stats(year):

    # the payload needed for the api request
    payload = {
        "College": "",
        "Conference": "",
        "Country": "",
        "DateFrom": "",
        "DateTo": "",
        "Division": "",
        "DraftPick": "",
        "DraftYear": "",
        "GameScope": "",
        "GameSegment": "",
        "Height": "",
        "LastNGames": 0,
        "LeagueID": "00",
        "Location": "",
        "MeasureType": "Base",
        "Month": 0,
        "OpponentTeamID": 0,
        "Outcome": "",
        "PORound": 0,
        "PaceAdjust": "N",
        "PerMode": "PerGame",
        "Period": 0,
        "PlayerExperience": "Rookie",
        "PlayerPosition": "",
        "PlusMinus": "N",
        "Rank": "N",
        "Season": year,
        "SeasonSegment": "",
        "SeasonType": "Regular Season",
        "ShotClockRange": "",
        "StarterBench": "",
        "TeamID": "0",
        "VsConference": "",
        "VsDivision": "",
        "Weight": ""
    }

    # the actual request call
    r = requests.get("http://stats.nba.com/stats/leaguedashplayerstats", params=payload, headers=HEADERS, timeout=120)
    r.raise_for_status()

    # converting the response to json
    nba_player_data = r.json()


    for player in rookie_data["players"]:

        hit = False;
        for row in nba_player_data["resultSets"][0]["rowSet"]:
            try:
                if fuzz.token_sort_ratio(player["player"], row[1]) >= 90:
                    player["metrics"]["ppg"] = row[29]
                    player["metrics"]["rpg"] = row[21]
                    player["metrics"]["apg"] = row[22]
                    player["metrics"]["spg"] = row[24]
                    player["metrics"]["bpg"] = row[25]
                    player["metrics"]["mpg"] = row[9]
                    hit = True
            except AttributeError:
                continue

        if hit == False:
            print('!!!!!ALERT!!!!!', player)


def calculate_z_scores(data):
    for stat in data["stats"]:
        metric = stat["metric"]
        sd = stat["standard_dev"]
        mean = stat["mean"]
        for player in data["players"]:
            player_metric = player["metrics"][metric]
            player["zscores"][metric] = (player_metric - mean) / sd

    for player in data["players"]:
        player["total_stand_zscore"] = player["zscores"]["ppg"] + player["zscores"]["rpg"] + player["zscores"]["apg"] + player["zscores"]["spg"] + player["zscores"]["bpg"]

        player["total_adv_zscore"] = player["zscores"]["mpg"] + player["zscores"]["winshare"] + player["zscores"]["bpm"] + player["zscores"]["per"] + player["zscores"]["usg"]

    data["players"] = sorted(data["players"], key=lambda x: (
        x['total_adv_zscore'], x['total_stand_zscore']))
    data["players"].reverse()

def perform_scrape():

    # get the advanced metrics for our remaining players
    get_player_set()

    # get that season's corresponding team standings
    get_standings(YEAR)

    # add team games to the player dictionaries
    assign_games(rookie_data["players"], standings[YEAR])

    # get the initial player set
    # get_traditional_stats(SEASON)

    # calculate the standard deviation and mean for each metric
    set_stats(rookie_data)

    # calculate the z scores for each player in each metric
    calculate_z_scores(rookie_data)

    #  Return the payload
    return rookie_data




# TODO:
# add fifth advance metric
# lambda function and aws hosting
# better commenting
