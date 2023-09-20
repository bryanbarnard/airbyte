import pytest
from airbyte_cdk import connector


@pytest.fixture()
def setup_valid_config():
    config_obj = connector.BaseConnector.read_config(config_path='../secrets/config.json')

    # if not using config file can set in code
    # config_obj = {
    #     "username": "xxx",
    #     "password": "xxx",
    #     "instance_id": "xxx",
    #     "start_timestamp": "xxx"
    # }
    return config_obj


@pytest.fixture()
def setup_invalid_config():
    # config_obj = connector.BaseConnector.read_config(config_path='../secrets/config.json')

    # if not using config file can set in code
    config_obj = {
        "username": "xxx",
        "password": "xxx",
        "instance_id": "xxx",
        "start_timestamp": "xxx"
    }
    return config_obj

