"""
interactive first-time setup for pyspodl (run with: pyspodl --setup)

1. runs librespot-auth so you can authorize pyspodl from the spotify app
2. converts the generated credentials.json to the format librespot-python expects
3. asks for the spotify api client id / secret and the download options
4. writes config.toml
"""

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

import requests
import toml

CREDENTIALS_TYPE = "AUTHENTICATION_STORED_SPOTIFY_CREDENTIALS"
RELEASES_API = "https://api.github.com/repos/dspearson/librespot-auth/releases/latest"
# the project only publishes a prebuilt binary for this platform
RELEASE_ASSET_MARKER = "x86_64-linux-musl"
LOCAL_BIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")
AUTH_TIMEOUT = 300  # seconds to wait for the user to pick "pyspodl" in spotify


def ask(question, default=None, secret=False):
    """prompt the user, return the answer or the default when left empty"""

    suffix = f" [{default}]" if default not in (None, "") else ""

    while True:
        answer = input(f"{question}{suffix}: ").strip()

        if answer:
            return answer

        if default is not None:
            return default

        print("  A value is required.")


def ask_yes_no(question, default):
    """yes/no prompt"""

    hint = "Y/n" if default else "y/N"

    while True:
        answer = input(f"{question} [{hint}]: ").strip().lower()

        if not answer:
            return default

        if answer in ("y", "yes"):
            return True

        if answer in ("n", "no"):
            return False


def ask_number(question, default):
    """prompt for a non-negative number"""

    while True:
        answer = ask(question, default)

        try:
            value = float(answer)

            if value >= 0:
                return int(value) if value == int(value) else value

        except ValueError:
            pass

        print("  Please enter a number (0 or higher).")


def convert_credentials(data):
    """
    librespot-auth writes {"username", "auth_type", "auth_data"}, librespot-python
    wants {"username", "credentials", "type"}. already-converted files pass through.
    """

    if "credentials" in data and "type" in data:
        return data

    if "auth_data" not in data or "username" not in data:
        raise ValueError('missing "username" or "auth_data" in credentials file')

    return {
        "username": data["username"],
        "credentials": data["auth_data"],
        "type": CREDENTIALS_TYPE,
    }


def download_librespot_auth():
    """
    download the latest prebuilt librespot-auth from the github releases, unpack
    it into <pyspodl>/bin and return the path to the binary (None on failure)
    """

    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
        print(
            f"No prebuilt release for {platform.system()} {platform.machine()}, "
            "you need to compile it yourself."
        )
        return None

    try:
        release = requests.get(RELEASES_API, timeout=15).json()
        asset = next(
            a for a in release["assets"] if RELEASE_ASSET_MARKER in a["name"]
        )

        print(f"Downloading {asset['name']} ({release['tag_name']})...")

        with tempfile.TemporaryDirectory(prefix="pyspodl-dl-") as tmp:
            archive = os.path.join(tmp, asset["name"])

            with requests.get(
                asset["browser_download_url"], stream=True, timeout=30
            ) as response:
                response.raise_for_status()

                with open(archive, "wb") as file:
                    for chunk in response.iter_content(chunk_size=65536):
                        file.write(chunk)

            os.makedirs(LOCAL_BIN_DIR, exist_ok=True)
            target = os.path.join(LOCAL_BIN_DIR, "librespot-auth")

            # extract only the binary, written by us (never trust member paths)
            with tarfile.open(archive) as tar:
                member = next(
                    m
                    for m in tar.getmembers()
                    if m.isfile() and os.path.basename(m.name) == "librespot-auth"
                )

                with tar.extractfile(member) as source, open(target, "wb") as out:
                    shutil.copyfileobj(source, out)

            os.chmod(target, 0o755)

        print(f"Installed to {target}")
        return target

    except (requests.exceptions.RequestException, KeyError, StopIteration,
            tarfile.TarError, OSError) as exc:
        print(f"Automatic download failed: {exc!r}")
        return None


