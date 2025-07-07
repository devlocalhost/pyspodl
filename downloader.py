import os
import sys
import time

import tqdm
import requests

from librespot.metadata import TrackId
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality


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

    def _get_track_metadata(self, url):
        """
        Fetches track metadata from Spotify API.
        """
        track_id_str = self.utils.get_id_type_from_url(url)[0]
        headers = {"Authorization": f"Bearer {self.utils.get_token()}"}
        resp = requests.get(
            f"https://api.spotify.com/v1/tracks/{track_id_str}",
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()  # Raise an exception for bad status codes
        return resp.json()

    def _get_path_from_metadata(self, metadata):
        """
        Constructs the final file path from metadata.
        """
        artist = metadata["artists"][0]["name"]
        track_title = metadata["name"]
        album_name = metadata["album"]["name"]
        album_release = metadata["album"]["release_date"]
        track_number = metadata["track_number"]

        filename_format = self.config.get_config_value("downloading", "track_format")
        filename = filename_format.format(
            artist=artist,
            title=track_title,
            album=album_name,
            tracknumber=track_number,
            year=album_release,
        )
        return f"{self.download_path}/{filename}.ogg"

    def get_track_urls(self, link):
        """
        get all tracks available in a playlist or album (spotify gives max 50 entries)
        """

        track_urls = []
        id_from_url = self.utils.get_id_type_from_url(link)

        url = (
            f"https://api.spotify.com/v1/{id_from_url[1] + 's'}/{id_from_url[0]}/tracks"
        )

        while True:
            try:
                headers = {"Authorization": f"Bearer {self.utils.get_token()}"}
                params = {"offset": 0, "limit": 50}

                response = requests.get(url, headers=headers, params=params, timeout=10)
                response_json = response.json()

                items = response_json["items"]
                url_next = response_json["next"]

                if url_next:
                    url = url_next

                for item in items:
                    try:
                        track_urls.append(
                            item["external_urls"]["spotify"]
                            if id_from_url[1] == "album"
                            else item["track"]["external_urls"]["spotify"]
                        )

                    except Exception as e:
                        print(f"[get_track_urls] Error making request: {e}")

                if len(track_urls) == response_json["total"]:
                    break

            except requests.exceptions.RequestException as e:
                print(f"[get_track_urls] Error making request: {e}")
                break

        return track_urls

    def download_playlist_or_album(self, link):
        """
        download songs off an album or playlist
        """

        all_track_urls = self.get_track_urls(link)
        if not all_track_urls:
            print("[download_playlist_or_album] No tracks found to download.")
            return

        print("[download_playlist_or_album] Checking for tracks to download...")

        tracks_to_download = []
        for url in tqdm.tqdm(all_track_urls, desc="Checking library"):
            try:
                metadata = self._get_track_metadata(url)
                path = self._get_path_from_metadata(metadata)

                if os.path.exists(path):
                    tqdm.tqdm.write(
                        f"[download_playlist_or_album] '{metadata['name']}' already exists, skipping."
                    )
                else:
                    tracks_to_download.append((url, metadata))
            except requests.exceptions.RequestException as e:
                tqdm.tqdm.write(
                    f"[download_playlist_or_album] Failed to get metadata for a track, skipping. Error: {e}"
                )

        total_to_download = len(tracks_to_download)
        print(f"[download_playlist_or_album] Found {total_to_download} new track(s) to download.")

        for count, (track_url, track_metadata) in enumerate(tracks_to_download):
            self.download_track(track_url, track_metadata)
            print(
                f"[download_playlist_or_album] Progress: {count + 1}/{total_to_download}\n"
            )

    def download_track(self, url, metadata):
        """
        download a track, metadata must be pre-fetched
        """
        try:
            timeout = self.config.get_config_value("downloading", "timeout")

            if timeout > 0:
                print(f"[download_track] Sleeping for {timeout} seconds...")
                time.sleep(timeout)

        except TypeError:
            sys.exit(
                '[download_track] "timeout" from config file must be a number (without quotes).'
            )

        resp = metadata
        artist = resp["artists"][0]["name"]  # artist
        track_title = resp["name"]  # title
        album_name = resp["album"]["name"]  # album
        album_release = resp["album"]["release_date"]  # date
        track_number = resp["track_number"]  # tracknumber
        cover_image = resp["album"]["images"][0]  # coverart, width, height

        quality = AudioQuality.VERY_HIGH if self.premium_downloads else AudioQuality.HIGH
        quality_str = "VERY_HIGH" if self.premium_downloads else "HIGH"

        print(f"[download_track] Requesting stream for '{track_title}' in {quality_str} quality.")

        track_id = TrackId.from_uri(
            f"spotify:track:{self.utils.get_id_type_from_url(url)[0]}"
        )
        try:
            stream = self.session.content_feeder().load(
                track_id, VorbisOnlyAudioQuality(quality), False, None
            )
        except RuntimeError as e:
            if "Failed fetching audio key" in str(e):
                print(
                    f"\n[download_track] ERROR: Could not get audio key for '{track_title}'.",
                    file=sys.stderr,
                )
                print(
                    "[download_track] This can happen due to regional restrictions, or if you're trying to download VERY_HIGH quality on a non-premium account.",
                    file=sys.stderr,
                )
                print(f"[download_track] Skipping this track. Original error: {e}\n", file=sys.stderr)
                return
            raise e

        path_filename_with_ext = self._get_path_from_metadata(metadata)
        path_filename = os.path.splitext(path_filename_with_ext)[0]

        print(f"[download_track] Downloading {track_title} by {artist}")

        directory_path = os.path.dirname(path_filename)

        if directory_path and not os.path.exists(directory_path):
            os.makedirs(directory_path)

        with (
            open(f"{path_filename}.ogg", "wb+") as track_file,
            tqdm.tqdm(
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                total=stream.input_stream.size,
                bar_format="{percentage:3.0f}%|{bar:16}|{n_fmt} / {total_fmt} | {rate_fmt}, ETA {remaining}",
            ) as progress_bar,
        ):
            chunk_size = 8192  # A common chunk size for I/O
            while True:
                chunk = stream.input_stream.stream().read(chunk_size)
                if not chunk:
                    break
                progress_bar.update(track_file.write(chunk))

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
            try:
                metadata = self._get_track_metadata(link)
                path = self._get_path_from_metadata(metadata)
                if os.path.exists(path):
                    print("[download] Track already exists, skipping.")
                else:
                    self.download_track(link, metadata)
            except requests.exceptions.RequestException as e:
                print(f"[download] Failed to get metadata for track: {e}", file=sys.stderr)

        elif link_type in ("album", "playlist"):
            self.download_playlist_or_album(link)

        else:
            sys.exit('[download] Invalid URL. URL must start with "open.spotify.com"')
