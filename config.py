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

    def __str__(self):
        return f"[Config] Using file {self.config_file}"

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
