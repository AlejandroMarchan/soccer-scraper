from bs4 import BeautifulSoup
import requests as r
import json
from multiprocessing import Pool

def parse_team(team_div):
    team_image = team_div.find('img')
    team_image_url = team_image['src'] if team_image else ''
    team_name = team_div.find('a').text
    return team_name, team_image_url

def parse_result(result_div):
    result_parts = result_div.find('p').text.strip().split('-')
    result_home = int(result_parts[0].strip()) if result_parts[0].strip() else None
    result_away = int(result_parts[1].strip()) if result_parts[1].strip() else None
    return result_home, result_away

def parse_substitutions(substitutions_table):
    substitutions_divs = substitutions_table.find_all('div', class_='acta-table-item')
    players_minutes = {}

    for substitution_div in substitutions_divs:
        minute = int(substitution_div.find('span', class_='sustitution-time').text.replace('(', '').replace(')', '').replace('\'', ''))
        for i, player_div in enumerate(substitution_div.find_all('div', class_='acta-table-item-name')):
            if i == 0:
                players_minutes[player_div.text] = 90 - minute
            else:
                players_minutes[player_div.text] = minute
    
    return players_minutes

ITEM_TYPES = {
    'performance-item-card-yellow': 'yellow_cards',
    'performance-item-penalti': 'penalty_goals',
    'performance-item-goal': 'goals',
    'performance-item-card-red': 'red_cards',
    'performance-item-goal-pp': 'own_goals'
}

def parse_players(players_table, players_minutes, starting=True):
    player_divs = players_table.find_all('div', class_='acta-table-item')
    players = []

    for player_div in player_divs:
        player_name = player_div.find('a').text.strip()
        player = {
            'name': player_name,
            'minutes_played': players_minutes[player_name] if player_name in players_minutes else 90 if starting else 0,
            'yellow_cards': [],
            'red_cards': [],
            'goals': [],
            'own_goals': [],
            'penalty_goals': []
        }
        player_performance = player_div.find('div', class_='performance-items')
        for item in player_performance.findChildren("div" , recursive=False):
            minute = int(item.text.replace('(', '').replace(')', '').replace('\'', '').replace('PP', '').strip())
            for item_type in ITEM_TYPES:
                if item['class'] == [item_type]:
                    player[ITEM_TYPES[item_type]].append(minute)
        players.append(player)
    
    return players

def parse_staff_team(staff_team_div):
    staff_name = staff_team_div.find_all('p', class_='team-name')
    staff_job = staff_team_div.find_all('p', class_='team-description')
    staff_team = []
    for name, job in zip(staff_name, staff_job):
        staff = {
            'name': name.text.strip(),
            'job': job.text.strip()
        }
        staff_team.append(staff)
    return staff_team

def parse_staff(staff_div):
    staff_local_div = staff_div.find_all('div', class_='local')[0]
    staff_away_div = staff_div.find_all('div', class_='visitor')[0]

    return parse_staff_team(staff_local_div), parse_staff_team(staff_away_div)

def parse_referees(referees_div):
    referee_names = referees_div.find_all('p', class_='jugador')
    referees = []
    for referee_name in referee_names:
        referees.append(referee_name.text.strip())
    return referees

def parse_stats(stats_div):
    match_stats_url = stats_div.find('a')['href']
    # print(match_stats_url)
    stats_page = r.get(match_stats_url)
    while(stats_page.status_code == 429):
        print('ERROR: 429 too many requests, retrying in 0.1 seconds')
        time.sleep(0.1)
        stats_page = r.get(match_stats_url)

    soup = BeautifulSoup(stats_page.text, 'html.parser')

    starting_local_players = []
    substitute_local_players = []
    starting_away_players = []
    substitute_away_players = []

    local_players_table = soup.find_all('div', {'class': 'acta-table-team local-team'})
    local_minutes = {}
    if len(local_players_table) > 2:
       local_minutes = parse_substitutions(local_players_table[2])
    
    if len(local_players_table) > 0:
        starting_local_players = parse_players(local_players_table[0], local_minutes)
    if len(local_players_table) > 1:
        substitute_local_players = parse_players(local_players_table[1], local_minutes, False)
    
    away_players_table = soup.find_all('div', {'class': 'acta-table-team visitor-team'})
    away_minutes = {}
    if len(away_players_table) > 2:
        away_minutes = parse_substitutions(away_players_table[2])

    if len(away_players_table) > 0:
        starting_away_players = parse_players(away_players_table[0], away_minutes)
    if len(away_players_table) > 1:
        substitute_away_players = parse_players(away_players_table[1], away_minutes, False)

    referees_staff_divs = soup.find_all('div', {'class': 'tabla-jugadores-equipo'})

    try:
        local_staff, away_staff = parse_staff(referees_staff_divs[0])
    except Exception as e:
        print('STAFF')
        print(soup)
        print(e)
        local_staff = ['ERROR']
        away_staff = ['ERROR']
    
    try:
        referees = parse_referees(referees_staff_divs[2])
    except Exception as e:
        print('REFEREES')
        print(e)
        referees = ['ERROR']

    try:
        field_name = soup.find('div', class_='nombre-campo').text.strip()
    except Exception as e:
        print('FIELD NAME')
        print(e)
        field_name = 'ERROR'
    

    
    players = {
        'starting_local_players': starting_local_players, 
        'substitute_local_players': substitute_local_players,
        'starting_away_players': starting_away_players, 
        'substitute_away_players': substitute_away_players,
    }

    staff = {
        'local_staff': local_staff,
        'away_staff': away_staff
    }

    return players, staff, field_name, referees

