import os

def load_env_vars(filepath: str):
    with open(filepath) as f:
        for line in f:
            # Ignore comments and empty lines
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, value = line.split('=', 1)
            os.environ[key.strip()] = value.strip()