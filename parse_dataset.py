import os
import pandas as pd
import json
from shutil import unpack_archive, rmtree
from collections import defaultdict
import gzip
import re

UNPACK_DIR = './tmp'
SOURCE_DATA = './source-data'


BETTING_ODDS_FIELDS = [
    'AvgL', 'AvgW', 'B&WL', 'B&WW', 'B365L', 'B365W', 'CBL', 'CBW', 'EXL',
    'EXW', 'IWL', 'IWW', 'LBL', 'LBW', 'PSL', 'PSW', 'SBL', 'SBW', 'SJL',
    'SJW', 'UBL', 'UBW'
]


def unzip_excels():
    for f in os.listdir(SOURCE_DATA):
        relative_path = os.path.join(SOURCE_DATA, f)
        if os.path.isfile(relative_path):
            unpack_archive(relative_path, UNPACK_DIR, format='zip')


def get_avg_odds(data_point):
    if data_point['AvgL'] and data_point['AvgW']:
        return {'AvgL': data_point['AvgL'], 'AvgW': data_point['AvgW']}
    else:
        loser_odds = [data_point[o] for o in BETTING_ODDS_FIELDS
                      if o[-1] == 'L' and data_point[o]]

        winner_odds = [data_point[o] for o in BETTING_ODDS_FIELDS
                       if o[-1] == 'W' and data_point[o]]

        try:
            return {'AvgL': sum(loser_odds) / len(loser_odds),
                    'AvgW': sum(winner_odds) / len(winner_odds)}
        except ZeroDivisionError:
            return {'AvgL': None, 'AvgW': None}


def clean_odds(data):
    for d in data:
        avg_odds = get_avg_odds(d)
        for odds_field in BETTING_ODDS_FIELDS:
            del d[odds_field]
        d['AvgL'] = avg_odds['AvgL']
        d['AvgW'] = avg_odds['AvgW']


def to_int(v):
    # clean ints because there are wierd characters sometimes
    try:
        return int(v) if v else None
    except:
        try:
            return int(re.sub("[^0-9]", "", v))
        except Exception:
            return None


def get_winner_stats(d):
    stats = {'atp': d['ATP'],
             'odds': d['AvgW'],
             'oppOdds': d['AvgL'],
             'bestOf': to_int(d['Best of']),
             'wonSets': to_int(d['Wsets']),
             'lostSets': to_int(d['Lsets']),
             'comment': d['Comment'],
             'court': d['Court'],
             'date': d['Date'],
             'atpRank': to_int(d['WRank']),
             'oppAtpRank': to_int(d['LRank']),
             'round': d['Round'],
             'tournament': d['Tournament'],
             'surface': d['Surface'],
             'won': True}
    return d['Winner'].replace(" ", ""), stats


def get_loser_stats(d):
    stats = {'atp': d['ATP'],
             'odds': d['AvgL'],
             'oppOdds': d['AvgW'],
             'bestOf': to_int(d['Best of']),
             'wonSets': to_int(d['Lsets']),
             'lostSets': to_int(d['Wsets']),
             'comment': d['Comment'],
             'court': d['Court'],
             'date': d['Date'],
             'atpRank': to_int(d['LRank']),
             'oppAtpRank': to_int(d['WRank']),
             'round': d['Round'],
             'tournament': d['Tournament'],
             'surface': d['Surface'],
             'won': False}
    return d['Loser'].replace(" ", ""), stats


def transform_structure(data):
    res = defaultdict(list)
    for d in data:
        # sometimes there is no winner?
        if d['Winner'] and d['Loser']:
            winner_name, winner_stats = get_winner_stats(d)
            loser_name, loser_stats = get_loser_stats(d)
            res[winner_name].append(winner_stats)
            res[loser_name].append(loser_stats)
    return res

SHEETS = {
    '2012': '2012',
    '2011': '2011',
    '2010': '2010'
}


def parse_matches_from_excels():
    unzip_excels()
    dfs = []
    for f in os.listdir(UNPACK_DIR):
        relative_path = os.path.join(UNPACK_DIR, f)
        year = os.path.splitext(f)[0]
        print(year)
        dfs.append(pd.read_excel(relative_path,
                                 sheetname=SHEETS.get(year, 0)))
    rmtree(UNPACK_DIR)
    # take care of all the strange numpy types by converting to json
    # then back to dict
    json_data = pd.concat(dfs).to_json(orient="records", date_format="iso")
    raw_dict = json.loads(json_data)
    clean_odds(raw_dict)

    with gzip.open('data.gz', 'wt') as f:
        json.dump(transform_structure(raw_dict), f)


if __name__ == "__main__":
    parse_matches_from_excels()
