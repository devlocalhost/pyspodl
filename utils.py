import os
import sys
import base64

import requests
import toml

from librespot.core import Session
from mutagen.flac import Picture
from mutagen.oggvorbis import OggVorbis

from mutagen.oggvorbis import OggVorbisHeaderError
from mutagen.ogg import error

from config import ConfigError


class Utils:
    def __init__(self, config):
        self.config = config

    def generate_new_token(self):
        """
        tokens are not permament, they expire after an hour,
        so when invalid, regenerates a new one
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

        config = self.config.read_config()

        print("[generate_new_token] Trying to update token...")

        if config:
            config["account"]["token"] = resp["access_token"]

            try:
                with open("config.toml", "w", encoding="utf-8") as f:
                    toml.dump(config, f)
                    print("[generate_new_token] Token was updated")

            except Exception as e:
                sys.exit(
                    f"[generate_new_token] Error updating the configuration file: {e}\n\nManually update token from the config.toml file by yourself with: \"{resp['access_token']}\""
                )

        try:
            os.execv(sys.argv[0], sys.argv)

        except FileNotFoundError:
            sys.exit("[generate_new_token] Token was updated, run pyspodl again")

    def get_token(self):
        """
        gets the temporary saved token from the config file
        """

        try:
            token = self.config.get_config_value("account", "token")

        except ConfigError:
            self.generate_new_token()

        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(
            "https://api.spotify.com/v1/search?q=home+resonance&type=track",
            headers=headers,
            timeout=10,
        )

        if resp.status_code == 401:
            self.generate_new_token()

        return token

    def set_metadata(self, metadata, cover_image, filename):
        """
        set metadata to a file (these are ogg tags, not id3!)
        """

        file = OggVorbis(f"{filename}.ogg")

        for key, value in metadata.items():
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

    def get_session(self):
        """
        create a user session and return it
        """

        try:
            print("[get_session] Trying to create a session...")

            session = Session.Builder().stored_file(self.config.get_config_value("account", "credentials_file_path")).create()

            return session

        except Exception as exc:
            sys.exit(
                f"[get_session] An issue occured while trying to create session:\n{exc}"
            )

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
