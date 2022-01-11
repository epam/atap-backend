from ast import literal_eval
from pandas import DataFrame
import re
import requests


def get_ngrams(content, start_year, end_year, smoothing, corpus=26, case_insensitive=False):
    params = dict(content=content, year_start=start_year, year_end=end_year, corpus=corpus, smoothing=smoothing)
    if case_insensitive:
        params['case_insensitive'] = case_insensitive
    req = requests.get('http://books.google.com/ngrams/graph', params=params)
    res = re.findall('ngrams.data = (.*?);\\n', req.text)
    if res and literal_eval(res[0]):
        df = DataFrame({qry['ngram']: qry['timeseries'] for qry in literal_eval(res[0])})
        df.insert(0, 'year', list(range(start_year, end_year + 1)))
    else:
        df = DataFrame()
    return df
