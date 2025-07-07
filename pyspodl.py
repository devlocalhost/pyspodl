#!/usr/bin/env python3

"""
pyspodl - a spotify downloader using librespot
"""

import logging
from arguments import get_arguments

from downloader import Downloader
from config import Config
from utils import Utils

def main():
    logging.basicConfig(level=logging.INFO)

    arguments = get_arguments()
    config = Config(arguments.config_path)
    utils = Utils(config)

    downloader = Downloader(config, utils)

    if not arguments.link:
        print("[main] No download links provided. Use -l or --link. Exiting.")
        return

    for link in arguments.link.split(" "):
        downloader.download(link)

    utils.clear_token()


if __name__ == "__main__":
    main()
