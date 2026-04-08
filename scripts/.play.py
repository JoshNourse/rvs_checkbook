import pandas
from pandas.io.json import json_normalize
import requests
import pandas as pd
import fx_checkbook as cbio
import re
import _config
import pickle

# TODO cache query results
# TODO pull all partners, apply account wrong account fix, separate back out

use_cache = True
file_date = '2023-09-03'


""" Get all checks - all partners in _keys"""
if use_cache:
    with open('checks_all.pkl', 'rb') as f:
        checks_all = pickle.load(f)
else:
    checks_all = cbio.cbio_get_sent_received_list_all_partners()
    with open('checks_all.pkl', 'wb') as f:
        pickle.dump(checks_all, f)

# df_checks_all = pd.json_normalize(checks_all)
# df_checks_all.to_csv('checks_all_2023-02-01.csv')


checkbook_fix = _config.get_checkbook_fix()  # List of dicts for manual overrides
checkbook_fix_ids = [d['checkbook_id'] for d in checkbook_fix if 'checkbook_id' in d]

claim_id_prefix = _config.get_claim_id_prefix()  # dict to turn claim number prefix into partner name

checks_play = checks_all.copy()

def dict_re_findall(dict_to_search, dict_key, re_pattern):
    """
    Pass a dict, a key and regular expression and return result of re.findall for the given key.
    Returns empty string if key does not exist or expression does not return a result.
    Empty strings evaluate to false

    :param dict_to_search:
    :param dict_key:
    :param re_pattern:
    :return:
    """
    try:
        re_fa = re.findall(re_pattern, dict_to_search[dict_key])
    except TypeError:
        re_fa = ""
        pass
    except IndexError:
        re_fa = ""
        pass
    # add KeyError

    return re_fa



for x in checks_play:
    """ Try regex to pull claim number from description """
    # works for the most part on new cliam numberrs regex cliam # [a-zA-Z]{5}\d{7}
    # x['claim_number'] = dict_re_findall(x, '[a-zA-Z]{5}\d{7}', 'description')

    try:
        x['claim_number'] = re.findall('[a-zA-Z]{5}\d{7}', x['description'])[0]
    except TypeError:
        pass
    except IndexError:
        pass

    """ Try regex for old style claim numbers ** in CBIO all Twisted Road"""
    try:
        x['claim_number'] = re.findall('DSC-\d{7}', x['description'])[0]
    except TypeError:
        pass
    except IndexError:
        pass

    """ dirty data and lookup overrides"""
    x_id = x['id']
    if x['id'] in checkbook_fix_ids:
        the_fix = [d for d in checkbook_fix if d['checkbook_id'] in x_id][0]
        # print(f'THE FIX IS: {the_fix}')
        x['claim_number'] = the_fix['correct_claim']
        # x['claim_number'] = [d for d in checkbook_fix if d['checkbook_id'] in x_id][0]['correct_claim']

    """ Lookup Partner based on claim ID pre-fix ** sender in cbio data could be wrong """
    # if 'claim_number' in x:
    x_prefix = x['claim_number'][0:3]
    x['partner'] = claim_id_prefix[x_prefix]

    """ Line 92 KeyError analyze, find first nan add to fix csv """
    # df = pd.json_normalize(checks_play)
    # dffnull = df[df.claim_number.isnull()]



    """ add add additional cols not in API but in UI download """
    x['type'] = 'check'
    # x['partner'] = ''  # TODO fx lu sender, with fix
    x['receive_date'] = ''
    x['aggregated_amount'] = ''
    x['debit_account'] = ''
    x['credit_account'] = ''
    x['action_ts'] = ''
    x['return_code'] = ''
    x['return_reason'] = ''
    # These disappeared on 2023-05-17???
    x['check_type'] = ''
    x['attachment_uri'] = ''
    x['total'] = ''





df_checks_play = pd.json_normalize(checks_play)

# Concat separate API cols to single address col to match UI download # TODO redo in dict, need KeyError handling
address_cols = ['recipient', 'recipient.line_1', 'recipient.line_2', 'recipient.city', 'recipient.state', 'recipient.zip']
df_checks_play['address'] = df_checks_play[address_cols].apply(lambda row: ' '.join(row.values.astype(str)), axis=1)

