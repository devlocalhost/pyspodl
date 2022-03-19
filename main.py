#!/usr/bin/python3

from librespot.core import Session
from librespot.metadata import TrackId
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality

from platform import system as sysname
from colorhex import colorex, BOLD
from datetime import datetime
from requests import get, post
from getpass import getpass
from base64 import b64encode, b64decode
from json import dumps, loads, dump, load
from time import sleep
from tqdm import tqdm
from sys import exit
from os import system, makedirs, getcwd

CLEARCMD = None # set to pass to ignore and not clear the terminal

def clearscr():
    if CLEARCMD == 'pass':
        pass

    elif CLEARCMD != None:
        system(CLEARCMD)

    elif CLEARCMD == None:
        if sysname() == 'Windows':
            system('cls')

        elif sysname() == 'Linux' or sysname() == 'Darwin':
            system('clear')

        else:
            print(f'Clear command not defined!')

def generate_new_token():
    with open('.data/account.json', 'r') as oldata:
        odata = load(oldata)

    CLIENT_ID = 'CLIENT_ID'
    CLIENT_SECRET = 'CLIENT_SECRET'
    AUTH_URL = 'https://accounts.spotify.com/api/token'

    resp = post(AUTH_URL, {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }).json()

    odata['token'] = resp['access_token']

    try:
        with open('.data/account.json', 'w') as newdata:
            dump(odata, newdata)
            newdata.flush()

    except Exception as exc:
        print(colorex(f'There was an error updating the file. Do you have write permissions?\nHeres the token anyway: {resp["access_token"]}. Replace it with the old "token" variable in .data/account.json\n{exc}', REDCOLO))

    input(colorex('Token has been succesfully updated\nPress enter to continue...', GREENCOLO, BOLD))
    main()

def isvalid(TOKEN):
    print(colorex('Checking if token is valid...', YELLOCOLO, BOLD))

    headr = {"Authorization": f"Bearer {TOKEN}"}
    resp = get(f'https://api.spotify.com/v1/search?q=home+resonance&type=track', headers=headr)

    if resp.status_code == 401:
        print(colorex('TOKEN HAS EXPIRED, REGENERATING...', REDCOLO, BOLD))
        generate_new_token()

    else:
        global TOKEN_VALID
        TOKEN_VALID = True

        print(colorex('Token is valid', GREENCOLO, BOLD))
        sleep(0.3)
        clearscr()
        main()

def search(term, TOKEN):
    clearscr()

    headr = {"Authorization": f"Bearer {TOKEN}"}

    resp = get(f'https://api.spotify.com/v1/search?q={term.replace(" ", "%20")}&type=track', headers=headr).json()

    try:
        if resp['error']['status'] == 401:
            print(colorex('API Token has expired, generating and updating...', REDCOLO, BOLD))
            generate_new_token()

    except KeyError:
        pass

    totalresults = len(resp['tracks']['items'])

    if totalresults == 0:
        input(colorex(f'No results found about "{term}"\nPress enter to continue...', REDCOLO, BOLD))

        clearscr()
        main()

    for details in resp['tracks']['items']:
        trackuri = details['uri']
        artistname = details['album']['artists'][0]['name']
        trackname = details['name']
        trackid = details['id']
        pre_url = details['preview_url']

        print(colorex(f'{trackname} by {artistname}\nURI: {trackuri}\nID: {trackid}\nShort preview: {pre_url}\n--------------------', YELLOCOLO, BOLD))

    input(colorex(f'\n{totalresults} total results\nPress enter to go back...', BLURPLECOLO, BOLD))
    clearscr()

    main()
        
# search('dua lipa love again', False)

