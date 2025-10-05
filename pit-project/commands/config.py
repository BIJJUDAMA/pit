# The command: pit config <key> <value>
# What it does: A user-facing command to set a configuration key-value pair (e.g., user.name)
# How it does: It acts as a simple dispatcher, passing the key and value to the `write_config` function in the `utils/config.py` module, which handles the file I/O and parsing logic
# What data structure it uses: None directly, but it provides the interface to the underlying Map / Dictionary structure managed by `utils/config.py`

import sys
from utils import config as config_utils

def run(args):
    try: # Set the configuration key-value pair
        config_utils.write_config(args.key, args.value) 
        print(f"Set {args.key} to '{args.value}'")
    except Exception as e: 
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)