# Reorder columns to match UI Download
checks_col_order = ['id', 'date', 'number', 'type', 'direction', 'status', 'check_type', 'amount', 'name', 'address', 'description', 'receive_date', 'aggregated_amount', 'debit_account', 'credit_account', 'sender', 'action_ts', 'return_code', 'return_reason', 'recipient', 'recipient.line_1', 'recipient.line_2', 'recipient.city', 'recipient.state', 'recipient.zip', 'attachment_uri', 'image_uri', 'total', 'claim_number', 'partner']
df_checks_download = df_checks_play[checks_col_order]
df_checks_download.to_csv(f'checks_download_all_{file_date}.csv')



# auth_rvs = ''

""" Test get aut from dict """
# auth_jax = cbio_keys["cbio_auth_jax"]
# print(auth_jax)


""" Try hitting single partner once (change auth in header) """
# url_base = "https://api.checkbook.io/v3/check"
# headers = {
#     "accept": "application/json",
#     "Authorization": cbio_keys["cbio_auth_egs"]
# }
# params = {"page": 1}
# response = requests.get(url_base, params=params, headers=headers)
# rspj = response.json()
# new_checks = rspj['checks']



"""" test call with pagination"""
# checks = cbio.cbio_get_sent_received_list(auth_rvs)
# checks = cbio.cbio_get_sent_received_list(cbio_keys["cbio_auth_txr"])
#
#
# df_checks = pd.json_normalize(checks)
# df_checks.to_csv('rvs_checks_2023-01-25.csv')

"""Test Loop over all partners in auth dict"""
# moved to fx_checkbook def cbio_get_sent_received_list_all_partners():
# checks_all = []
# for x in cbio_keys:
#     print(f'starting partner {cbio_keys[x]}')
#     checks_partner = cbio.cbio_get_sent_received_list(cbio_keys[x])
#     print
#     checks_all.extend(checks_partner)
# df_checks_all = pd.json_normalize(checks_all)
# df_checks_all.to_csv('rvs_checks_all_2023-01-25.csv')








"""


# https://docs.checkbook.io/docs/environments
url_demo = "https://demo.checkbook.io/v3/check"
# https://docs.checkbook.io/reference/get-checks
url_prod = "https://api.checkbook.io/v3/check"
# url_prod_1 = "https://api.checkbook.io/v3/check/digital"
url_prod_from = "https://dapi.checkbook.io/v3/check?start_date=2023-09-01"
url_prod_page = "https://dapi.checkbook.io/v3/check?page=2"
url_prod_page_from = "https://demo.checkbook.io/v3/check?page=2&start_date=2023-09-01"






headers = {
    "accept": "application/json",
    "Authorization": auth_rvs
}

params_all = {
    "q": "string",
    "page": "int of page number to get",
    "per_page": "int of 10, 25, 50",
    "start_date": 'string of iso date',
    "end_date": "string of iso date",
    "direction": "INCOMING OR OUTGOING",
    "sort": "see docs",
    "status": "str [PAID, IN_PROCESS, UNPAID, VOID, EXPIRED, PRINTED, MAILED, FAILED, REFUNDED "

}

params = {"page": 1}

# response = requests.get(url_prod, headers=headers)
response1 = requests.get(url_prod, params=params, headers=headers)

rspt = response.text
rspj = response.json()
# print(rsp)

page = rspj['page']
pages = rspj['pages']
checks = rspj['checks']

checks.extend(checks)


while page < pages:
    url_prod_pag = f"https://api.checkbook.io/v3/check?page={page+1}"
    response_pag = requests.get(url_prod_pag, headers=headers)
    rsp_j = response_pag.json()
    page = rsp_j['page']
    checks_ = rsp_j['checks']



# TODO regex claim number

# df = pandas.DataFrame(rsp)
df = pd.json_normalize(response.json(), record_path=['checks'])
# df1 = pd.json_normalize(checks)
# df1 = pd.DataFrame(checks)
df1 = pd.read_json(checks)
df1 = pd.json_normalize(checks)

"""