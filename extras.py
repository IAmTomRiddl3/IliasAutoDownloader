import os

def config_file() -> str:
    config_file = "config.json"
    public_config_file = "config_public.json"

    # Load the configuration file, fallback to public_config.json if not found
    if not os.path.exists(config_file):
        print(f"{config_file} not found. Using {public_config_file} as fallback.")
        return public_config_file

    return config_file
