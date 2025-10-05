# What it does: Manages all read/write operations for the `.pit/config` file
# What data structure it uses: Map / Hash Table / Dictionary (the INI file format is a map of sections to key-value pairs, managed by Python's `configparser`)

import configparser
import os
from .repository import find_repo_root

def get_config_path(repo_root):  # Returns the path to the config file within the repository
    return os.path.join(repo_root, '.pit', 'config')

def read_config(): # Reads and returns the configuration as a ConfigParser object
    repo_root = find_repo_root()
    if not repo_root:
        return configparser.ConfigParser()
        
    config_path = get_config_path(repo_root)
    config = configparser.ConfigParser()
    if os.path.exists(config_path):
        config.read(config_path)
    return config

def write_config(key, value): # Sets a configuration key to a value and writes it to the config file
    repo_root = find_repo_root()
    if not repo_root:
        raise FileNotFoundError("Not a Pit repository.")

    config_path = get_config_path(repo_root)
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

def get_user_config(repo_root): # Retrieves user.name and user.email from the config, or None if not set
    config_path = get_config_path(repo_root)
    config = configparser.ConfigParser()
    if not os.path.exists(config_path):
        return None, None
    
    config.read(config_path)
    
    user_name = config.get('user', 'name', fallback=None)
    user_email = config.get('user', 'email', fallback=None)
    
    return user_name, user_email