#!/usr/bin/env python3

import os
import sys
import logging
import argparse

from datetime import datetime
from typing import Dict, List
from string import Template

from log_parser import LogParser, LogFile, find_latest_log, ParsingStatus
from utils import setup_logging, load_config
from stats import calculate_metrics

logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Log analyzer config path")

    return parser.parse_args()


def report_name_by_date(date: datetime) -> str:
    report_pattern = "report-{date}.html"
    date_string = date.strftime("%Y.%m.%d")

    return report_pattern.format(date=date_string)


def is_date_report_exists(directory: str, date: datetime) -> bool:
    report_name = report_name_by_date(date)

    if not directory:
        return False

    if os.path.exists(directory + "/" + report_name):
        return True

    return False


def generate_report(report_directory: str, log: LogFile, metrics: List):
    report_pattern_name = "report.html"
    report_pattern_path = report_directory + "/" + report_pattern_name

    with open(report_pattern_path, encoding='utf-8') as report_pattern:
        report_text = report_pattern.read()
        report_text = Template(report_text).safe_substitute(table_json=str(metrics))

    report_name = report_name_by_date(log.date)
    report_path = report_directory + "/" + report_name

    with open(report_path, "w+") as report_file:
        report_file.write(report_text)


def analyze(config: Dict):
    fnmatch_log_pattern = "nginx-access-ui.log-*"
    latest_log = find_latest_log(config["LOG_DIR"],
                                 fnmatch_log_pattern)

    if not latest_log:
        logger.info("No logs or can't parsed")
        return None

    if is_date_report_exists(config["REPORT_DIR"], latest_log.date):
        logger.info("Report already exists")
        return None

    log_parser = LogParser(config=config)
    try:
        status, stats = log_parser.parse(latest_log.path)
    except Exception as e:
        logger.exception("Can't parse log: ".format(e), exc_info=True)
        return None

    if status == ParsingStatus.ERROR:
        logger.info("Parsing was finished with errors")
        return None

    metrics = calculate_metrics(stats)
    sorted_metrics = sorted(metrics, key=lambda k: k['time_sum'])
    top_metrics = sorted_metrics[-int(config["REPORT_SIZE"]):]

    try:
        generate_report(config["REPORT_DIR"], latest_log, top_metrics)
    except Exception as e:
        logger.exception("Can't generate report: {}".format(e), exc_info=True)
        return None


def main():
    args = parse_args()
    config = load_config(args.config)

    setup_logging(config)

    try:
        analyze(config)
    except Exception as e:
        logger.exception(e, exc_info=True)
        sys.exit(0)


if __name__ == "__main__":
    main()
