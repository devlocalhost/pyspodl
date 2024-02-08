import argparse


def custom_help_formatter(prog):
    """fixing the ugly looking help menu"""

    return argparse.HelpFormatter(prog, max_help_position=46)


def get_arguments():
    """creating arguments"""
    parser = argparse.ArgumentParser(formatter_class=custom_help_formatter, description="pyspodl - a spotify downloader using librespot / https://github.com/devlocalhost/pyspodl")

    parser.add_argument("-l", "--link", type=str, help="link (s) to download, all in quotes, separated by a space: \"link1 link2 link3\"")
    parser.add_argument("-c", "--config-path", type=str, help="the path of the config file")

    return parser.parse_args()

if __name__ == "__main__":
    get_arguments()
