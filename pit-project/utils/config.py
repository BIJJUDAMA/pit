# What it does: Manages all read/write operations for the `.pit/config` file
# What data structure it uses: Map / Hash Table / Dictionary (the INI file format is a map of sections to key-value pairs, managed by Python's `configparser`)

import configparser
import os
from .repository import find_repo_root
def get_global_config_path():
    return os.path.expanduser("~/.pitconfig")

def read_global_config():
    config = configparser.ConfigParser()
    global_path = get_global_config_path()
    if os.path.exists(global_path):
        config.read(global_path)
    return config


def get_config_path(repo_root):  # Returns the path to the config file within the repository
    return os.path.join(repo_root, '.pit', 'config')

def read_config():
    merged_config = configparser.ConfigParser()

    # 1. Read global config
    global_config = read_global_config()
    merged_config.read_dict(global_config)

    # 2. Read local repo config (overrides global)
    repo_root = find_repo_root()
    if repo_root:
        local_config_path = get_config_path(repo_root)
        if os.path.exists(local_config_path):
            local_config = configparser.ConfigParser()
            local_config.read(local_config_path)
            merged_config.read_dict(local_config)

    return merged_config


def write_config(key, value): # Sets a configuration key to a value and writes it to the config file
    repo_root = find_repo_root()
    if not repo_root:
        raise FileNotFoundError("Not a Pit repository.")

    config_path = get_config_path(repo_root)
os.makedirs(os.path.dirname(config_path), exist_ok=True)
config = configparser.ConfigParser()

    if os.path.exists(config_path):
        config.read(config_path)

    try:
        section, option = key.split('.', 1)
    except ValueError:
        raise ValueError("Error: Invalid key format. Should be 'section.key'.")

    if not config.has_section(section):
        config.add_section(section)
    
    config.set(section, option, value)
    
    with open(config_path, 'w') as configfile:
        config.write(configfile)

def get_user_config(repo_root):
    config = read_config()
    user_name = config.get('user', 'name', fallback=None)
    user_email = config.get('user', 'email', fallback=None)
    return user_name, user_email
