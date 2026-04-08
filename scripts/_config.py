import csv
import json
import logging
from pathlib import Path


""" ****************************************
            CONFIGURE Paths
******************************************** """

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_FOLDER = PROJECT_ROOT / "logs"
# logs_folder = Path(r"C:\.logs")

# Keys:  Note Personal vault requires 2FA and autolocks after 20 minutes.
key_vault = Path(r'C:\Users\Joshu\OneDrive\Personal Vault\my_keys.json')


#  Deprecated - Doing fix in BigQuery now
# checkbook_fix_csv = pathlib.Path(r'/data_exports/checkbook_fix.csv')
# def get_checkbook_fix():  # Does not work for UTF8
#     with open(checkbook_fix_csv, 'r') as data:
#         return list(csv.DictReader(data))



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
    LOGS_FOLDER.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_FOLDER / f'{logger_name}.log'

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        file_handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s : %(levelname)s : %(name)s : %(funcName)s : %(message)s'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def report(message, logger=None, level="info"):
    print(message, flush=True)

    if logger is None:
        return

    if level == "warning":
        logger.warning(message)
    elif level == "error":
        logger.error(message)
    else:
        logger.info(message)


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
