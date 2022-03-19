#!/usr/bin/python3

from requests import post

CLIENT_ID = 'CLIENT_ID' # your apps client ID
CLIENT_SECRET = 'CLIENT_SECRET' # your apps client secret
AUTH_URL = 'https://accounts.spotify.com/api/token'

resp = post(AUTH_URL, {
	'grant_type': 'client_credentials',
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
}).json()

print(resp['access_token'])