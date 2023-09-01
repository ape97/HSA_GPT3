import os
from enum import Enum


class LogLevel(Enum):
    INFO = '\033[94m'     # blue
    QUESTION = '\033[93m'  # yellow
    ERROR = '\033[91m'    # red
    RESET = '\033[0m'     # default


def custom_print(message, log_level=None):

    YELLOW = '\033[93m'
    RESET = '\033[0m'

    if log_level:
        if isinstance(log_level, LogLevel):
            color = log_level.value
        else:
            color = ''
    else:
        color = YELLOW

    print(f"{color}{message}{RESET}")


def custom_input(message):
    YELLOW = '\033[93m'
    RESET = '\033[0m'

    user_input = input(f"{YELLOW}{message}{RESET}")
    return user_input


def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
        custom_print(f"Verzeichnis {directory} erstellt.", LogLevel.INFO)


def print_header(title):
    print("=" * 40)
    print("GPT3-Trainer Hochschulassistent")
    print(title)
    print("="*40)
