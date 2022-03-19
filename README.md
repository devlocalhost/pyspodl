# pyspodl, a python script to download songs or playlists from spotify

using [librespot-python by kokarare1212](https://github.com/kokarare1212/librespot-python)'s module

# screenshots

![main](img1.png)
![playlist info](img2.png)
![track info](img3.png)
![playlist download](img4.png)
![track info example](img5.png)
![playlist info example](img6.png)
![playlist info example 2](img7.png)
![search result](img8.png)
![playlist downloading](img9.png)
![playlist downloading 2](img10.png)

# what can you do?

+ download songs
+ download playlists
+ get playlist or track info
+ search

# how to use

+ FIRST, youll need an client id and secret key. Get them by making a application on [spotify dashboard](https://developer.spotify.com/dashboard/applications)
+ create an application and copy client id and secret
![create app](createapp.png)
![client id and secret](https://i.imgur.com/Qfl2wxd.png)
+ git clone the repo
+ paste client id and secret in `main.py` on line 42 and 43 and `gettoken.py` on line 5 and 6
![mainpy file lines](mainpyfile.png)
![gettoken file lines](gettokenfile.png)
+ make sure you have python 3.6, and if on windows, **remove** the first line in __main.py__ file
+ make sure [the module](https://github.com/kokarare1212/librespot-python) and git is installed, then `pip3 install git+https://github.com/kokarare1212/librespot-python`
+ python3 main.py (or on linux chmod +x main.py && ./main.py)

---

youre free to fork and make PR's. if youre forking, **PLEASE** leave [this repos link](https://github.com/devlocalhost/pyspodl) on your readme, **AND** [kokarare1212's module repo link](https://github.com/kokarare1212/librespot-python). if you face any issues, **PLEASE** open an issue, or submit a PR