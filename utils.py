import base64
import os
import sys
import threading
import time

import requests

import librespot_patch

from librespot.core import Session
from mutagen.flac import Picture
from mutagen.oggvorbis import OggVorbis

from mutagen.oggvorbis import OggVorbisHeaderError
from mutagen.ogg import error



class Utils:
    TOKEN_LIFETIME = 3000  # spotify tokens last an hour, renew a bit earlier

    def __init__(self, config):
        self.config = config

        # the token lives in memory only, shared by all download threads
        self._token = None
        self._token_time = 0
        self._token_lock = threading.Lock()

    def generate_new_token(self):
        """
        tokens are not permament, they expire after an hour,
        so when invalid or old, requests a new one (call with the lock held)
        """

        client_id = self.config.get_config_value("account", "client_id")
        client_secret = self.config.get_config_value("account", "client_secret")

        resp = requests.post(
            "https://accounts.spotify.com/api/token",
            {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=10,
        ).json()

        if "access_token" not in resp:
            raise RuntimeError(
                f"[generate_new_token] No token received, check client_id and client_secret: {resp}"
            )

        self._token = resp["access_token"]
        self._token_time = time.time()

    def get_token(self, stale=None):
        """
        get the api token. pass the token that was just rejected (HTTP 401) as
        "stale" to renew it - unless another thread already did
        """

        with self._token_lock:
            if (
                self._token is None
                or self._token == stale
                or time.time() - self._token_time > self.TOKEN_LIFETIME
            ):
                self.generate_new_token()

            return self._token

    def set_metadata(self, metadata, cover_image, path):
        """
        set metadata to an ogg file (these are ogg tags, not id3!)
        """

        file = OggVorbis(path)

        for key, value in metadata.items():
            if value is None:
                continue

            if isinstance(value, list):
                file[key] = [str(v) for v in value]
            else:
                file[key] = str(value)

        try:
            resp = requests.get(cover_image["url"], timeout=10)
            picture = Picture()

            picture.data = resp.content
            picture.type = 17
            picture.mime = "image/jpeg"
            picture.width = cover_image["width"]
            picture.height = cover_image["height"]

            picture_data = picture.write()
            encoded_data = base64.b64encode(picture_data)
            vcomment_value = encoded_data.decode("ascii")

            file["metadata_block_picture"] = [vcomment_value]

        except requests.exceptions.RequestException:
            pass

        try:
            file.save()

        except (OggVorbisHeaderError, error):
            pass  # fuck you
            # seriously fuck it, idk why it happens

    def get_session(self, credentials_path, name="account", attempts=3):
        """
        create a user session from a credentials file and return it.
        connection problems are retried, a missing/broken file is reported clearly
        """

        librespot_patch.apply()  # several sessions must not share their state

        if not os.path.isfile(credentials_path):
            raise RuntimeError(
                f"[get_session] Credentials file of {name} not found: {credentials_path}"
            )

        # librespot would otherwise rewrite ./credentials.json (world readable)
        # and fill a ./cache directory on every login
        conf = (
            Session.Configuration.Builder()
            .set_store_credentials(False)
            .set_cache_enabled(False)
            .build()
        )

        print(f"[get_session] Trying to create a session for {name}...")

        for attempt in range(1, attempts + 1):
            try:
                return Session.Builder(conf).stored_file(credentials_path).create()

            except OSError as exc:  # connection refused/reset, timeouts: try again
                if attempt == attempts:
                    raise RuntimeError(
                        f"[get_session] Could not connect for {name}: {exc}"
                    ) from exc

                time.sleep(2 * attempt)

            except Exception as exc:
                raise RuntimeError(
                    f"[get_session] Could not create a session for {name}: {exc}\n"
                    "(wrong or expired credentials? run: pyspodl --add-account)"
                ) from exc

    def get_id_type_from_url(self, url):
        """
        get the id of the track or whatever, and the type of whatever (lol.)
        """

        try:
            return (url.split("/")[4].split("?")[0], url.split("/")[3])

        except IndexError:
            sys.exit(
                '[get_id_type_from_url] Invalid URL? Does it start with "https://open.spotify.com"?'
            )
