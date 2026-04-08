import requests
# from  _keys import cbio_keys
import _config


cbio_keys = _config.get_cbio_keys()


# Gets all checks within params for a single partner(auth).
# Example Query Params.
# url_prod_1 = "https://api.checkbook.io/v3/check/digital"
# url_prod_from = "https://dapi.checkbook.io/v3/check?start_date=2023-09-01"
# url_prod_page = "https://dapi.checkbook.io/v3/check?page=2"
# url_prod_page_from = "https://demo.checkbook.io/v3/check?page=2&start_date=2023-09-01"

def cbio_get_sent_received_list(auth, params={"page": 1}):

    url_base = "https://api.checkbook.io/v3/check"
    headers = {
        "accept": "application/json",
        "Authorization": auth
    }
    page = 1
    pages = 2
    params.update({"page": 1})  # because did not return to 1 with all partners loop?
    checks = []

    # TODO if passed params don't include page, add

    while page < pages:
        checks = checks
        # params = params
        # page = page
        # pages = pages

        response = requests.get(url_base, params=params, headers=headers)
        print(response.status_code)

        # rspt = response.text
        rspj = response.json()
        page = rspj['page']
        pages = rspj['pages']
        params.update({"page": page + 1})

        # For Testing, move to logging
        print(f'{page} of {pages} with {rspj["total"]} records')

        if rspj['total'] > 0:
            new_checks = rspj['checks']
        else:
            new_checks = []
        checks.extend(new_checks)
        # # Cut
        # try:
        #     new_checks = rspj['checks']
        # except KeyError:
        #     print('oops key error on results')
        #     new_checks = []
        #     continue


        # page = rspj['page']
        # pages = rspj['pages']
        #  params.update({"page": page + 1})

    return checks

def cbio_get_sent_received_list_all_partners():
    checks_all = []
    for x in cbio_keys:
        # print(f'starting partner {cbio_keys[x]}')
        print(f'starting partner {x}')
        checks_partner = cbio_get_sent_received_list(cbio_keys[x])
        # print
        checks_all.extend(checks_partner)
    return checks_all




if __name__ == "__main__":
    twr = "8c1... get from keys"
    checks_partner = cbio_get_sent_received_list(twr)
    pass





"""

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
"""