def parse_match(match):
    div = list(BeautifulSoup(match['div'], 'html.parser').children)[0]
    children_divs = div.findChildren("div" , recursive=False)
    team_home = parse_team(children_divs[0])
    result = parse_result(children_divs[1])
    team_away = parse_team(children_divs[2])
    players, staff, field_name, referees = parse_stats(children_divs[1]) if result[0] is not None else {}
    local_points = 0
    away_points = 3
    final_result = 'away'
    played = True
    if result[0] is None:
        result = (0, 0)
        away_points = 0
        played = False
        final_result = None
    elif result[0] > result[1]:
        local_points = 3
        away_points = 0
        final_result = 'local'
    elif result[0] == result[1]:
        local_points = 1
        away_points = 1
        final_result = 'draw'

    print(f"Jornada {match['match_day_number']} - {team_home[0]} {result[0]} - {result[1]} {team_away[0]}")
    
    return {
        'match_day_number': match['match_day_number'],
        'match_day_date': match['match_day_date'],
        'team_home_name': team_home[0],
        'team_home_logo_url': team_home[1],
        'team_home_goals': result[0],
        'team_away_goals': result[1],
        'team_away_name': team_away[0],
        'team_away_logo_url': team_away[1],
        'local_points': local_points,
        'away_points': away_points,
        'played': played,
        'result': final_result,
        'field_name': field_name,
        'referees': referees,
        'staff': staff,
        'players': players
    }

def get_competition_data(url):
    response = r.get(url)

    html_doc = response.text
    soup = BeautifulSoup(html_doc, 'html.parser')

    match_days_table = soup.find_all("div", {"class": "table matches session calendario"})

    matches = []

    jornadas_range = range(39)

    # filename = 'temporada_Ferro_21_22/temporada_Ferro_21_22.json'
    filename = 'data.json'

    for match_day_table in match_days_table:
        # Get the match day date and number
        match_day_div = match_day_table.find('div', class_='table-row-header-item right').text.strip()
        match_day_parts = match_day_div.split(' ')
        match_day_number = int(match_day_parts[0])
        match_day_date = match_day_parts[1][1:-1]

        # print(f'Jornada {match_day_number}')
        if match_day_number in jornadas_range:
            matches_divs = match_day_table.find_all("div", {"class": "table-row"})
            for div in matches_divs:
                match = {
                    'div': str(div),
                    'match_day_number': match_day_number,
                    'match_day_date': match_day_date
                }
                # parse_match(match)
                matches.append(match)
        #         break
        # break

    with Pool() as pool:
        parsed_matches = pool.imap_unordered(parse_match, matches)

        # Save to JSON
        with open(filename, 'w') as outfile:
            json.dump(list(parsed_matches), outfile, indent=4, ensure_ascii=False)

        print('SUCCESS!!')

    # Save the data as CSV file
    # with open('temporada_Ferro_21_22/temporada_Ferro_21_22.csv', 'w') as csvfile:
    #     fieldnames = matches[0].keys()
    #     writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    #     writer.writeheader()
    #     for match in matches:
    #         writer.writerow(match)

BASE_URL = 'https://www.rffm.es/competiciones/calendario?season=17&type=1&competition=13564522&group=13768766&'

###### TIMING STUFF ######
import time

start = time.perf_counter()

get_competition_data(BASE_URL)

end = time.perf_counter()

print(f'Finished in {end - start} seconds')