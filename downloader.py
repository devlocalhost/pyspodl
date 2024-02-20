import os
import sys
import time

import tqdm
import requests

from librespot.metadata import TrackId
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality

from config import Config
from utils import Utils


class Downloader:
    """
    where the magic happens.
    """

    def __init__(self, config, utils):
        """
        define some values i guess...?
        """

        self.config = config
        self.utils = utils

        self.session = self.utils.get_session()

        self.premium_downloads = self.config.get_config_value(
            "downloading", "premium_downloads"
        )
        self.download_path = self.config.get_config_value(
            "downloading", "download_path"
        )
        self.set_metadata = self.config.get_config_value("downloading", "set_metadata")

    def __str__(self):
        return f"Premium? {self.premium_downloads}, Download path? {self.download_path}, Metadata? {self.set_metadata}"

    def get_track_urls(self, link):
        """
        get all tracks available in a playlist or album (spotify gives max 50 entries)
        """

        track_urls = []
        offset = 0
        limit = 100
        id_from_url = self.utils.get_id_type_from_url(link)

        url = (
            f"https://api.spotify.com/v1/{id_from_url[1] + 's'}/{id_from_url[0]}/tracks"
        )

        while True:
            try:
                headers = {"Authorization": f"Bearer {self.utils.get_token()}"}
                params = {"offset": offset, "limit": limit}

                response = requests.get(url, headers=headers, params=params, timeout=10)
                items = response.json().get("items", [])

                if not items:
                    break

                track_urls.extend(
                    # item["track"]["id"]
                    item["track"]["external_urls"]["spotify"]
                    for item in items
                    if "track" in item and item["track"]
                )

                offset += limit

            except requests.exceptions.RequestException as e:
                print(f"[get_track_urls] Error making request: {e}")
                break

        return track_urls

    def download_playlist_or_album(self, link):
        """
        download songs off an album or playlist
        """

        tracks = self.get_track_urls(link)

        for track in tracks:
            self.download_track(track)  # sends id

    def download_track(self, url):
        """
        download an track
        """

        try:
            timeout = self.config.get_config_value("downloading", "timeout")

            if timeout > 0:
                print(f"[download_track] Sleeping for {timeout} seconds...")
                time.sleep(timeout)

        except TypeError:
            sys.exit(
                '[download_playlist_or_album] "timeout" from config file must be a number (without quotes).'
            )

        track_id = TrackId.from_uri(
            f"spotify:track:{self.utils.get_id_type_from_url(url)[0]}"
        )
        headers = {"Authorization": f"Bearer {self.utils.get_token()}"}

        resp = requests.get(
            f"https://api.spotify.com/v1/tracks/{self.utils.get_id_type_from_url(url)[0]}",
            headers=headers,
            timeout=10,
        ).json()

        artist = resp["artists"][0]["name"]  # artist
        track_title = resp["name"]  # title
        album_name = resp["album"]["name"]  # album
        album_release = resp["album"]["release_date"].split("-")[0]  # date
        track_number = resp["track_number"]  # tracknumber
        cover_image = resp["album"]["images"][0]  # coverart, width, height

        if self.premium_downloads:
            stream = self.session.content_feeder().load(
                track_id, VorbisOnlyAudioQuality(AudioQuality.VERY_HIGH), False, None
            )

        else:
            stream = self.session.content_feeder().load(
                track_id, VorbisOnlyAudioQuality(AudioQuality.HIGH), False, None
            )

        filename_format = self.config.get_config_value("downloading", "track_format")
        filename = filename_format.format(
            artist=artist,
            title=track_title,
            album=album_name,
            tracknumber=track_number,
            year=album_release,
        )

        print(f"Downloading {track_title} by {artist}")

        path_filename = f"{self.download_path}/{filename}"

        if os.path.exists(path_filename + ".ogg"):
            print("Track exists, skipping")

        else:
            directory_path = os.path.dirname(path_filename)

            if directory_path and not os.path.exists(directory_path):
                os.makedirs(directory_path)

            with open(f"{path_filename}.ogg", "wb+") as track_file, tqdm.tqdm(
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                total=stream.input_stream.size,
                bar_format="{percentage:3.0f}%|{bar:16}|{n_fmt} / {total_fmt} | {rate_fmt}, ETA {remaining}",
            ) as progress_bar:
                for _ in range(int(stream.input_stream.size / 5000) + 1):
                    progress_bar.update(
                        track_file.write(stream.input_stream.stream().read(50000))
                    )

            if self.set_metadata:
                tags = {
                    "artist": artist,
                    "title": track_title,
                    "album": album_name,
                    "date": album_release,  # .split("-")[0],
                    "tracknumber": track_number,
                }

                self.utils.set_metadata(tags, cover_image, path_filename)

    def download(self, link):
        """
        execute the function based on the link
        """

        link_type = self.utils.get_id_type_from_url(link)[1]

        if link_type == "track":
            self.download_track(link)

        elif link_type in ("album", "playlist"):
            self.download_playlist_or_album(link)

        else:
            sys.exit('[download] Invalid URL. URL must start with "open.spotify.com"')
