import json
import requests

host     = 'https://app.mode.com'
username = 'api_token'
password = 'api_secret'

url      = '%s/api/account' % (host)
response = requests.get(url, auth=HTTPBasicAuth(username, password))
result   = response.json()

print result
