#!/usr/bin/env python3

import os
import gzip
import logging
import fnmatch

from datetime import datetime
from gzip import GzipFile
from enum import Enum
from typing import Union, TextIO, Any, Iterable, Optional, Dict, Tuple
from collections import namedtuple, defaultdict

from log_pattern import log_line_pattern, log_request_pattern, log_date_pattern


class ParsingStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"


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
        match = log_date_pattern.match(file)
        if not match:
            return None

        date_string = match.groupdict()["date"]
        date = datetime.strptime(date_string, "%Y%m%d")
        if latest_date is None or latest_date < date:
            latest_date = date
            latest_log = file

    return latest_log, latest_date


def find_latest_log(directory: str, file_pattern: str) -> Optional[LogFile]:
    files = search_logs(directory, file_pattern)
    latest_log = filter_to_latest_log(files)
    if not latest_log:
        return None

    return LogFile(name=latest_log[0],
                   path=directory + "/" + latest_log[0],
                   date=latest_log[1])


class LogParser:
    ERROR_THRESHOLD = 1000

    def __init__(self, config: Dict):
        self.config = config

    @staticmethod
    def _open(file: str, *args, **kwargs) -> Union[Union[TextIO, GzipFile], Any]:
        if file.endswith('.gz'):
            return gzip.open(file, *args, **kwargs)
        return open(file, *args, **kwargs)

    def _read_lines(self, file: Union[Union[TextIO, GzipFile], Any]) -> Iterable[str]:
        with self._open(file, 'rt', encoding='utf-8') as file:
            yield from file

    @staticmethod
    def parse_request(request: str) -> Optional[Request]:
        match = log_request_pattern.match(request)
        if not match:
            return None

        groups = match.groupdict()

        return Request(type=groups["request_type"],
                       url=groups["request_url"],
                       proto=groups["request_proto"])

    def parse_log_line(self, log_line: str) -> Tuple[ParsingStatus, Optional[LogLineResult]]:

        match = log_line_pattern.match(log_line)
        if not match:
            return ParsingStatus.ERROR, None

        groups = match.groupdict()

        if not groups["request"] or not groups["request_time"]:
            logger.info("Request or request time are missed")
            return ParsingStatus.ERROR, None

        parsed_request = self.parse_request(groups["request"])
        if not parsed_request:
            logger.info("Request is not parsed, request string: {}"
                        .format(str(groups["request"])))
            return ParsingStatus.ERROR, None

        if parsed_request.url and groups["request_time"]:
            return ParsingStatus.SUCCESS, \
                   LogLineResult(url=parsed_request.url,
                                 request_time=float(groups["request_time"]))

        return ParsingStatus.ERROR, None

    def parse(self, log_file: str) -> Tuple[ParsingStatus, Dict]:
        parsing_errors_count = 0
        stats = defaultdict(list)

        for line in self._read_lines(log_file):
            status, result = self.parse_log_line(line)
            if status == ParsingStatus.ERROR or not result:
                parsing_errors_count += 1
                continue

            stats[result.url].append(result.request_time)

        if parsing_errors_count >= self.ERROR_THRESHOLD:
            logger.error("Parser error threshold exceeded")
            return ParsingStatus.ERROR, stats

        return ParsingStatus.SUCCESS, stats