def find_librespot_auth():
    """
    locate the librespot-auth binary: PATH, then <pyspodl>/bin, then offer to
    download it from the releases, finally ask for a path
    """

    local = os.path.join(LOCAL_BIN_DIR, "librespot-auth")
    found = shutil.which("librespot-auth") or (
        local if os.access(local, os.X_OK) else None
    )

    if found:
        return found

    print(
        "\n'librespot-auth' was not found (PATH or ./bin).\n"
        "Project page: https://github.com/dspearson/librespot-auth"
    )

    if ask_yes_no("Download the latest prebuilt release from GitHub now?", True):
        downloaded = download_librespot_auth()

        if downloaded:
            return downloaded

    print("Compile it with `cargo build --release`, or grab a binary manually.")

    while True:
        path = os.path.expanduser(
            ask("Full path to the librespot-auth binary (empty to abort)", "")
        )

        if not path:
            sys.exit("Setup aborted.")

        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

        print("  Not an executable file, try again.")


def run_librespot_auth(binary):
    """
    run librespot-auth in a temp directory and wait for the credentials.json
    to show up. returns the parsed json.
    """

    with tempfile.TemporaryDirectory(prefix="pyspodl-auth-") as workdir:
        target = os.path.join(workdir, "credentials.json")

        print(
            "\nNow open the Spotify **desktop app** (same network as this machine),\n"
            'click the "Connect to a device" button and pick "pyspodl".\n'
            f"Waiting up to {AUTH_TIMEOUT // 60} minutes... (Ctrl+C to abort)\n"
        )

        process = subprocess.Popen(
            [binary, "--name", "pyspodl", "--class", "tv"], cwd=workdir
        )

        try:
            deadline = time.time() + AUTH_TIMEOUT

            while time.time() < deadline:
                if os.path.exists(target) and os.path.getsize(target) > 0:
                    time.sleep(1)  # let librespot-auth finish writing

                    try:
                        with open(target, encoding="utf-8") as file:
                            return json.load(file)

                    except json.JSONDecodeError:
                        pass  # still being written, try again

                if process.poll() is not None and not os.path.exists(target):
                    sys.exit(
                        f"librespot-auth exited (code {process.returncode}) "
                        "without creating credentials.json."
                    )

                time.sleep(1)

            sys.exit("Timed out waiting for authorization. Run the setup again.")

        finally:
            if process.poll() is None:
                process.terminate()

                try:
                    process.wait(timeout=5)

                except subprocess.TimeoutExpired:
                    process.kill()


def write_private(path, content):
    """write a file only the current user can read (it holds secrets)"""

    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)

    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        file.write(content)

    os.chmod(path, 0o600)


def confirm_overwrite(path):
    """ask before replacing an existing file"""

    return not os.path.exists(path) or ask_yes_no(f"{path} exists. Overwrite?", False)


def existing_usernames(directory):
    """usernames of the accounts already stored in the credentials directory"""

    names = set()

    if os.path.isdir(directory):
        for filename in os.listdir(directory):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(directory, filename), encoding="utf-8") as file:
                        names.add(json.load(file).get("username"))

                except (OSError, ValueError, AttributeError):
                    pass

    return names


def add_account(directory, defaults):
    """
    log in one more spotify account with librespot-auth and save it to
    <directory>/<username>.json together with its own settings
    (name, premium_downloads, timeout). returns the path, or None if skipped
    """

    print(
        "\nTo add an account, the Spotify desktop app must be logged in to THAT account.\n"
        "(To add a second account, log out in the app and log in with the other one.)"
    )

    raw = run_librespot_auth(find_librespot_auth())

    try:
        credentials = convert_credentials(raw)

    except ValueError as exc:
        sys.exit(f"Unexpected credentials.json from librespot-auth: {exc}")

    username = credentials["username"]

    if username in existing_usernames(directory):
        print(f"Account '{username}' is already configured, skipping.")
        return None

    path = os.path.join(directory, re.sub(r"[^A-Za-z0-9._-]", "_", username) + ".json")

    if not confirm_overwrite(path):
        sys.exit("Setup aborted, nothing changed.")

    # settings of this account, stored in its own file (change them there any time)
    credentials["name"] = username
    credentials["premium_downloads"] = ask_yes_no(
        f"Is '{username}' a premium account ('very high' quality)?",
        defaults["premium_downloads"],
    )
    credentials["timeout"] = ask_number(
        f"Seconds '{username}' waits between its downloads "
        "(independent of the other accounts, skipped tracks never wait)",
        defaults["timeout"],
    )

    os.makedirs(directory, mode=0o700, exist_ok=True)
    write_private(path, json.dumps(credentials, indent=2) + "\n")
    print(f"Account '{username}' saved to {path}")

    return path


