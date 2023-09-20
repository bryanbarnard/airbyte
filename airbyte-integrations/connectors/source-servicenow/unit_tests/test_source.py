#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#

from unittest.mock import MagicMock
import pytest
import requests.exceptions

from source_servicenow.source import SourceServicenow


def test_check_connection_success(setup_valid_config):
    source = SourceServicenow()
    logger_mock, config_mock = MagicMock(), MagicMock()
    assert source.check_connection(logger_mock, setup_valid_config) == (True, None)


def test_check_connection_fail(setup_invalid_config):
    source = SourceServicenow()
    logger_mock, config_mock = MagicMock(), MagicMock()
    with pytest.raises(requests.exceptions.ConnectionError):
        source.check_connection(logger_mock, setup_invalid_config)


def test_streams(setup_valid_config):
    source = SourceServicenow()
    streams = source.streams(setup_valid_config)
    expected_streams_number = 1
    assert len(streams) == expected_streams_number
