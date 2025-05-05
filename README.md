# pyspodl - a spotify downloader using librespot

using the module [librespot-python by kokarare1212](https://github.com/kokarare1212/librespot-python)

# What is different from other downloaders?
Well, maybe nothing. pyspodl can only do these things: download tracks, albums and playlists in "high" (non-premium) and "very high" (premium account required) quality. It downloads them from Spotify, it does not use another source like some other programs do.

# how to use
Requirements: python3, git. Make sure you have those and a linux PC/environment, then

+ Generate a `credentials.json` file using [librespot-auth](https://github.com/dspearson/librespot-auth)
    + After compiling (or grabbing the prebuilt binaries), run `librespot-auth` like this: `librespot-auth --name "pyspodl" --class tv`. Then, copy the generated `credentials.json` file to the path where you will run the git clone command.
    + Open the `credentials.json` file, and do the following:
        1. Replace `"auth_data"` with `"credentials"`.
        2. Remove `"auth_type": 1,`
        3. Enter this before the closing `}`: `"type": "AUTHENTICATION_STORED_SPOTIFY_CREDENTIALS"`.
        4. Confirm your file looks similar to this:
```json
{"username": "BLABLA", "credentials": "BLABLABLA", "type": "AUTHENTICATION_STORED_SPOTIFY_CREDENTIALS"}
```
+ Create an application from [spotify dashboard](https://developer.spotify.com/dashboard/applications), and copy the client ID and secret
+ Run this command: `git clone https://github.com/devlocalhost/pyspodl`
+ Paste the client id and secret into the config file, inside the "pyspodl" directory.
+ Run `pip3 install git+https://github.com/kokarare1212/librespot-python`.
+ You will also need Pillow for the album cover, mutagen for tags, and toml to read the config file: `pip3 install Pillow mutagen toml`.
+ Now you can use pyspodl like this: `python3 pyspodl`

## examples
`python pyspodl -l LINK`

`python pyspodl -l "LINK1 LINK2 LINK3"`

`python pyspodl -l ... -c /path/to/config.file`

Or, check `python -h`

## updating pyspodl
When there's a new update, you can simply run `git pull` in the directory where you cloned pyspodl.

# the config file
Before you start using pyspodl, you need to fill out the config file.

## config entries
+ `credentials_config_file`: the full path to credentials.json file
+ `token`: used to send request to spotify api. you do not need to touch this.
+ `client_id`: used to get the token
+ `client_secret`: used to get the token
+ `timeout`: tells the program to wait x seconds before downloading the next song from a playlist or album (to avoid account bans, but I never had an account get banned by using my program).
+ `premium_downloads`: download tracks in higher quality. only for premium accounts.
+ `download_path`: the path to download the tracks
+ `set_metadata`: set tags for the tracks
+ `track_format`: the format the tracks will be saved in. check the config file for possible entries

## config example
```
[account]
credentials_file_path = "" # full path to the credentials.json file
token = "" # used to communicate with spotify api
client_id = "" # used to get the token
client_secret = "" # same thing as above

[downloading]
timeout = 2 # in seconds
premium_downloads = false # can be false or true
download_path = "" # download path for the tracks
set_metadata = true # can be false or true
track_format = "{artist}/{album}/{title}" # can be: artist, album, title, tracknumber, year
# the above format will save a song like this: download_path/Nas/Illmatic/The World Is Yours.ogg
#                                                         artist    album              title
```

# help
Feel free to fork or make PR's (pull requests). If you're forking, please leave [this repos link](https://github.com/devlocalhost/pyspodl) in your readme and [kokarare1212's module repo link](https://github.com/kokarare1212/librespot-python).
If you have any problems/want to report a bug or request a feature, open an issue
