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
        name, credentials_file_path, timeout, premium_downloads.

        accounts come from the [[accounts]] tables; a config without them
        (older format) uses the single [account] credentials_file_path.
        timeout and premium_downloads fall back to the [downloading] values.
        """

        config = self.read_config()
        defaults = config.get("downloading", {})

        entries = config.get("accounts")

        if not entries:
            path = config.get("account", {}).get("credentials_file_path")
            entries = [{"credentials_file_path": path}] if path else []

        accounts = []

        for number, entry in enumerate(entries, 1):
            path = entry.get("credentials_file_path")

            if not isinstance(path, str) or not path.strip():
                raise ConfigError(
                    f"[get_accounts] Account #{number} has no credentials_file_path."
                )

            timeout = entry.get("timeout", defaults.get("timeout", 0))

            if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
                raise ConfigError(
                    f'[get_accounts] "timeout" of account #{number} must be a number (without quotes).'
                )

            accounts.append(
                {
                    "name": str(entry.get("name") or f"account{number}"),
                    "credentials_file_path": path,
                    "timeout": timeout,
                    "premium_downloads": bool(
                        entry.get("premium_downloads", defaults.get("premium_downloads", False))
                    ),
                }
            )

        if not accounts:
            raise ConfigError(
                "[get_accounts] No account configured. Run: python3 pyspodl --setup"
            )

        return accounts
