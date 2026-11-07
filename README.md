# pyspodl - a spotify downloader using librespot

Built on [librespot-python by kokarare1212](https://github.com/kokarare1212/librespot-python).

## What is different from other downloaders?
Maybe nothing. pyspodl does one thing: download tracks, albums, playlists and whole artists
straight from Spotify (it does not use another source) in "high" quality, or in
"very high" quality with a premium account. Tracks that already exist on disk are
skipped without any waiting, and you can download with several accounts at once.

## Contents
- [Installation](#installation)
- [Setup](#setup)
- [Multiple accounts](#multiple-accounts)
- [Usage](#usage)
- [Config file](#config-file)
- [Updating](#updating)
- [Troubleshooting](#troubleshooting)
- [Help](#help)

## Installation
You need `python3` (3.10 or newer) and `git`. Everything else is handled for you.

```sh
git clone https://github.com/devlocalhost/pyspodl
cd pyspodl
python3 pyspodl --setup
```

On the first run `pyspodl` creates a virtual environment in `.venv/` inside the project
directory, installs the dependencies from `requirements.txt` into it and restarts itself
there. Every later run uses that environment automatically (and installs anything that
is missing after an update). On Debian/Ubuntu you may need `sudo apt install python3-venv`.

If you prefer to manage the dependencies yourself (system packages, your own venv,
docker), install them with `pip install -r requirements.txt` and set
`PYSPODL_NO_VENV=1` to disable the automatic environment. Running pyspodl from a
virtual environment you activated yourself also works: missing packages are installed into it.

You also need the `librespot-auth` binary, which is used once to log in to Spotify.
You don't have to install it yourself on x86_64 Linux: if it isn't found, `--setup`
offers to download the latest prebuilt release from
[dspearson/librespot-auth](https://github.com/dspearson/librespot-auth) and unpacks it
into `bin/`. On other platforms, compile it (`cargo build --release`) and put it in
your `PATH`; the setup also accepts a full path.

## Setup
Everything (login, `credentials.json`, `config.toml`) is handled by one command:

```sh
python3 pyspodl --setup
```

The guided setup will:

1. **Ask for your Spotify API app.** Create one at the
   [Spotify dashboard](https://developer.spotify.com/dashboard) (any name; tick
   **Web API** only, the Web Playback SDK is not needed; any redirect URI such as
   `http://127.0.0.1:8888/callback` works), then paste its *Client ID* and
   *Client secret*.
2. **Ask for the download options** (directory, premium, wait time between
   downloads, tags, file naming). These are the defaults for every account.
3. **Log in your Spotify account(s).** It finds (or downloads) `librespot-auth` and runs
   `librespot-auth --name pyspodl --class tv` for you. Open the Spotify **desktop app**
   on a machine in the same network, click the "Connect to a device" button and pick
   **pyspodl**. The setup detects the generated credentials by itself (waits up to
   5 minutes), converts them to the format pyspodl needs and saves them as
   `credentials-<username>.json` next to the config (readable by your user only). No
   manual editing required. Then you can add another account, see below.

The result is `config.toml`. Use `-c /path/to/config.toml` together with `--setup` to write the config somewhere
else. Existing files are never overwritten without asking.

<details>
<summary>Manual setup (without <code>--setup</code>)</summary>

1. Run `librespot-auth --name "pyspodl" --class tv`, select "pyspodl" in the Spotify
   desktop app, and take the generated `credentials.json`.
2. Edit it:
   1. Replace `"auth_data"` with `"credentials"`
   2. Remove `"auth_type": 1,`
   3. Add `"type": "AUTHENTICATION_STORED_SPOTIFY_CREDENTIALS"` before the closing `}`

   The result should look like:
   ```json
   {"username": "BLABLA", "credentials": "BLABLABLA", "type": "AUTHENTICATION_STORED_SPOTIFY_CREDENTIALS"}
   ```
3. Create `config.toml` as described in [Config file](#config-file).
</details>

## Usage
```sh
python3 pyspodl -l LINK                       # one track, album, playlist or artist
python3 pyspodl -l "LINK1 LINK2 LINK3"        # several links, in quotes, space separated
python3 pyspodl -l LINK -c /path/to/config.toml
python3 pyspodl --setup                       # guided first-time setup
python3 pyspodl --add-account                 # log in one more account
python3 pyspodl -h                            # all options
```

Links must be `https://open.spotify.com/track|album|playlist|artist/...` URLs.

**Downloading an artist:** an artist link downloads all of the artist's albums and
singles (not compilations or "appears on" releases). The releases are looked up while
downloading, so it starts right away. A track that is listed more than once is only
downloaded once; the same file is never written twice.

**Skipping existing tracks:** before a track is downloaded, pyspodl checks whether the
target `.ogg` file already exists. If it does, the track is skipped immediately and the
`timeout` wait is **not** applied; only real downloads wait. Re-running a link
after an interrupted album/playlist download therefore continues right where it stopped.

## Multiple accounts
You can log in several Spotify accounts. Each account gets its **own session and its own
download thread** with its **own wait time**, and all accounts work on the **same**
track list: for an album, playlist or artist every account takes the next track that
nobody has claimed yet, so the job finishes roughly N times faster with N accounts.

- Add accounts during `--setup`, or later with `python3 pyspodl --add-account` (log the
  Spotify desktop app in to the other account first). The old config is saved as
  `config.toml.bak`.
- Every account has its own `timeout` and `premium_downloads` (see below); accounts without
  their own values use the ones from `[downloading]`.
- Progress bars are shown per account. A file only gets its final name when it is
  complete (unfinished downloads are `*.ogg.part` and are cleaned up), so an interrupted
  run never leaves broken files that would be skipped next time.
- If a track fails for one account, another account tries it. An account that fails
  three tracks in a row stops, the others continue. An account that can't log in at
  startup is skipped with a warning.
- Ctrl+C stops all accounts and removes unfinished files.

Note that downloading with several accounts at once is more visible to Spotify than a single
slow download; use reasonable wait times.

## Config file
`config.toml` is looked up in the current directory unless you pass `-c`. It contains
secrets, so it is not committed (see `.gitignore`) and `--setup` makes it private (mode 600).

```toml
[account]
client_id = ""      # from the Spotify dashboard
client_secret = ""  # from the Spotify dashboard

[downloading]
timeout = 2                    # default seconds to wait before each *new* download (0 = no wait)
premium_downloads = false      # default quality: true = "very high" (premium only)
download_path = "./Downloads"  # where tracks are saved
set_metadata = true            # write tags and cover art
track_format = "{artist}/{album}/{title}" # artist, album, title, tracknumber, year
# the format above saves a song as: download_path/Nas/Illmatic/The World Is Yours.ogg

# one table per account, each downloads on its own thread
[[accounts]]
name = "me@example.com"        # label shown in the output
credentials_file_path = "/home/me/pyspodl/credentials-me.json"
premium_downloads = true       # optional, overrides [downloading]
timeout = 30                   # optional, overrides [downloading]

[[accounts]]
name = "friend"
credentials_file_path = "/home/me/pyspodl/credentials-friend.json"
timeout = 45
```

An older config with a single `credentials_file_path` under `[account]` still works (it is
used as one account).

| Key | Meaning |
| --- | --- |
| `[[accounts]]` | One table per Spotify account: `credentials_file_path` (required, full path to the converted credentials file), `name` (label), `timeout` and `premium_downloads` (optional, override the defaults below). |
| `client_id`, `client_secret` | Credentials of your Spotify API app; used to request an API token (kept in memory and renewed automatically, the old `token` entry is no longer used). |
| `timeout` | Seconds an account waits before each new download, to be gentle with your account (no bans reported so far). Skipped tracks never wait, and every account waits independently. Must be a number without quotes. |
| `premium_downloads` | `true` for "very high" quality (premium only), otherwise "high". |
| `download_path` | Base directory for downloads. |
| `set_metadata` | Write artist, album, title, date, track/disc number and cover art as Ogg tags. |
| `track_format` | Path template below `download_path`; `.ogg` is appended. Available fields: `{artist}`, `{album}`, `{title}`, `{tracknumber}`, `{year}`. |

## Updating
Run `git pull` in the directory where you cloned pyspodl. New dependencies are installed on the next run.

## Troubleshooting
- **Dependency install fails**: `librespot-python` is installed from GitHub, so `git` and internet access are required. Delete `.venv/` to start over.
- **`librespot-auth` not found / download fails**: install it and add it to `PATH`, or enter its full path when the setup asks. Prebuilt releases exist for x86_64 Linux only.
- **"pyspodl" doesn't show up in Spotify**: the desktop app and the machine running the setup must be in the same network; use the desktop app, not the phone or web player.
- **Session / login errors**: the credentials may be stale. Run `python3 pyspodl --setup` again and choose to create new credentials.
- **`"timeout" ... must be a number`**: write `timeout = 2`, not `timeout = "2"`.
- **Token errors / HTTP 401**: check `client_id` and `client_secret`.
- **One account keeps failing**: re-run `python3 pyspodl --setup` or `--add-account` for it to create fresh credentials (an existing entry for the same user is skipped, delete it from the config first).

## Help
Feel free to fork or open pull requests. If you fork, please leave
[this repo's link](https://github.com/devlocalhost/pyspodl) in your readme, along with
[kokarare1212's module repo link](https://github.com/kokarare1212/librespot-python).
For problems, bug reports or feature requests, open an issue.