def track(trackid, TOKEN):
    clearscr()

    headr = {"Authorization": f"Bearer {TOKEN}"}

    resp = get(f'https://api.spotify.com/v1/tracks/{trackid}', headers=headr).json()

    try:
        if resp['error']['status'] == 401:
            print(colorex('API Token has expired, generating and updating...', REDCOLO, BOLD))
            generate_new_token()

    except KeyError:
        pass

    if resp['explicit'] == False:
       isexplicit = 'No'

    if resp['explicit'] == True:
       isexplicit = 'Yes'

    # durationms = resp['duration_ms']
    duration = datetime.fromtimestamp(resp['duration_ms'] / 1000.0).strftime('%M minutes and %S seconds')
    trackurl = resp['external_urls']['spotify']
    trackname = resp['name']
    track_pre = resp['preview_url']
    artistname = resp['album']['artists'][0]['name']
    albumurl = resp['album']['external_urls']['spotify']
    albumname = resp['album']['name']
    albumreleased = resp['album']['release_date']
    albumtotaltracks = resp['album']['total_tracks']

    print(colorex(f'{trackname} by {artistname}\nDuration? {duration}\nURL? {trackurl}\nIs explicit? {isexplicit}\nFrom album "{albumname}" which was released at {albumreleased} and has total {albumtotaltracks} tracks\nAlbum link? {albumurl}', BLURPLECOLO, BOLD))

# track('1imMjt1YGNebtrtTAprKV7', True)

