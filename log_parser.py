#!/usr/bin/env python3

import os
import gzip
import logging
import fnmatch

from datetime import datetime
from gzip import GzipFile
from typing import Union, TextIO, Any, Iterable, Optional, Dict, Tuple
from collections import namedtuple, defaultdict

from constants import LOG_LINE_PATTERN, LOG_REQUEST_PATTERN, LOG_DATE_PATTERN

Request = namedtuple("Request", ["type", "url", "proto"])
LogLineResult = namedtuple("LogLineResult", ["url", "request_time"])
LogFile = namedtuple("LastLog", ["name", "path", "date"])

logger = logging.getLogger(__name__)


def search_logs(directory: str, file_pattern: str) -> Optional[Iterable[str]]:
    if not directory:
        return None

    for path, dir_list, file_list in os.walk(directory):
        for name in fnmatch.filter(file_list, file_pattern):
            yield name


def filter_to_latest_log(files: Iterable[str]) -> Optional[Tuple[str, datetime]]:
    latest_log = None
    latest_date = None

    for file in files:
        match = LOG_DATE_PATTERN.match(file)
        if not match:
            continue

        date_string = match.groupdict()["date"]
        try:
            date = datetime.strptime(date_string, "%Y%m%d")
        except ValueError as e:
            logger.error("Can't convert str to datetime: {}".format(e))
            continue

        if latest_date is None or latest_date < date:
            latest_date = date
            latest_log = file

    if not latest_log or not latest_date:
        return None

    return latest_log, latest_date


def find_latest_log(directory: str, file_pattern: str) -> Optional[LogFile]:
    files = search_logs(directory, file_pattern)
    latest_log = filter_to_latest_log(files)

    if latest_log is None:
        return None

    return LogFile(name=latest_log[0],
                   path=os.path.join(directory, latest_log[0]),
                   date=latest_log[1])


def xreadlines(file: Union[Union[TextIO, GzipFile], Any]) -> Iterable[str]:
    open_ = gzip.open if file.endswith('.gz') else open
    with open_(file, 'rt', encoding='utf-8') as file:
        yield from file


def parse_request(request: str) -> Optional[Request]:
    match = LOG_REQUEST_PATTERN.match(request)
    if not match:
        return None

    groups = match.groupdict()

    return Request(type=groups["request_type"],
                   url=groups["request_url"],
                   proto=groups["request_proto"])


def parse_log_line(log_line: str) -> Optional[LogLineResult]:
    match = LOG_LINE_PATTERN.match(log_line)
    if not match:
        return None

    groups = match.groupdict()

    if not groups["request"] or not groups["request_time"]:
        logger.info("Request or request time are missed")
        return None

    parsed_request = parse_request(groups["request"])
    if not parsed_request:
        logger.info("Request is not parsed, request string: {}"
                    .format(str(groups["request"])))
        return None

    if parsed_request.url and groups["request_time"]:
        return LogLineResult(url=parsed_request.url,
                             request_time=float(groups["request_time"]))

    return None


def parse_log_stat(log_file: str, config: Dict) -> Optional[Dict]:
    parsing_errors_count = 0
    lines_parsed = 0

    stats = defaultdict(list)

    for line in xreadlines(log_file):
        result = parse_log_line(line)
        lines_parsed += 1
        if result is None:
            parsing_errors_count += 1
            continue

        stats[result.url].append(result.request_time)

    error_percent = parsing_errors_count / lines_parsed * 100
    if error_percent >= config["ERROR_PERCENT_THRESHOLD"]:
        logger.error("Parser error threshold exceeded")
        return None

    return stats
