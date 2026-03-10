import pytest
import json


class ResultsCollector:
    def __init__(self):
        self.reports = []

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        report = outcome.get_result()
        if report.when == 'call':
            self.reports.append(report)


def get_response_from_test(collector, result):
    reports = []
    for report in collector.reports:
        if not report.longrepr:
            continue
        reports.append(str(report.longrepr).split('\n'))
    if not reports:
        reponse = {'status': 'OK'} if str(result) == 'ExitCode.OK' else {'error': 'Test cant start'}
        return reponse
    return {'error': reports}


def pytest_addoption(parser):
    parser.addoption(
        "--buyout_id",
        action="append",
        default=[],
        help="parameter for test",
    )
    parser.addoption(
        "--payment_type",
        action="append",
        default=[],
        help="parameter for test",
    )
    parser.addoption(
        "--review_id",
        action="append",
        default=[],
        help="parameter for test",
    )
    parser.addoption(
        "--favorite_id",
        action="append",
        default=[],
        help="parameter for test",
    )


def pytest_generate_tests(metafunc):
    if "buyout_id" in metafunc.fixturenames:
        metafunc.parametrize("buyout_id", metafunc.config.getoption("buyout_id"))
        metafunc.parametrize("payment_type", metafunc.config.getoption("payment_type"))
    if "favorite_id" in metafunc.fixturenames:
        metafunc.parametrize("favorite_id", metafunc.config.getoption("favorite_id"))
    if "review_id" in metafunc.fixturenames:
        metafunc.parametrize("review_id", metafunc.config.getoption("review_id"))
