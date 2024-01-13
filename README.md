# pyspodl - a spotify downloader using librespot

using [librespot-python by kokarare1212](https://github.com/kokarare1212/librespot-python)'s module

# important
I will possibly not work on pyspodl anymore. I dont want to work on this program anymore, im just tired of it. So please, dont expect new features. I will of course update the program if a bug or issue is found, i just wont add any features. [Feel free to fork and add your own features](#helping)

# whats different than the other downloaders?
well, maybe nothing. pyspodl can only do these: download tracks, albums and playlists, at "High" (non premium) and "Very High" (premium account needed) quality. It downloads them from spotify, it does not use a different source like some other programs do.

# how to use
+ First, you'll need a client ID and secret key. Get them by making a application in [spotify dashboard](https://developer.spotify.com/dashboard/applications)
+ Create an application and copy the client ID and secret
![creating an application in Spotify dashboard](screens/createapp.png)
![copying client id and secret](https://i.imgur.com/Qfl2wxd.png)
+ git clone the repo
+ Paste client id and secret on the config file
+ Make sure you have python 3.6+, git, and then `pip3 install git+https://github.com/kokarare1212/librespot-python`
+ You will also need to install [music-tag](https://pypi.org/project/music-tag/) and [pil (pillow)](https://pypi.org/project/Pillow/): `pip install music-tag Pillow`
+ python3 pyspodl (or on linux chmod +x pyspodl && ./pyspodl)

# the config file
Before starting to use pyspodl, you need to fill the config file. Open the config file, and add your accounts email and password (line 2 and 3). After that, set the `download_path`, line 11

## config entries
+ `email`: your accounts email
+ `password`: your accounts password
+ `token`: used for sending request to the spotify api. you do not need to touch that
+ `client_id`: used to get the token
+ `client_secret`: used to get the token
+ `timeout`: tells the program to wait x seconds before downloading the next song from a playlist or album (to avoid account ban, but i never had anm account banned by using my program)
+ `premium_downloads`: download tracks at a higher quality. only for premium accounts
+ `download_path`: the path to download the tracks
+ `set_metadata`: sets tags to the tracks
+ `track_format`: the format the songs will be saved

# helping
Feel free to fork or make PR's (Pull requests). If you're forking, please leave [this repos link](https://github.com/devlocalhost/pyspodl) on your readme, and [kokarare1212's module repo link](https://github.com/kokarare1212/librespot-python).
If you face any issues/want to report a bug, or want to request a feature, open a issue
