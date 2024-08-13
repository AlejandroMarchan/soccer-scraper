import time
from bs4 import BeautifulSoup
import requests as r
import json
from multiprocessing import Pool
from tqdm import tqdm
import json
import urllib3
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = 'https://www.rffm.es/'
API_URL = 'https://www.rffm.es/api/'
DATA_BASE_DIR = 'data/'


def save_json(filename, data, subfolders=[]):
    # Ensure trailing slash (/)
    folder_path = os.path.join(DATA_BASE_DIR, *subfolders, "")

    # Check if the folder exists, if not create it
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    with open(folder_path + filename + '.json', 'w') as outfile:
        json.dump(data, outfile, indent=4, ensure_ascii=False)


def get_url_data(url):
    response = r.get(url, verify=False)

    html_doc = response.text
    soup = BeautifulSoup(html_doc, 'html.parser')

    return json.loads(soup.find(
        "script", {"id": "__NEXT_DATA__"}).text)


def get_match_data(codacta, season, competition, group):
    url = BASE_URL + \
        f'acta-partido/{codacta}?temporada={season}&competicion={competition}&grupo={group}'

    return get_url_data(url)['props']['pageProps']['game']


def get_match_data_wrapper(args):
    return get_match_data(*args)


def get_competition_data(season, game_type, competition, group):
    url = BASE_URL + \
        f'competicion/calendario?temporada={season}&tipojuego={game_type}&competicion={competition}&grupo={group}'

    matches = get_url_data(url)['props']['pageProps']['calendar']

    competition_name = f'{matches["competicion"].capitalize()} {matches["grupo"].capitalize()} Temporada {matches["temporada"]}'

    print(f'Extracting data for competition: {competition_name}')
    print(url)

    args = []

    for round in matches['rounds']:
        for match in round['equipos']:
            args.append((match['codacta'], season, competition, group))

    with Pool() as pool:
        parsed_matches = list(tqdm(pool.imap_unordered(
            get_match_data_wrapper, args), total=len(args)))

        save_json(matches["grupo"], parsed_matches, [
                  matches["temporada"], matches["competicion"]])


def get_seasons_and_game_types():
    print('Getting the competition data')
    url = BASE_URL + f'competicion/calendario'

    seasons = get_url_data(url)['props']['pageProps']['seasons']
    game_types = get_url_data(url)['props']['pageProps']['gameTypes']

    save_json('seasons', seasons)
    save_json('game-types', game_types)

    return seasons, game_types


def get_competitions(season, game_type):
    '''
    https://www.rffm.es/api/competitions?temporada=19&tipojuego=1

    A competition looks as follows:
    .. code-block:: json
        {
            "codigo": "17217772",
            "nombre": "COPA R.F.E.F. FASE AUTONOMICA",
            "tipo_competicion": "2",
            "Orden": "15",
            "TipoJuego": "Futbol-11",
            "CodigoCategoria": "40050",
            "NombreCategoria": "TERCERA FEDERACION",
            "cod_grupo_categoria": "4949443",
            "nombre_grupo_categoria": "CATEGORIA NACIONAL",
            "Activa": "0",
            "FechaInicio": "2023-08-16",
            "FechaFin": "2023-08-23",
            "ptos_ganado": "3",
            "ptos_empatado": "1",
            "ptos_perdido": "0",
            "minutos_juego": "90",
            "numero_partes": "2",
            "goleadores": "1",
            "ver_estadisticas_jugador": "1",
            "visible_clasificacion": "1"
        }
    '''
    url = API_URL + f'competitions?temporada={season}&tipojuego={game_type}'
    return r.get(url, verify=False).json()


def get_competition_groups(competition):
    '''
    https://www.rffm.es/api/groups?competicion=17145407

    A group looks as follows:
    .. code-block:: json
        {
            "codigo": "17145408",
            "nombre": "Grupo 1",
            "total_jornadas": "30",
            "total_equipos": "16",
            "clasificacion_porteros": "1",
            "ver_clasificacion": "1",
            "clasificacion_goleadores": "1",
            "orden": "10"
        }
    '''
    url = API_URL + f'groups?competicion={competition}'
    return r.get(url, verify=False).json()


# seasons, game_types = get_seasons_and_game_types()

season = 19
game_type = 1
competition = 17145407
# group = 13768766

###### TIMING STUFF ######
total_start = time.perf_counter()


groups = get_competition_groups(competition)

for group in groups:
    start = time.perf_counter()

    get_competition_data(season, game_type, competition, group['codigo'])

    end = time.perf_counter()

    print(f'Finished in {end - start} seconds')

total_end = time.perf_counter()
print(f'Total finished in {total_end - total_start} seconds')
