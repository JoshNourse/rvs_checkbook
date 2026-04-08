# import pandas
# from pandas.io.json import json_normalize
import requests
import pandas as pd
import fx_checkbook as cbio
import re
import _config
import pickle
from datetime import datetime
from pathlib import Path


# TODO cache query results
# TODO pull all partners, apply account wrong account fix, separate back out

use_cache = True
file_date = datetime.today().strftime('%Y-%m-%d')
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_EXPORTS = PROJECT_ROOT / "data_exports"

# output_file = DATA_EXPORTS / f"checks_download_all_{file_date}.csv"
output_file = DATA_EXPORTS / f"checks_download_all_test{file_date}.csv"



""" Get all checks - all partners in _keys"""
if use_cache:
    with open(DATA_EXPORTS / 'checks_all.pkl', 'rb') as f:
        checks_all = pickle.load(f)
else:
    checks_all = cbio.cbio_get_sent_received_list_all_partners()
    with open(DATA_EXPORTS / 'checks_all.pkl', 'wb') as f:
        pickle.dump(checks_all, f)


checks_play = checks_all.copy()
df_checks_play = pd.json_normalize(checks_play)
#checks_col_order = ['id', 'date', 'number', 'direction', 'status', 'amount', 'name', 'address', 'description',  'sender', 'recipient', 'recipient.line_1', 'recipient.line_2', 'recipient.city', 'recipient.state', 'recipient.zip', 'image_uri', 'claim_number', 'partner']
checks_col_order = ['id', 'date', 'number', 'direction', 'status', 'amount', 'name', 'description', 'sender', 'recipient', 'recipient.line_1', 'recipient.line_2', 'recipient.city', 'recipient.state', 'recipient.zip', 'image_uri']
# check if new API columns exist (checked 2026-04-08)

df_checks_download = df_checks_play[checks_col_order]
# df_checks_download.to_csv(f'checks_download_all_{file_date}.csv')  # original before path refactor
df_checks_download.to_csv(output_file, index=True) #TODO set index to false in future, need to keep now to avoid schema change on ghseet-bq sync
# df_checks_play.to_csv(f'checks_download_play_{file_date}.csv')



# Going to do fixes in BigQuery
# checkbook_fix = _config.get_checkbook_fix()  # List of dicts for manual overrides
# checkbook_fix_ids = [d['checkbook_id'] for d in checkbook_fix if 'checkbook_id' in d]
# claim_id_prefix = _config.get_claim_id_prefix()  # dict to turn claim number prefix into partner name


# for x in checks_play:
#     """ Try regex to pull claim number from description """
#     # works for the most part on new cliam numberrs regex cliam # [a-zA-Z]{5}\d{7}
#     # x['claim_number'] = dict_re_findall(x, '[a-zA-Z]{5}\d{7}', 'description')
#
#     try:
#         x['claim_number'] = re.findall('[a-zA-Z]{5}\d{7}', x['description'])[0]
#     except TypeError:
#         pass
#     except IndexError:
#         pass
#
#     """ Try regex for old style claim numbers ** in CBIO all Twisted Road"""
#     try:
#         x['claim_number'] = re.findall('DSC-\d{7}', x['description'])[0]
#     except TypeError:
#         pass
#     except IndexError:
#         pass

""" dirty data and lookup overrides  """
    # NOT WORKING NEED TO FIX
    # x_id = x['id']
    # if x['id'] in checkbook_fix_ids:
    #     the_fix = [d for d in checkbook_fix if d['checkbook_id'] in x_id][0]
#     # print(f'THE FIX IS: {the_fix}')
#     x['claim_number'] = the_fix['correct_claim']
#     # x['claim_number'] = [d for d in checkbook_fix if d['checkbook_id'] in x_id][0]['correct_claim']
#
# """ Lookup Partner based on claim ID pre-fix ** sender in cbio data could be wrong """
# # if 'claim_number' in x:
# x_prefix = x['claim_number'][0:3]
# x['partner'] = claim_id_prefix[x_prefix]

""" Line 92 KeyError analyze, find first nan add to fix csv """
# df = pd.json_normalize(checks_play)
# dffnull = df[df.claim_number.isnull()]



    # """ add add additional cols not in API but in UI download """
    # x['type'] = 'check'
    # # x['partner'] = ''  # TODO fx lu sender, with fix
    # x['receive_date'] = ''
    # x['aggregated_amount'] = ''
    # x['debit_account'] = ''
    # x['credit_account'] = ''
    # x['action_ts'] = ''
    # x['return_code'] = ''
    # x['return_reason'] = ''
    # # These disappeared on 2023-05-17???
    # x['check_type'] = ''
    # x['attachment_uri'] = ''
    # x['total'] = ''


# df_checks_play = pd.json_normalize(checks_play)
#
# # Concat separate API cols to single address col to match UI download # TODO redo in dict, need KeyError handling
# # address_cols = ['recipient', 'recipient.line_1', 'recipient.line_2', 'recipient.city', 'recipient.state', 'recipient.zip']
# # df_checks_play['address_joined'] = df_checks_play[address_cols].apply(lambda row: ' '.join(row.values.astype(str)), axis=1)
#
# #TODO Not working, not all these columns exist anymore
# # checks_col_order = ['id', 'date', 'number', 'type', 'direction', 'status', 'check_type', 'amount', 'name', 'address', 'description', 'receive_date', 'aggregated_amount', 'debit_account', 'credit_account', 'sender', 'action_ts', 'return_code', 'return_reason', 'recipient', 'recipient.line_1', 'recipient.line_2', 'recipient.city', 'recipient.state', 'recipient.zip', 'attachment_uri', 'image_uri', 'total', 'claim_number', 'partner']
# checks_col_order = ['id', 'date', 'number', 'direction', 'status', 'amount', 'name', 'address', 'description',  'sender', 'recipient', 'recipient.line_1', 'recipient.line_2', 'recipient.city', 'recipient.state', 'recipient.zip', 'image_uri', 'claim_number', 'partner']
# df_checks_download = df_checks_play[checks_col_order]
# df_checks_download.to_csv(f'checks_download_all_{file_date}.csv')
# # df_checks_play.to_csv(f'checks_download_play_{file_date}.csv')

"""Just to Explore original data"""
# df_checks_all = pd.json_normalize(checks_all)
# df_checks_all.to_csv(f'checks_download_all_{file_date}.csv')



# THIS WORKS
# auth_key = 'moved_to_secrets'
# # "Authorization": cbio_keys["cbio_auth_egs"]
#
# url_base = "https://api.checkbook.io/v3/check"
# headers = {
#     "accept": "application/json",
#     "Authorization": auth_key
# }
# params = {"page": 1}
# response = requests.get(url_base, params=params, headers=headers)
# rspj = response.json()
# new_checks = rspj['checks']

