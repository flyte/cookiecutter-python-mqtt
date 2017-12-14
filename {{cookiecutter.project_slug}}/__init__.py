from os.path import dirname, join

import yaml


with open(join(dirname(__file__), 'config.schema.yml')) as schema:
    CONFIG_SCHEMA = yaml.load(schema)