def playlist_info(playlist_id, TOKEN):
    headr = {"Authorization": f"Bearer {TOKEN}"}

    info = get(f'https://api.spotify.com/v1/playlists/{playlist_id}/', headers=headr).json()

    try:
        if info['error']['status'] == 401:
            print(colorex('API Token has expired, generating and updating...', REDCOLO, BOLD))
            generate_new_token()

    except KeyError:
        pass

    des = info['description']

    if des == '':
        print(colorex(f"{info['name']} made by {info['owner']['display_name']} | {playlist_id} (Playlist ID)", LIGHTPINKCOLO, BOLD))

    elif des != '':
        print(colorex(f"{info['name']} made by {info['owner']['display_name']} | {info['description']} - {playlist_id} (Playlist ID)", LIGHTPINKCOLO, BOLD))

    print(colorex(f"{info['tracks']['total']} tracks in total", BLURPLECOLO, BOLD))
    print(colorex(f"{info['followers']['total']} people are following this playlist", YELLOCOLO, BOLD))
    print(colorex('--------------------------------', GREYCOLO, BOLD))

    target = info['tracks']['total']
    final = 0

    for i in range(0, target, 101):
        resp = get(f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks?offset={final}&limit=100', headers=headr).json()

        final += 100

        for tracks in resp['items']:
            duration = datetime.fromtimestamp(tracks['track']['duration_ms'] / 1000.0).strftime('%M minutes and %S seconds')
            trackid = tracks['track']['id']
            trackname = tracks['track']['name']
            trackartist = tracks['track']['artists'][0]['name']
            tracklink = tracks['track']['external_urls']['spotify']

            if tracks['track']['preview_url'] != None:
                previewurl = tracks['track']['preview_url']

            elif tracks['track']['preview_url'] == None:
                previewurl = 'Preview not available'

            if tracks['track']['explicit'] == False:
                isexplicit = 'No'

            if tracks['track']['explicit'] == True:
                isexplicit = 'Yes'

            print(colorex(f'{trackname} by {trackartist}', YELLOCOLO, BOLD))
            print(colorex(f'Link? {tracklink}', GREYCOLO, BOLD))
            print(colorex(f'Duration? {duration}', SPECIALCOLO, BOLD))
            print(colorex(f'Is explicit? {isexplicit}', LIGHTPINKCOLO, BOLD))
            print(colorex(f'ID? {trackid}', BLURPLECOLO, BOLD))
            print(colorex(f'Preview by visiting: {previewurl}', GREENCOLO, BOLD))
            print(colorex('--------------------------------', GREYCOLO, BOLD))
    
    input(colorex(f'Press enter to go back...', BLURPLECOLO, BOLD))
    clearscr()

    main()

def playlist_download(playlist_id, token, EMAIL, PASSWD):
    makedirs(f'playlist_{playlist_id}', exist_ok=True)

    session = Session.Builder().user_pass(EMAIL, PASSWD).create()
    headr = {"Authorization": f"Bearer {token}"}

    resp = get(f'https://api.spotify.com/v1/playlists/{playlist_id}', headers=headr).json()
    info = get(f'https://api.spotify.com/v1/playlists/{playlist_id}/', headers=headr).json()

    target = info['tracks']['total']
    final = 0

    for i in range(0, target, 101):
        resp = get(f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks?offset={final}&limit=100', headers=headr).json()

        final += 100

        for tracks in resp['items']:
            trackid = tracks['track']['id']

            track_id = TrackId.from_uri(f"spotify:track:{trackid}")

            resp = get(f'https://api.spotify.com/v1/tracks/{trackid}', headers=headr).json()

            try:
                stream = session.content_feeder().load(track_id, VorbisOnlyAudioQuality(AudioQuality.HIGH), False, None)

            except Exception as exc:
                print(colorex(f'ERR: {resp["name"]} by {resp["album"]["artists"][0]["name"]}: {exc}\nSkipping...', REDCOLO, BOLD))

            print(colorex(f"Downloading {resp['name']} by {resp['album']['artists'][0]['name']} ...", GREENCOLO, BOLD))

            total_size = stream.input_stream.size
            
            filename = str(f"{resp['album']['artists'][0]['name']} - {resp['name']}.mp3").replace(' ', '_').replace('(', '-').replace(')', '-').replace('*', '-').replace('&', '-').replace('#', '-').replace('$', '-').replace('!', '-').replace('"', '').replace("'", '-')

            with open(f'playlist_{playlist_id}/{filename}', 'wb') as fl, tqdm(unit='B', unit_scale=True, unit_divisor=1024, total=total_size, bar_format=colorex('{percentage:3.0f}%|{bar:16}|{n_fmt} out of {total_fmt} with rate of {rate_fmt}, ETA {remaining}', BLURPLECOLO, BOLD)) as bar:
                for _ in range(int(total_size / 5000) + 1):
                    bar.update(fl.write(stream.input_stream.stream().read(50000)))

            print(colorex(f"{resp['name']} by {resp['album']['artists'][0]['name']} | OK", SPECIALCOLO, BOLD))

def downloader(uri, EMAIL, PASSWD, TOKEN):
    session = Session.Builder().user_pass(EMAIL, PASSWD).create()

    track_id = TrackId.from_uri(f"spotify:track:{uri}")

    headr = {"Authorization": f"Bearer {TOKEN}"}

    resp = get(f'https://api.spotify.com/v1/tracks/{uri}', headers=headr).json()

    try:
        if resp['error']['status'] == 401:
            print(colorex('API Token has expired, generating and updating...', REDCOLO, BOLD))
            generate_new_token()

    except KeyError:
        pass

    print(colorex('Trying to use highest possible quality...', YELLOCOLO, BOLD))

    try:
        stream = session.content_feeder().load(track_id, VorbisOnlyAudioQuality(AudioQuality.VERY_HIGH), False, None)
        print(colorex('Using highest possible quality (VERY_HIGH)', GREENCOLO, BOLD))

    except:
        print(colorex('Failed. Maybe try to use a premium account? Using normal quality instead (HIGH)', REDCOLO, BOLD))
        stream = session.content_feeder().load(track_id, VorbisOnlyAudioQuality(AudioQuality.HIGH), False, None)

    print(colorex(f"Downloading {resp['name']} by {resp['album']['artists'][0]['name']}...", BLURPLECOLO, BOLD))

    total_size = stream.input_stream.size

    with open(f"{resp['album']['artists'][0]['name']}_-_{resp['name']}.m4a", 'wb') as fl, tqdm(unit='B', unit_scale=True, unit_divisor=1024, total=total_size, bar_format=colorex('{percentage:3.0f}%|{bar:16}|{n_fmt} out of {total_fmt} with rate of {rate_fmt}, ETA {remaining}', BLURPLECOLO, BOLD)) as bar:
        for _ in range(int(total_size / 5000) + 1):
            bar.update(fl.write(stream.input_stream.stream().read(50000)))

    # with open(f"{resp['album']['artists'][0]['name']} - {resp['name']}.m4a", 'wb') as fl:
    #     fl.write(stream.input_stream.stream().read())

    input(colorex(f'Done. Saved in "{getcwd()}". Press enter to continue', GREENCOLO, BOLD))
    main()

# downloader('1imMjt1YGNebtrtTAprKV7')

def writedetails():
    print(colorex('MAKE SURE YOU ENTER THE CORRECT DETAILS! THE PROGRAM DOES NOT CHECK IF YOUR DETAILS ARE CORRECT, But when downloading a song, it will raise an exception/error if your details are incorrect', REDCOLO, BOLD))
    print(colorex('Note: You wont be able to see your password and API token while typing. If you dont have a API Token, run the gettoken.py file\n', YELLOCOLO, BOLD))

    email = input(colorex('Email\n -> ', BLURPLECOLO, BOLD))
    passwd = getpass(colorex('Password\n -> ', REDCOLO, BOLD))
    token = getpass(colorex('API Token\n -> ', REDCOLO, BOLD))

    makedirs('.data', exist_ok=True)

    with open('.data/account.json', 'w+') as data:
        data.write(dumps({"email": email, "password": str(b64encode(passwd.encode("utf-8")), "utf-8"), "token": token}))
        data.flush()

        input(colorex('Data written succesfully. The data has been saved in a hidden directory to keep your account information secret (.data)\nPress enter to continue', GREENCOLO, BOLD))

        clearscr()

        main()

def main():
    clearscr()

    try:
        with open('.data/account.json', 'r') as file:
            data = loads(file.read())

            EMAIL = data['email']
            PASSWD = str(b64decode(data['password']), "utf-8")
            TOKEN = data['token']

            if TOKEN_VALID == None:
                isvalid(TOKEN)

            elif TOKEN_VALID == True:
                pass

            ask = input(colorex('Press\n - enter to continue\n - e to exit\n - u to update account data\n -> ', BLURPLECOLO, BOLD))

            if ask == '':
                clearscr()

                askchoice = input(colorex('Press\n - ds to download a song\n - t to get track info\n - p to get playlist info\n - pd to download a playlist\n - s to search\n -> ', BLURPLECOLO, BOLD))

                if askchoice.lower() == 'ds':
                    clearscr()

                    uri = input(colorex('Enter song URI (spotify:track: isnt needed, only URI)\n -> ', YELLOCOLO, BOLD))

                    downloader(uri, EMAIL, PASSWD, TOKEN)

                elif askchoice.lower() == 't':
                    clearscr()

                    tid = input(colorex('Enter track ID\n -> ', GREENCOLO, BOLD))

                    track(tid, TOKEN)

                elif askchoice.lower() == 's':
                    clearscr()

                    srch = input(colorex('I want to search for...\n -> ', REDCOLO, BOLD))

                    search(srch, TOKEN)

                elif askchoice.lower() == 'p':
                    clearscr()

                    playid = input(colorex('Enter playlist ID\n -> ', BLURPLECOLO, BOLD))

                    clearscr()
                    playlist_info(playid, TOKEN)

                elif askchoice.lower() == 'pd':
                    clearscr()

                    playid = input(colorex('Enter playlist ID\n -> ', BLURPLECOLO, BOLD))

                    clearscr()
                    playlist_download(playid, TOKEN, EMAIL, PASSWD)

            elif ask.lower() == 'e':
                clearscr()
                exit()

            elif ask.lower() == 'u':
                clearscr()
                writedetails()

            # track('1imMjt1YGNebtrtTAprKV7', False, TOKEN)

    except FileNotFoundError:
        print(colorex('No account detected. Account email, password and API token are required\n', REDCOLO, BOLD))

        ask = input(colorex('Press enter to proceed or e to exit\n -> ', BLURPLECOLO, BOLD))

        clearscr()

        if ask == '':
            writedetails()

        elif ask == 'e':
            clearscr()
            exit()

if __name__ == '__main__':
    TOKEN_VALID = None
    GREENCOLO = '43b581'
    YELLOCOLO = 'fdcc4b'
    REDCOLO = 'f04947'
    BLURPLECOLO = '7289DA'
    GREYCOLO = 'CAD3c8'
    LIGHTPINKCOLO = 'FEA47F'
    SPECIALCOLO = 'BCA799'

    main()
