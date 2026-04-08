import json
import pathlib
from pathlib import Path
import logging
import csv


""" ****************************************
            CONFIGURE Paths
******************************************** """

# Keys:  Note Personal vault requires 2FA and autolocks after 20 minutes.
key_vault = pathlib.Path(r'C:\Users\Joshu\OneDrive\Personal Vault\my_keys.json')
logs_folder = Path(r"C:\.logs")

#  Deprecated - Doing fix in BigQuery now
checkbook_fix_csv = pathlib.Path(r'/data_exports/checkbook_fix.csv')
def get_checkbook_fix():  # Does not work for UTF8
    with open(checkbook_fix_csv, 'r') as data:
        return list(csv.DictReader(data))



""" ****************************************
            CONFIGURE KEYS
******************************************** """

def get_keys(key_path=key_vault):
    """
    Reads a JSON file of all keys stored locally.
    :return:
    """
    with open(key_path, 'r') as key_txt:
        keys = json.loads(key_txt.read())
    return keys


def get_cbio_keys(keys_dict=get_keys()):
    return get_keys()['cbio_rvs_keys']

def get_bigquery_keys(keys_dict=get_keys()):
    return get_keys()['bq_python-load-josh']

""" ****************************************
            CONFIGURE LOGGER
******************************************** """
def logger_configure(logger_name):

    # logs_folder = Path("/home/joshua/PyProjects/zoom/logs")
    logger_folder = logs_folder
    log = Path.joinpath(logger_folder, Path(f'{logger_name}.log'))

    # Gets or creates a logger
    logger = logging.getLogger(logger_name)
    # set log level
    logger.setLevel(logging.DEBUG)
    # define file handler and set formatter
    file_handler = logging.FileHandler(log)
    formatter    = logging.Formatter('%(asctime)s : %(levelname)s : %(name)s : %(funcName)s : %(message)s')
    file_handler.setFormatter(formatter)
    # add file handler to logger
    logger.addHandler(file_handler)
    return logger


""" ****************************************
            CONFIGURE HELPERS
******************************************** """

def get_claim_id_prefix():
    claim_id_prefix = {
        "NEE": "NEED",
        "TWR": "Twisted Road",
        "DSC": "Twisted Road",  # becuase all early checkbook pmts were TR, though DSC could be any partner
        "RVS": "RVshare",
        "TXR": "TxRV",
        "EGS": "EagleShare",
        "FTC": "Fetch",
        "JAX": "Jax",
        "sys": "system"
    }
    return claim_id_prefix






if __name__ == "__main__":
    pass
    # x = get_checkbook_fix()
    # try_keys =
    # try_key = get_cbio_keys
