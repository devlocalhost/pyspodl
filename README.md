# pyspodl - a spotify downloader using librespot

using the module [librespot-python by kokarare1212](https://github.com/kokarare1212/librespot-python)

# important
I may not work on pyspodl anymore. I dont want to work on this program anymore, im just tired of it. So please do not expect any new features. I will of course update the program if a bug or problem is found, I just will not add any features. [Feel free to fork and add your own features](#helping)

# What is different from other downloaders?
Well, maybe nothing. pyspodl can only do these things: download tracks, albums and playlists in "high" (non-premium) and "very high" (premium account required) quality. It downloads them from Spotify, it does not use another source like some other programs do.

# how to use
+ First, you'll need a client ID and a secret key. Get them by creating an application in the [spotify dashboard](https://developer.spotify.com/dashboard/applications)
+ Create an application and copy the client ID and secret
+ Run this command: `git clone https://github.com/devlocalhost/pyspodl`
+ Paste the client id and secret into the config file, inside the "pyspodl" directory.
+ Make sure you have git, then run `pip3 install git+https://github.com/kokarare1212/librespot-python`.
+ You will also need Pillow for the album cover, mutagen for tags, and toml to read fhe config file: `pip3 install Pillow mutagen toml`.
+ Now you can use pyspodl like this: `python3 pyspodl`

# the config file
Before you start using pyspodl, you need to fill out the config file. Open the config file and add your account email and password (line 2 and 3). Then set the `download_path`, line 11

## config entries
+ `email`: your account email
+ `password`: your accounts password
+ `token`: used to send request to spotify api. you do not need to touch this.
+ `client_id`: used to get the token
+ `client_secret`: used to get the token
+ `timeout`: tells the program to wait x seconds before downloading the next song from a playlist or album (to avoid account bans, but I never had an account get banned by using my program).
+ `premium_downloads`: download tracks in higher quality. only for premium accounts.
+ `download_path`: the path to download the tracks
+ `set_metadata`: set tags for the tracks
+ `track_format`: the format the tracks will be saved in. check the config file for possible entries

# help
Feel free to fork or make PR's (pull requests). If you're forking, please leave [this repos link](https://github.com/devlocalhost/pyspodl) in your readme and [kokarare1212's module repo link](https://github.com/kokarare1212/librespot-python).
If you have any problems/want to report a bug or request a feature, open an issue
