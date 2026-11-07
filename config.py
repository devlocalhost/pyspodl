import json
import os
import sys

import toml


class ConfigError(Exception):
    """
    triggered when theres an issue with the config file
    """


class Config:
    """
    config related functions
    """

    def __init__(self, config_path=None):
        self.config_file = (
            os.path.abspath(config_path)
            if config_path
            else os.path.abspath("config.toml")
        )

    def read_config(self):
        """
        read the config file and return the data
        """

        try:
            with open(self.config_file, encoding="utf-8") as config_file:
                return toml.load(config_file)

        except FileNotFoundError:
            sys.exit(f'[read_config] Config file "{self.config_file}" not found.')

    def get_config_value(self, section, key):
        """
        get value from config file
        """

        config = self.read_config()
        value = config.get(section).get(key)

        if value is None or (isinstance(value, str) and not value.strip()):
            raise ConfigError(
                f"[get_config_value] Value for '{key}' in section '{section}' is missing or blank."
            )

        return value

    def get_accounts(self):
        """
        return the list of accounts to download with. every account has:
        name, credentials_file_path, timeout, premium_downloads,
        long_wait_chance, long_wait.

        accounts are the *.json files in the credentials directory (default:
        "credentials" next to the config file, or [account] credentials_dir).
        besides the login data written by the setup, such a file may contain
        its own settings, which override the [downloading] defaults:
            "name", "timeout", "premium_downloads", "long_wait_chance",
            "long_wait", "enabled" (false = skip it)
        accounts of older configs ([[accounts]] tables or a single
        [account] credentials_file_path) are still used.
        """

        config = self.read_config()
        defaults = config.get("downloading", {})
        base_dir = os.path.dirname(self.config_file)

        credentials_dir = os.path.join(
            base_dir,
            os.path.expanduser(config.get("account", {}).get("credentials_dir", "credentials")),
        )

        entries = []  # (path, settings)

        if os.path.isdir(credentials_dir):
            for filename in sorted(os.listdir(credentials_dir)):
                path = os.path.join(credentials_dir, filename)

                if not filename.endswith(".json") or not os.path.isfile(path):
                    continue

                try:
                    with open(path, encoding="utf-8") as file:
                        data = json.load(file)

                except (OSError, ValueError) as exc:
                    raise ConfigError(f"[get_accounts] Cannot read {path}: {exc}") from exc

                if not isinstance(data, dict) or "username" not in data:
                    raise ConfigError(f'[get_accounts] {path} has no "username".')

                entries.append((path, data))

        # older config formats
        known = {os.path.abspath(path) for path, _ in entries}
        legacy = list(config.get("accounts") or [])
        single = config.get("account", {}).get("credentials_file_path")

        if single:
            legacy.append({"credentials_file_path": single})

        for entry in legacy:
            path = entry.get("credentials_file_path")

            if not isinstance(path, str) or not path.strip():
                raise ConfigError("[get_accounts] An [[accounts]] entry has no credentials_file_path.")

            if os.path.abspath(path) not in known:
                known.add(os.path.abspath(path))
                entries.append((path, entry))

        accounts = []
        usernames = set()

        for number, (path, settings) in enumerate(entries, 1):
            if settings.get("enabled", True) is False:
                continue

            username = settings.get("username")

            if username is not None and username in usernames:
                print(f"[get_accounts] {path}: account {username} is configured twice, ignoring this one.")
                continue

            if username is not None:
                usernames.add(username)

            timeout = settings.get("timeout", defaults.get("timeout", 0))

            if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
                raise ConfigError(
                    f'[get_accounts] "timeout" in {path} must be a number (without quotes).'
                )

            long_wait_chance = settings.get(
                "long_wait_chance", defaults.get("long_wait_chance", 0)
            )
            long_wait = settings.get("long_wait", defaults.get("long_wait", 0))

            if (
                isinstance(long_wait_chance, bool)
                or not isinstance(long_wait_chance, (int, float))
                or not 0 <= long_wait_chance <= 1
            ):
                raise ConfigError(
                    f'[get_accounts] "long_wait_chance" in {path} must be a number from 0 to 1 (0.1 = 10%).'
                )

            if isinstance(long_wait, bool) or not isinstance(long_wait, (int, float)) or long_wait < 0:
                raise ConfigError(
                    f'[get_accounts] "long_wait" in {path} must be a number of seconds (0 or more).'
                )

            accounts.append(
                {
                    "name": str(settings.get("name") or username or f"account{number}"),
                    "long_wait_chance": long_wait_chance,
                    "long_wait": long_wait,
                    "credentials_file_path": path,
                    "timeout": timeout,
                    "premium_downloads": bool(
                        settings.get("premium_downloads", defaults.get("premium_downloads", False))
                    ),
                }
            )

        if not accounts:
            raise ConfigError(
                f"[get_accounts] No (enabled) account found in {credentials_dir}. "
                "Run: python3 pyspodl --setup or --add-account"
            )

        return accounts
