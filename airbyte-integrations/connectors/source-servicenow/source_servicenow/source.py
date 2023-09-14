#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


from abc import ABC
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple

import requests
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream
from airbyte_cdk.sources.streams.http.requests_native_auth import BasicHttpAuthenticator
from airbyte_cdk.sources.streams import IncrementalMixin
from datetime import datetime


class ServicenowStream(HttpStream, ABC):
    """
    TODO remove this comment

    This class represents a stream output by the connector.
    This is an abstract base class meant to contain all the common functionality at the API level e.g: the API base URL,
    pagination strategy, parsing responses etc..

    Each stream should extend this class (or another abstract subclass of it) to specify behavior unique to that stream.

    Typically for REST APIs each stream corresponds to a resource in the API. For example if the API
    contains the endpoints
        - GET v1/customers
        - GET v1/employees

    then you should have three classes:
    `class ServicenowHttpExampleStream(HttpStream, ABC)` which is the current class
    `class Customers(ServicenowHttpExampleStream)` contains behavior to pull data for customers using v1/customers
    `class Employees(ServicenowHttpExampleStream)` contains behavior to pull data for employees using v1/employees

    If some streams implement incremental sync, it is typical to create another class
    `class IncrementalServicenowHttpExampleStream((ServicenowHttpExampleStream), ABC)` then have concrete stream implementations extend it.

    See the reference docs for the full list of configurable options.
    """

    url_base = "https://dev97596.service-now.com/api/now/table/"

    def __init__(self, config: Mapping[str, Any], **kwargs):
        super().__init__(**kwargs)


class Incidents(ServicenowStream, IncrementalMixin):
    primary_key = "sys_id"
    cursor_field = "sys_updated_on"
    state_checkpoint_interval = 1

    def __init__(self, config: Mapping[str, Any], start_timestamp: datetime, **kwargs):
        super().__init__(config, **kwargs)
        self.start_timestamp = start_timestamp
        self._cursor_value = None

        # testing
        # self._cursor_value = self.start_timestamp

    @property
    def state(self) -> Mapping[str, Any]:
        self.logger.debug("getting state field")
        if self._cursor_value:
            self.logger.info(f"STATE_DEBUG cursor field set to self._cursor_value of {self._cursor_value}")
            return {self.cursor_field: self._cursor_value.strftime('%Y-%m-%d %H:%M:%S')}
        else:
            self.logger.info("STATE_DEBUG _cursor_value not set, defaulting to start_timestamp from config")
            return {self.cursor_field: self.start_timestamp.strftime('%Y-%m-%d %H:%M:%S')}

    @state.setter
    def state(self, value: Mapping[str, Any]):

        if value:
            self.logger.info(f'STATE_DEBUG setting state in incidents stream to {value}')
        else:
            self.logger.info(f'STATE_DEBUG empty value passed to setter')

        self._cursor_value = datetime.strptime(value[self.cursor_field], '%Y-%m-%d %H:%M:%S')
        self.logger.info(f'STATE_DEBUG self._cursor_value set to: {self._cursor_value}')

    def read_records(self, *args, **kwargs) -> Iterable[Mapping[str, Any]]:

        for record in super().read_records(*args, **kwargs):

            if self._cursor_value:
                latest_record_date = datetime.strptime(record[self.cursor_field], '%Y-%m-%d %H:%M:%S')

                # # debug
                # print('DEBUG: latest_record_data:', latest_record_date)

                self._cursor_value = max(self._cursor_value, latest_record_date)
            yield record

    def path(
            self,
            stream_state: Mapping[str, Any] = None,
            stream_slice: Mapping[str, Any] = None,
            next_page_token: Mapping[str, Any] = None
    ) -> str:

        if 'sys_updated_on' in stream_state:
            _interval_timestamp = datetime.strptime(stream_state['sys_updated_on'], '%Y-%m-%d %H:%M:%S')
            _date = _interval_timestamp.strftime("%Y-%m-%d")
            _time = _interval_timestamp.strftime("%H:%M:%S")
        else:
            _date = self.start_timestamp.strftime("%Y-%m-%d")
            _time = self.start_timestamp.strftime("%H:%M:%S")

        return ("incident?sysparm_query=state=7^"
                "sys_updated_on%3Ejavascript:gs.dateGenerate(%27" + _date + "%27,%27" + _time + "%27)%5EORDERBYsys_updated_on")

    def request_headers(
            self,
            stream_state: Mapping[str, Any],
            stream_slice: Mapping[str, Any] = None,
            next_page_token: Mapping[str, Any] = None
    ) -> Mapping[str, Any]:
        return {}

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        # TODO: see if we could use yield here to improve perf
        # yield response.json()["result"]

        data = response.json()["result"]
        return data

    def request_params(
            self,
            stream_state: Mapping[str, Any],
            stream_slice: Mapping[str, any] = None,
            next_page_token: Mapping[str, Any] = None,
    ) -> MutableMapping[str, Any]:
        return {
            "sysparm_display_value": "true",
            "sysparm_exclude_reference_link": "true",

            "sysparm_fields": "number,sys_updated_on,sys_id,category,state,closed_at,active,close_notes,description,contact_type",

            # for simpler testing use less fields
            # "sysparm_fields": "number,sys_updated_on",
        }

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        return None


class SourceServicenow(AbstractSource):
    def check_connection(self, logger, config) -> Tuple[bool, any]:
        """
        :param config:  the user-input config object conforming to the connector's spec.yaml
        :param logger:  logger object
        :return Tuple[bool, any]: (True, None) if the input config can be used to connect to the API successfully, (False, error) otherwise.
        """
        username = config["username"]
        password = config["password"]
        url = "https://dev97596.service-now.com/api/now/table/incident?sys_parm_limit=1"

        try:
            response = requests.get(url, auth=(username, password), headers={})
            if response.status_code == 200:
                return True, None
        # TODO: improve this connection check
        except ConnectionError as error:
            return False, error

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        username = config["username"]
        password = config["password"]
        auth = BasicHttpAuthenticator(username=username, password=password)

        start_timestamp = config["start_timestamp"]
        start_timestamp_obj = datetime.strptime(start_timestamp, '%Y-%m-%d %H:%M:%S')

        return [Incidents(authenticator=auth, config=config, start_timestamp=start_timestamp_obj)]
