from __future__ import print_function

from future import standard_library

from builtins import object
from datetime import datetime
from tzlocal import get_localzone

import configparser
import json
import pytz
import sys
import requests
import requests.auth
import dateutil.parser
import time

standard_library.install_aliases()


class TruStar(object):
    """
    Main class you to instantiate the TruStar API
    """

    def __init__(self, config_file="trustar.conf", config_role="trustar"):

        self.enclaveIds = []
        self.attributedToMe = False

        config_parser = configparser.RawConfigParser()
        config_parser.read(config_file)

        try:
            # parse required properties
            self.auth = config_parser.get(config_role, 'auth_endpoint')
            self.base = config_parser.get(config_role, 'api_endpoint')
            self.apikey = config_parser.get(config_role, 'user_api_key')
            self.apisecret = config_parser.get(config_role, 'user_api_secret')

            # parse enclave an attribution properties
            if config_parser.has_option(config_role, 'enclave_ids'):
                self.enclaveIds = [i for i in config_parser.get(config_role, 'enclave_ids').split(',') if i is not None]

            if config_parser.has_option(config_role, 'attribute_reports'):
                self.attributedToMe = config_parser.getboolean(config_role, 'attribute_reports')
        except Exception as e:
            print("Problem reading config file: %s", e)
            sys.exit(1)

    @staticmethod
    def normalize_timestamp(date_time):
        """
        Attempt to convert a string timestamp in to a TruSTAR compatible format for submission.
        Will return current time with UTC time zone if None
        :param date_time: int that is epoch time, or string/datetime object containing date, time, and ideally timezone
        examples of supported timestamp formats: 1487890914, 1487890914000, "2017-02-23T23:01:54", "2017-02-23T23:01:54+0000"
        """
        datetime_dt = datetime.now()

        # get current time in seconds-since-epoch
        current_time = int(time.time())

        try:
            # identify type of timestamp and convert to datetime object
            if isinstance(date_time, int):

                # if timestamp has more than 10 digits, it is in ms
                if date_time > 9999999999:
                    date_time /= 1000

                # if timestamp is incorrectly forward dated, set to current time
                if date_time > current_time:
                    date_time = current_time
                datetime_dt = datetime.fromtimestamp(date_time)
            elif isinstance(date_time, str):
                datetime_dt = dateutil.parser.parse(date_time)
            elif isinstance(date_time, datetime):
                datetime_dt = date_time

        # if timestamp is none of the formats above, error message is printed and timestamp is set to current time by default
        except Exception as e:
            print(e)
            datetime_dt = datetime.now()

        # if timestamp is timezone naive, add timezone
        if not datetime_dt.tzinfo:
            timezone = get_localzone()

            # add system timezone
            datetime_dt = timezone.localize(datetime_dt)

            # convert to UTC
            datetime_dt = datetime_dt.astimezone(pytz.utc)

        # converts datetime to iso8601
        return datetime_dt.isoformat()

    def get_token(self, verify=True):
        """
        Retrieves the OAUTH token generated by your API key and API secret.
        this function has to be called before any API calls can be made
        :param verify: boolean - ignore verifying the SSL certificate if you set verify to False
        """
        client_auth = requests.auth.HTTPBasicAuth(self.apikey, self.apisecret)
        post_data = {"grant_type": "client_credentials"}
        resp = requests.post(self.auth, auth=client_auth, data=post_data, verify=verify)
        token_json = resp.json()
        return token_json["access_token"]

    def get_latest_reports(self, access_token):
        """
        Retrieves the latest 5 reports submitted to the TruSTAR community
        :param access_token: OAuth API token
        """

        headers = {"Authorization": "Bearer " + access_token}
        resp = requests.get(self.base + "/reports/latest", headers=headers)
        return json.loads(resp.content.decode('utf8'))

    def get_report_details(self, access_token, report_id):
        """
        Retrieves the report details
        :param access_token: OAuth API token
        :param report_id: Incident Report ID
        """

        headers = {"Authorization": "Bearer " + access_token}
        payload = {'id': report_id}
        resp = requests.get(self.base + "/reports/details", payload, headers=headers)
        return json.loads(resp.content)

    def get_report_details_v12(self, access_token, report_id, id_type=None, verify=True):
        """
        Retrieves the report details
        :param access_token: OAuth API token
        :param report_id: Incident Report ID
        :param id_type: indicates if ID is internal report guid or external ID provided by the user
        :param verify: boolean - ignore verifying the SSL certificate if you set verify to False
        """

        url = "%s/report/%s" % (self.base, report_id)
        headers = {"Authorization": "Bearer " + access_token}
        params = {'idType': id_type}
        resp = requests.get(url, params=params, headers=headers, verify=verify)
        return json.loads(resp.content)

    def update_report(self, access_token, report_id, id_type=None, title=None, report_body=None, time_discovered=None,
                      distribution=None, attribution=None, enclave_ids=None, verify=True):
        """
        Updates report with the given id, overwrites any fields that are provided
        :param access_token: OAuth API token
        :param report_id: Incident Report ID
        :param id_type: indicates if ID is internal report guid or external ID provided by the user
        :param title: new title for report
        :param report_body: new body for report
        :param time_discovered: new time_discovered for report
        :param distribution: new distribution type for report
        :param attribution: new value indicating if attribution is enabled for report
        :param enclave_ids: new list of enclave ids that the report will belong to
        :param verify: boolean - ignore verifying the SSL certificate if you set verify to False
        """

        url = "%s/report/%s" % (self.base, report_id)
        headers = {'Authorization': 'Bearer ' + access_token, 'content-Type': 'application/json'}
        params = {'idType': id_type}

        # if enclave_ids field is not null, parse into array of strings
        if enclave_ids:
            enclave_ids = [i for i in enclave_ids.split(',') if i is not None]

        payload = {'incidentReport': {'title': title, 'reportBody': report_body, 'timeDiscovered': time_discovered,
                                      'distributionType': distribution}, 'enclaveIds': enclave_ids,
                   'attributedToMe': attribution}
        resp = requests.put(url, json.dumps(payload), params=params, headers=headers, verify=verify)
        return json.loads(resp.content)

    def delete_report(self, access_token, report_id, id_type=None, verify=True):
        """
        Deletes the report for the given id
        :param access_token: OAuth API token
        :param report_id: Incident Report ID
        :param id_type: indicates if ID is internal report guid or external ID provided by the user
        :param verify: boolean - ignore verifying the SSL certificate if you set verify to False
        """

        url = "%s/report/%s" % (self.base, report_id)
        headers = {"Authorization": "Bearer " + access_token}
        params = {'idType': id_type}
        resp = requests.delete(url, params=params, headers=headers, verify=verify)
        return resp

    def query_latest_indicators(self, access_token, source, indicator_types, limit, interval_size):
        """
        Finds all latest indicators
        :param access_token: OAUTH access token
        :param source: source of the indicators which can either be INCIDENT_REPORT or OSINT
        :param indicator_types: a list of indicators or a string equal to "ALL" to query all indicator types extracted
        by TruSTAR
        :param limit: limit on the number of indicators. Max is set to 5000
        :param interval_size: time interval on returned indicators. Max is set to 24 hours
        :return json response of the result
        """

        headers = {"Authorization": "Bearer " + access_token}
        payload = {'source': source, 'types': indicator_types, 'limit': limit, 'intervalSize': interval_size}
        resp = requests.get(self.base + "/indicators/latest", payload, headers=headers)
        return json.loads(resp.content)

    def get_correlated_reports(self, access_token, indicator):
        """
        Retrieves all TruSTAR reports that contain the searched indicator. You can specify multiple indicators
        separated by commas
        :param access_token:  OAuth API token
        :param indicator:
        """

        headers = {"Authorization": "Bearer " + access_token}
        payload = {'q': indicator}
        resp = requests.get(self.base + "/reports/correlate", payload, headers=headers)
        return json.loads(resp.content)

    def query_indicators(self, access_token, indicators, limit):
        """
        Finds all reports that contain the indicators and returns correlated indicators from those reports.
        you can specify the limit of indicators returned.
        :param access_token: OAuth API token
        :param indicators: list of space-separated indicators to search for
        :param limit: max number of results to return
        """

        headers = {"Authorization": "Bearer " + access_token}
        payload = {'q': indicators, 'limit': limit}

        resp = requests.get(self.base + "/indicators", payload, headers=headers)
        return json.loads(resp.content)

    def submit_report(self, access_token, report_body_txt, report_name, began_time=datetime.now(),
                      enclave=False, verify=True):
        """
        Wraps supplied text as a JSON-formatted TruSTAR Incident Report and submits it to TruSTAR Station
        By default, this submits to the TruSTAR community. To submit to your enclave, set enclave parameter to True,
        and ensure that the target enclaves' ids are specified in the config file field enclave_ids.
        :param began_time:
        :param enclave: boolean - whether or not to submit report to user's enclaves (see 'enclave_ids' config property)
        :param report_name:
        :param report_body_txt:
        :param access_token:
        :param verify: boolean - ignore verifying the SSL certificate if you set verify to False
        """

        # Convert timestamps
        distribution_type = 'ENCLAVE' if enclave else 'COMMUNITY'
        if distribution_type == 'ENCLAVE' and len(self.enclaveIds) < 1:
            raise Exception("Must specify one or more enclave IDs to submit enclave reports into")

        headers = {'Authorization': 'Bearer ' + access_token, 'content-Type': 'application/json'}

        payload = {'incidentReport': {
            'title': report_name,
            'timeBegan': self.normalize_timestamp(began_time),
            'reportBody': report_body_txt,
            'distributionType': distribution_type},
            'enclaveIds': self.enclaveIds,
            'attributedToMe': self.attributedToMe}
        print("Submitting report %s to TruSTAR Station..." % report_name)
        resp = requests.post(self.base + "/reports/submit", json.dumps(payload), headers=headers,
                             timeout=60, verify=verify)

        return resp.json()

    def submit_report_v12(self, access_token, report_body_txt, report_name, external_id=None, began_time=datetime.now(),
                          enclave=False, verify=True):
        """
        Wraps supplied text as a JSON-formatted TruSTAR Incident Report and submits it to TruSTAR Station
        By default, this submits to the TruSTAR community. To submit to your enclave(s), set enclave parameter to True,
        and ensure that the target enclaves' ids are specified in the config file field enclave_ids.
        :param access_token: OAuth API token
        :param report_body_txt: body of report
        :param report_name: title of report
        :param external_id: external tracking id of report, optional if user doesn't have their own tracking id that they want associated with this report
        :param began_time: time report began
        :param enclave: boolean - whether or not to submit report to user's enclaves (see 'enclave_ids' config property)
        :param verify: boolean - ignore verifying the SSL certificate if you set verify to False
        """

        distribution_type = 'ENCLAVE' if enclave else 'COMMUNITY'
        if distribution_type == 'ENCLAVE' and len(self.enclaveIds) < 1:
            raise Exception("Must specify one or more enclave IDs to submit enclave reports into")

        headers = {'Authorization': 'Bearer ' + access_token, 'content-Type': 'application/json'}

        payload = {'incidentReport': {
            'title': report_name,
            'externalTrackingId': external_id,
            'timeBegan': self.normalize_timestamp(began_time),
            'reportBody': report_body_txt,
            'distributionType': distribution_type},
            'enclaveIds': self.enclaveIds,
            'attributedToMe': self.attributedToMe}
        print("Submitting report %s to TruSTAR Station..." % report_name)
        resp = requests.post(self.base + "/report", json.dumps(payload), headers=headers,
                             timeout=60, verify=verify)

        return resp.json()

    def get_report_url(self, report_id):
        """
        Build direct URL to report from its ID
        :param report_id: Incident Report (IR) ID, e.g., as returned from `submit_report`
        :return URL
        """

        # Check environment for URL
        base_url = 'https://station.trustar.co' if ('https://api.trustar.co' in self.base) else \
            self.base.split('/api/')[0]

        return "%s/constellation/reports/%s" % (base_url, report_id)
