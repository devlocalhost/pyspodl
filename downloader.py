import collections
import os
import random
import sys
import threading
import time

import tqdm
import requests

from librespot.metadata import TrackId
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality

WAIT_VARIATION = 0.2  # waits vary randomly by +/- 20% around the configured mean
MAX_CONSECUTIVE_FAILURES = 3  # a worker with this many failures in a row gives up


class Downloader:
    """
    where the magic happens.

    every configured account gets its own session and its own worker thread.
    all workers take tracks from one shared stream, so they work on the same
    track, album, playlist or artist together - each with its own wait time.
    """

    def __init__(self, config, utils):
        """
        define some values i guess...? and log in all accounts
        """

        self.config = config
        self.utils = utils

        self.download_path = self.config.get_config_value(
            "downloading", "download_path"
        )
        self.set_metadata = self.config.get_config_value("downloading", "set_metadata")

        self.lock = threading.Lock()  # guards everything below
        self.stop = threading.Event()  # set on ctrl+c, ends all workers

        self.in_progress = set()  # target files that are being downloaded right now
        self.part_files = set()  # unfinished *.part files (removed on abort)
        self.source = iter(())  # shared stream of track urls
        self.seen = set()
        self.retry = collections.deque()  # (url, accounts that already failed it)
        self.alive = set()  # names of the accounts whose worker is still running
        self.active = 0
        self.stats = {}
        self.failed = []

        try:
            self.utils.get_token()  # fail early on a wrong client id / secret

        except RuntimeError as exc:
            sys.exit(str(exc))

        self.accounts = []

        for account in self.config.get_accounts():
            try:
                account["session"] = self.utils.get_session(
                    account["credentials_file_path"], account["name"]
                )
                account["index"] = len(self.accounts)
                self.accounts.append(account)

                try:
                    free = account["session"].get_user_attribute("type") == "free"

                except Exception:  # pylint: disable=broad-except
                    free = False

                if free:
                    print(
                        f"[Downloader] WARNING: {account['name']} is a free account. Spotify "
                        "refuses audio keys to free accounts, downloads will most likely fail."
                    )

            except RuntimeError as exc:
                print(f"{exc}\nContinuing without {account['name']}.")

        if not self.accounts:
            sys.exit("[Downloader] None of the accounts could log in.")

        print(f"[Downloader] Logged in with {len(self.accounts)} account(s)")

    # ------------------------------------------------------------------ api

    def log(self, account, message):
        """print a message without breaking the progress bars"""

        tqdm.tqdm.write(f"[{account['name']}] {message}")

    def api_get(self, url, params=None):
        """
        GET from the spotify web api. renews an expired token and waits when
        spotify says "too many requests" (shared by all threads)
        """

        response = None

        for _ in range(6):
            token = self.utils.get_token()
            response = requests.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params=params,
                timeout=10,
            )

            if response.status_code == 401:
                self.utils.get_token(stale=token)

            elif response.status_code == 429:
                try:
                    delay = min(int(response.headers.get("Retry-After", 5)), 60) + 1

                except ValueError:
                    delay = 6

                tqdm.tqdm.write(f"[api] Rate limited, waiting {delay} seconds...")

                if self.stop.wait(delay):
                    raise RuntimeError("interrupted")

            else:
                break

        return response

    def get_track_urls(self, link):
        """
        get all tracks available in a playlist or album (spotify gives max 50 entries per page)
        """

        track_urls = []
        id_from_url = self.utils.get_id_type_from_url(link)

        url = (
            f"https://api.spotify.com/v1/{id_from_url[1] + 's'}/{id_from_url[0]}/tracks"
        )
        params = {"limit": 50}

        # follow the "next" links until spotify has no more pages
        while url:
            try:
                response = self.api_get(url, params)
                response.raise_for_status()
                response_json = response.json()

            except (requests.exceptions.RequestException, ValueError) as e:
                print(f"[get_track_urls] Error making request: {e}")
                break

            for item in response_json["items"]:
                try:
                    track = item if id_from_url[1] == "album" else item["track"]
                    track_urls.append(track["external_urls"]["spotify"])

                except (KeyError, TypeError) as e:
                    # e.g. local files or unavailable tracks in playlists
                    print(f"[get_track_urls] Skipping unreadable item: {e!r}")

            # the "next" url already contains all query parameters
            url = response_json.get("next")
            params = None

        return track_urls

    def get_artist_album_urls(self, link):
        """
        get all albums and singles of an artist (spotify gives max 10 entries per page)
        """

        artist_id = self.utils.get_id_type_from_url(link)[0]
        album_urls = []

        url = f"https://api.spotify.com/v1/artists/{artist_id}/albums"
        params = {"include_groups": "album,single", "limit": 10}

        while url:
            try:
                response = self.api_get(url, params)
                response.raise_for_status()
                response_json = response.json()

            except (requests.exceptions.RequestException, ValueError) as e:
                print(f"[get_artist_album_urls] Error making request: {e}")
                break

            for item in response_json["items"]:
                album_url = item["external_urls"]["spotify"]

                if album_url not in album_urls:
                    album_urls.append(album_url)

            # the "next" url already contains all query parameters
            url = response_json.get("next")
            params = None

        return album_urls

    def iter_track_urls(self, link, link_type):
        """
        yield the track urls of a link one by one. albums of an artist are
        only looked up when the workers get there, so downloading starts at once
        """

        if link_type == "track":
            yield link

        elif link_type in ("album", "playlist"):
            yield from self.get_track_urls(link)

        elif link_type == "artist":
            albums = self.get_artist_album_urls(link)
            print(f"[download] Found {len(albums)} releases")

            for album in albums:
                yield from self.get_track_urls(album)

    # -------------------------------------------------------------- workers

    def prune_retry(self):
        """
        give up on retries that no running account can still take
        (call with the lock held)
        """

        for url, tried in list(self.retry):
            if not self.alive - tried:
                self.retry.remove((url, tried))
                self.failed.append(url)

    def next_track(self, account):
        """
        hand out the next job to a worker, atomically.
        returns ("track", (url, tried)), ("wait", None) when other workers
        may still requeue a failed track, or ("done", None).
        a failed track is only given to accounts that have not failed it yet
        """

        with self.lock:
            self.prune_retry()

            for item in self.retry:
                if account["name"] not in item[1]:
                    self.retry.remove(item)
                    self.active += 1
                    return "track", item

            try:
                for url in self.source:
                    if url in self.seen:
                        continue

                    self.seen.add(url)
                    self.active += 1
                    return "track", (url, frozenset())

            except Exception as exc:  # pylint: disable=broad-except
                print(f"[next_track] Could not list more tracks: {exc}")

            return ("wait", None) if self.active or self.retry else ("done", None)

    def wait_before_download(self, account):
        """
        sleep before a download. the account's "timeout" is the mean, every wait is
        randomly 20% shorter or longer so the requests don't follow a fixed rhythm.
        after a song the account may have rolled a longer break ("long_wait"), which
        is then taken instead of the normal wait.
        only called when a track is really going to be downloaded, never for skipped tracks
        """

        mean = account["timeout"]
        longer = account.pop("long_wait_due", False)

        if longer:
            mean = account["long_wait"]  # the longer break replaces the normal wait

        if mean > 0:
            delay = mean * random.uniform(1 - WAIT_VARIATION, 1 + WAIT_VARIATION)
            self.log(
                account,
                f"{'Taking a longer break:' if longer else 'Sleeping for'} {delay:.1f} seconds...",
            )

            if self.stop.wait(delay):
                raise RuntimeError("interrupted")

    def download_track(self, url, account):
        """
        download a track with one account, returns "downloaded" or "skipped"
        """

        track_id_str = self.utils.get_id_type_from_url(url)[0]
        track_id = TrackId.from_uri(f"spotify:track:{track_id_str}")

        response = self.api_get(f"https://api.spotify.com/v1/tracks/{track_id_str}")
        response.raise_for_status()
        resp = response.json()

        album_artist = resp["artists"][0]["name"]  # albumartist
        artists = [a["name"] for a in resp["artists"]]  # artist
        track_title = resp["name"]  # title
        album_name = resp["album"]["name"]  # album
        album_release = resp["album"]["release_date"]  # date
        track_number = resp["track_number"]  # tracknumber
        disc_number = resp["disc_number"]  # discnumber
        cover_image = resp["album"]["images"][0]  # coverart, width, height

        filename_format = self.config.get_config_value("downloading", "track_format")
        filename = filename_format.format(
            artist=album_artist,
            title=track_title,
            album=album_name,
            tracknumber=track_number,
            year=album_release,
        )

        final_path = f"{self.download_path}/{filename}.ogg"
        part_path = final_path + ".part"  # only a finished file gets the real name

        # an existing track (or one another account is working on) is skipped
        # *before* any waiting or streaming, so it never costs any timeout
        with self.lock:
            skip = os.path.exists(final_path) or final_path in self.in_progress

            if not skip:
                self.in_progress.add(final_path)

        if skip:
            self.log(account, f"Track exists, skipping: {track_title} by {album_artist}")
            return "skipped"

        try:
            self.wait_before_download(account)

            self.log(account, f"Downloading {track_title} by {album_artist}")

            quality = (
                AudioQuality.VERY_HIGH
                if account["premium_downloads"]
                else AudioQuality.HIGH
            )
            stream = account["session"].content_feeder().load(
                track_id, VorbisOnlyAudioQuality(quality), False, None
            )

            directory_path = os.path.dirname(final_path)

            if directory_path:
                os.makedirs(directory_path, exist_ok=True)

            with self.lock:
                self.part_files.add(part_path)

            with (
                open(part_path, "wb+") as track_file,
                tqdm.tqdm(
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    total=stream.input_stream.size,
                    desc=account["name"],
                    position=account["index"],
                    leave=False,
                    bar_format="{desc}: {percentage:3.0f}%|{bar:16}|{n_fmt} / {total_fmt} | {rate_fmt}, ETA {remaining}",
                ) as progress_bar,
            ):
                for _ in range(int(stream.input_stream.size / 5000) + 1):
                    if self.stop.is_set():
                        raise RuntimeError("interrupted")

                    progress_bar.update(
                        track_file.write(stream.input_stream.stream().read(50000))
                    )

            if self.set_metadata:
                tags = {
                    "artist": artists,
                    "albumartist": album_artist,
                    "title": track_title,
                    "album": album_name,
                    "date": album_release,  # .split("-")[0],
                    "tracknumber": track_number,
                    "tracktotal": resp["album"].get("total_tracks"),
                    "discnumber": disc_number,
                }

                self.utils.set_metadata(tags, cover_image, part_path)

            os.replace(part_path, final_path)

        except BaseException:
            self.remove_part_file(part_path)
            raise

        finally:
            with self.lock:
                self.in_progress.discard(final_path)
                self.part_files.discard(part_path)

        return "downloaded"

    @staticmethod
    def remove_part_file(path):
        """delete an unfinished download, ignoring files that are already gone"""

        try:
            os.remove(path)

        except OSError:
            pass

    def abort(self, threads):
        """
        stop all workers after ctrl+c / SIGTERM: give them a moment to clean up
        after themselves, then delete whatever unfinished files are left (a
        worker stuck in a network read can't react before the program ends)
        """

        self.stop.set()
        print("\n[download] Interrupted, cleaning up...")

        try:
            deadline = time.time() + 5

            for thread in threads:
                thread.join(max(0, deadline - time.time()))

        except KeyboardInterrupt:
            pass  # impatient: skip the waiting, still clean up below

        for path in list(self.part_files):
            self.remove_part_file(path)

        sys.exit(130)

    def worker(self, account):
        """
        one thread per account: take tracks from the shared stream until it is empty
        """

        failures = 0

        try:
            while not self.stop.is_set():
                state, item = self.next_track(account)

                if state == "done":
                    return

                if state == "wait":
                    self.stop.wait(1)
                    continue

                url, tried = item

                try:
                    status = self.download_track(url, account)
                    failures = 0

                    # after a finished song there is a chance for a longer break
                    # before the next download (so nothing waits at the very end)
                    if status == "downloaded" and random.random() < account["long_wait_chance"]:
                        account["long_wait_due"] = True

                    with self.lock:
                        self.stats[account["name"]][status] += 1

                except Exception as exc:  # pylint: disable=broad-except
                    if self.stop.is_set():
                        return

                    failures += 1
                    self.log(account, f"Failed {url}: {exc!r}")

                    with self.lock:
                        tried = tried | {account["name"]}

                        if self.alive - tried:
                            self.retry.append((url, tried))  # another account tries it
                        else:
                            self.failed.append(url)

                    if failures >= MAX_CONSECUTIVE_FAILURES:
                        self.log(
                            account, "Too many failures in a row, stopping this account."
                        )
                        return

                finally:
                    with self.lock:
                        self.active -= 1

        finally:
            with self.lock:
                self.alive.discard(account["name"])
                self.prune_retry()

    def download(self, link):
        """
        download a track, album, playlist or artist with all accounts at once
        """

        link_type = self.utils.get_id_type_from_url(link)[1]

        if link_type not in ("track", "album", "playlist", "artist"):
            sys.exit('[download] Invalid URL. URL must start with "open.spotify.com"')

        self.source = self.iter_track_urls(link, link_type)
        self.seen = set()
        self.retry.clear()
        self.failed = []
        self.active = 0
        self.alive = {a["name"] for a in self.accounts}
        self.stats = {
            a["name"]: collections.Counter() for a in self.accounts
        }

        threads = [
            threading.Thread(target=self.worker, args=(account,), daemon=True)
            for account in self.accounts
        ]

        for thread in threads:
            thread.start()

        try:
            while any(thread.is_alive() for thread in threads):
                for thread in threads:
                    thread.join(0.5)

        except KeyboardInterrupt:
            self.abort(threads)

        print("\n[download] Summary")

        for name, counter in self.stats.items():
            print(
                f"  {name}: {counter['downloaded']} downloaded, {counter['skipped']} skipped"
            )

        if self.failed:
            print(f"  {len(self.failed)} track(s) failed:")

            for url in self.failed:
                print(f"    {url}")
