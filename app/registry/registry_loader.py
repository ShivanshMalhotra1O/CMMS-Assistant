import yaml


# Load registry
def load_registry(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)