import unittest
from trustar import *

import time
import random


DAY = 24 * 60 * 60 * 1000

current_time = int(time.time()) * 1000
yesterday_time = current_time - DAY
old_time = current_time - DAY * 365 * 3


def generate_ip(start_range=100):
    """
    Generates a random IP where each.
    :param start_range: The lowest possible value for each octet.
    :return: The random IP address.
    """
    return ".".join(map(str, (random.randint(start_range, 255) for _ in range(4))))


class TruStarTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ts = TruStar()

    def test_ping(self):
        pong = self.ts.ping()
        self.assertTrue(len(pong) > 0)

    def test_version(self):
        version = self.ts.get_version()
        BETA_TAG = "-beta"
        self.assertEqual(version.strip(BETA_TAG), trustar.__api_version__.strip(BETA_TAG))

    def test_get_reports(self):
        """
        Test that we can get all reports fitting some filters.
        """
        for from_time in [yesterday_time, old_time]:
            reports = self.ts.get_reports_page(from_time=from_time,
                                               to_time=current_time,
                                               is_enclave=False)
            print(reports)

    def test_submit_report(self):
        """
        Test the entire workflow of submitting, updating, getting, tagging, and deleting a report.
        """
        # create and submit report
        report = Report(title="Report 1",
                        body="Blah blah blah",
                        time_began=yesterday_time,
                        enclave_ids=self.ts.enclave_ids)
        report = self.ts.submit_report(report=report)

        # update report
        report.body = "Bleh bleh bleh"
        self.ts.update_report(report=report)

        # get report
        result = self.ts.get_report_details(report_id=report.id)
        self.assertEqual(result.body, report.body)

        # add tag
        result = self.ts.add_enclave_tag(report_id=report.id,
                                         enclave_id=self.ts.enclave_ids[0],
                                         name="some_tag")

        # get tags
        result = self.ts.get_enclave_tags(report_id=report.id)
        tag_id = None
        for tag in result:
            if tag.name == "some_tag":
                tag_id = tag.id

        self.assertIsNotNone(tag_id)

        # delete tag
        result = self.ts.delete_enclave_tag(report_id=report.id,
                                            tag_id=tag_id)

        # delete report
        response = self.ts.delete_report(report_id=report.id)

    def test_community_trends(self):
        """
        Check that we can get community trending indicators, and that the total
        number of each indicator type (except MALWARE and CVE) is consistent with
        the total number returned when we get ALL indicator types (except MALWARE and CVE).
        """
        totals = []

        indicator_types = {
            IndicatorType.CVE,
            IndicatorType.MALWARE,
            None
        }

        # get results for all types and sum total elements for all except CVE and MALWARE
        for indicator_type in indicator_types:
            result = self.ts.get_community_trends(indicator_type=indicator_type)

            if indicator_type is not None:
                # ensure only indicators of correct type received
                for indicator in result:
                    self.assertEqual(indicator.type, indicator_type)

            correlation_counts = [indicator.correlation_count for indicator in result]
            for i in range(len(correlation_counts) - 1):
                self.assertTrue(correlation_counts[i] >= correlation_counts[i+1])

    def test_get_related_indicators_and_correlated_reports(self):
        """
        Submits a group of reports that contain common indicators, then checks that
        getting related indicators and correlated reports returns the expected results.
        """

        #########
        # SETUP #
        #########

        indicators = [
            "www.wefrrtdgwefwef1234.org",
            "wefoijseroijr@yahoo.org"
        ]

        related = ["www.abcxyz1235.com"] + [generate_ip() for _ in range(27)]

        indicator_groups = [
            related[:5],
            related[5:9],
            related[9:19],
            related[19:25],
            related[25:]
        ]

        reports = []

        count = 0
        for group in indicator_groups:
            count += 1
            report = Report(
                title="Test_Get_Related_Indicators_Report_%s" % count,
                body=" some words ".join([indicators[count % 2]] + group),
                enclave_ids=self.ts.enclave_ids
            )
            report = self.ts.submit_report(report=report)
            reports.append(report)

        count = 0
        for report, indicator_group in zip(reports, indicator_groups):
            count += 1
            report_indicators = self.ts.get_indicators_for_report(report_id=report.id)
            self.assertSetEqual(set(str(x.value) for x in report_indicators),
                                set([indicators[count % 2]] + indicator_group))

        ###############
        # GET RELATED #
        ###############

        server_related = list(self.ts.get_related_indicators(indicators=indicators))
        related_reports = self.ts.get_correlated_report_ids(indicators=indicators)

        ###########
        # CLEANUP #
        ###########

        for report in reports:
            self.ts.delete_report(report_id=report.id)

        ##########
        # ASSERT #
        ##########

        server_indicator_values = set([str(ind.value.lower()) for ind in server_related])
        for indicator in related:
            self.assertTrue(indicator.lower() in server_indicator_values)

    def test_get_related_indicators(self):
        result = self.ts.get_related_indicators_page(indicators=["evil", "1.2.3.4", "wannacry"])

    def test_get_correlated_reports(self):
        result = self.ts.get_correlated_report_ids(["evil", "wannacry"])

    def test_get_reports_by_tag(self):
        """
        Test workflow of submitting and tagging a report, then getting all reports by that tag name.
        """

        from_time = get_current_time_millis()

        enclave_id = self.ts.enclave_ids[0]

        # create and submit report
        report = Report(title="Report 1",
                        body="Blah blah blah",
                        time_began=yesterday_time,
                        enclave_ids=[enclave_id])
        report = self.ts.submit_report(report=report)

        # tag report
        tag = "some gibberish"
        self.ts.add_enclave_tag(report_id=report.id, name=tag, enclave_id=enclave_id)

        to_time = get_current_time_millis()

        # get all reports with the tag just created
        report_ids = [r.id for r in self.ts.get_reports(tag=tag, from_time=from_time, to_time=to_time)]

        try:
            # assert that only the report submitted earlier was found
            self.assertEqual(len(report_ids), 1)
            self.assertEqual(report_ids[0], report.id)
        finally:
            # cleanup reports
            for id in report_ids:
                self.ts.delete_report(report_id=id)

    @unittest.skip
    def test_search_indicators(self):
        indicators = self.ts.search_indicators("abc")
        self.assertGreater(len(list(indicators)), 0)

    @unittest.skip
    def test_search_reports(self):
        reports = self.ts.search_reports("abc")
        self.assertGreater(len(list(reports)), 0)

    def test_get_enclaves(self):
        enclaves = self.ts.get_user_enclaves()
        self.assertGreater(len(enclaves), 0)
        print(enclaves[0])

    def test_whitelist(self):
        indicators = self.ts.add_terms_to_whitelist(["not_malicious.com", "really_not_malicious.net"])
        self.assertEqual(len(indicators), 2)

        whitelist = self.ts.get_whitelist_page()
        self.assertGreater(len(whitelist), 0)

        for indicator in indicators:
            self.ts.delete_indicator_from_whitelist(indicator=indicator)

    def test_get_indicator_details(self):

        indicators = ["1.2.3.4", "evil.com"]

        report = Report(title="test",
                        body=' '.join(indicators))

        self.ts.submit_report(report)

        details = self.ts.get_indicator_details(indicators)

        print(details)

        self.ts.delete_report(report.id)

    def test_submit_indicators(self):
        indicators = [
            Indicator(value="1.5.8.7",
                      first_seen=get_current_time_millis() - 24 * 60 * 60 * 1000, last_seen= get_current_time_millis(),
                      sightings=100, source="Somewhere", notes="This is a note."),
            Indicator(value="1.5.8.9",
                      first_seen=get_current_time_millis() - 2 * 24 * 60 * 60 * 1000, last_seen=get_current_time_millis(),
                      sightings=50, source="Somewhere else", notes="This is another note.")
        ]
        tags = [
            Tag(name="tag_1", enclave_id=self.ts.enclave_ids[0]),
            Tag(name="tag_2", enclave_id=self.ts.enclave_ids[0])
        ]
        self.ts.submit_indicators(indicators=indicators, tags=tags)

    def test_get_indicators(self):
        indicators = self.ts.get_indicators(from_time=0, to_time=get_current_time_millis())
        print(list(indicators))

    def test_get_indicator_metadata(self):
        metadata = self.ts.get_indicator_metadata("blah.com")
        print(metadata)

    def test_get_indicators_metadata(self):
        values = ['1.5.8.7', '1.5.8.9']

        indicators = [Indicator(value=value, type=IndicatorType.IP) for value in values]
        metadata = self.ts.get_indicators_metadata(indicators)
        self.assertTrue(len(metadata) == 2)

        for i in indicators:
            i.type = IndicatorType.URL

        metadata = self.ts.get_indicators_metadata(indicators)
        self.assertTrue(len(metadata) == 0)

        for i in indicators:
            i.type = None

        metadata = self.ts.get_indicators_metadata(indicators)
        self.assertTrue(len(metadata) == 2)


    def test_add_tag_to_indicator(self):
        tag = self.ts.add_indicator_tag("blah.com", name="indicator_tag", enclave_id=self.ts.enclave_ids[0])
        print(tag)

    def test_get_indicator_tags(self):
        tags = self.ts.get_all_indicator_tags()
        print(tags)

    def test_delete_tag_from_indicator(self):
        metadata = self.ts.get_indicator_metadata("blah.com")
        tags = metadata.get('tags')
        tag = tags[0]
        self.ts.delete_indicator_tag(metadata.get('indicator').value, tag_id=tag.id)


if __name__ == '__main__':
    unittest.main()
