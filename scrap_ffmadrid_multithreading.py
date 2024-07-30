import time
from bs4 import BeautifulSoup
import requests as r
import json
from multiprocessing import Pool
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = 'https://www.rffm.es/'


def get_url_data(url):
    response = r.get(url, verify=False)

    html_doc = response.text
    soup = BeautifulSoup(html_doc, 'html.parser')

    return json.loads(soup.find(
        "script", {"id": "__NEXT_DATA__"}).text)


def get_match_data(codacta, temporada, competicion, grupo):
    print(f'Getting details for match: {codacta}')

    url = BASE_URL + \
        f'acta-partido/{codacta}?temporada={temporada}&competicion={competicion}&grupo={grupo}'

    return get_url_data(url)['props']['pageProps']['game']


def get_match_data_wrapper(args):
    return get_match_data(*args)


def get_competition_data(temporada, tipoJuego, competicion, grupo):
    print('Getting the competition data')
    url = BASE_URL + \
        f'competicion/calendario?temporada={temporada}&tipojuego={tipoJuego}&competicion={competicion}&grupo={grupo}'

    matches = get_url_data(url)['props']['pageProps']['calendar']

    print(
        f'Competition data extracted for {matches["competicion"]} {matches["grupo"].upper()} TEMPORADA {matches["temporada"]}')

    args = []

    for round in matches['rounds']:
        for match in round['equipos']:
            args.append((match['codacta'], temporada, competicion, grupo))

    with Pool() as pool:
        parsed_matches = pool.imap_unordered(get_match_data_wrapper, args)

        # Save to JSON
        with open('matches.json', 'w') as outfile:
            json.dump(list(parsed_matches), outfile,
                      indent=4, ensure_ascii=False)

        print('SUCCESS!!')


temporada = 17
tipoJuego = 1
competicion = 13564522
grupo = 13768766

###### TIMING STUFF ######

start = time.perf_counter()

get_competition_data(temporada, tipoJuego, competicion, grupo)

end = time.perf_counter()

print(f'Finished in {end - start} seconds')