def add_accounts_loop(directory, defaults):
    """keep adding accounts until the user is done; returns the saved paths"""

    saved = []

    while True:
        path = add_account(directory, defaults)

        if path:
            saved.append(path)

        if not ask_yes_no("Add another account?", False):
            return saved


def credentials_directory(config, config_file):
    """the directory the accounts live in (see Config.get_accounts)"""

    return os.path.join(
        os.path.dirname(config_file),
        os.path.expanduser(config.get("account", {}).get("credentials_dir", "credentials")),
    )


def add_account_to_config(config_path=None):
    """pyspodl --add-account: add accounts to an existing setup"""

    config_file = os.path.abspath(config_path or "config.toml")

    try:
        with open(config_file, encoding="utf-8") as file:
            config = toml.load(file)

    except FileNotFoundError:
        sys.exit(f"{config_file} not found. Run: python3 pyspodl --setup")

    defaults = {
        "premium_downloads": config.get("downloading", {}).get("premium_downloads", False),
        "timeout": config.get("downloading", {}).get("timeout", 2),
    }

    saved = add_accounts_loop(credentials_directory(config, config_file), defaults)
    print(f"\nAdded {len(saved)} account(s).")


def setup(config_path=None):
    """the setup wizard"""

    config_file = os.path.abspath(config_path or "config.toml")

    print("=== pyspodl setup ===")
    print(f"Config file: {config_file}\n")

    if not confirm_overwrite(config_file):
        sys.exit("Setup aborted, nothing changed.")

    # --- step 1: spotify api app --------------------------------------------
    print(
        "[1/3] Spotify API app\n"
        "Create an app at https://developer.spotify.com/dashboard (any name, tick\n"
        '"Web API", any redirect URI such as http://127.0.0.1:8888/callback), then\n'
        "copy its Client ID and Client secret from the app's settings."
    )
    client_id = ask("Client ID")
    client_secret = ask("Client secret")

    # --- step 2: download options -------------------------------------------
    print("\n[2/3] Download options (defaults for every account)")
    download_path = ask("Download directory", "./Downloads")
    premium = ask_yes_no("Premium accounts by default ('very high' quality)?", False)
    timeout = ask_number(
        "Seconds to wait between downloads (skipped tracks never wait)", 2
    )
    long_wait_chance = ask_number(
        "Chance in percent of a longer break after a downloaded song (0 = never)", 10
    )
    long_wait = (
        ask_number("Mean length of such a longer break in seconds", 120)
        if long_wait_chance > 0
        else 0
    )
    set_metadata = ask_yes_no("Write tags and cover art to the files?", True)
    track_format = ask(
        "Track path format (artist, album, title, tracknumber, year)",
        "{artist}/{album}/{tracknumber:02d} - {title}",
    )

    # --- step 3: accounts ---------------------------------------------------
    print(
        "\n[3/3] Spotify accounts\n"
        "Every account downloads at the same time, each with its own wait time,\n"
        "all working on the same album, playlist or artist."
    )
    config = {
        "account": {"client_id": client_id, "client_secret": client_secret},
        "downloading": {
            "timeout": timeout,
            "premium_downloads": premium,
            "long_wait_chance": min(long_wait_chance, 100) / 100,
            "long_wait": long_wait,
            "download_path": download_path,
            "set_metadata": set_metadata,
            "track_format": track_format,
        },
    }

    saved = add_accounts_loop(
        credentials_directory(config, config_file),
        {"premium_downloads": premium, "timeout": timeout},
    )

    if not saved:
        sys.exit("No account was added, nothing written.")

    write_private(config_file, toml.dumps(config))

    print(
        f"\nDone! Config written to {config_file} ({len(saved)} account(s) in {credentials_directory(config, config_file)})\n"
        'Try it: python3 pyspodl -l "https://open.spotify.com/track/..."\n'
        "Add more accounts later with: python3 pyspodl --add-account"
    )
