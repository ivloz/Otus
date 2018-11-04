#!/usr/bin/env python3

import os
import logging
import argparse

from datetime import datetime
from typing import Dict, List, Optional
from string import Template
from statistics import mean, median

from log_parser import LogFile, find_latest_log, parse_log_stat
from utils import setup_logging, load_config

logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Log analyzer config path")

    return parser.parse_args()


def report_name_by_date(date: datetime) -> str:
    report_pattern = "report-{date}.html"
    try:
        date_string = date.strftime("%Y.%m.%d")
    except ValueError as e:
        logger.error("Can't convert date to str: {}".format(e))
        raise e

    return report_pattern.format(date=date_string)


def is_date_report_exists(directory: str, date: datetime) -> bool:
    report_name = report_name_by_date(date)

    if not directory:
        return False

    if os.path.exists(os.path.join(directory, report_name)):
        return True

    return False


def calculate_metrics(stats: Dict) -> List:
    metrics = []
    total_url_count = 0
    total_request_time = 0

    for url, requests_time in stats.items():
        total_url_count += 1
        total_request_time += sum(requests_time)

    if not total_url_count or not total_request_time:
        return metrics

    for url, requests_time in stats.items():
        url_metrics = {}
        url_metrics["url"] = url
        url_metrics["count"] = len(requests_time)
        url_metrics["count_perc"] = float(url_metrics["count"]) / total_url_count * 100
        url_metrics["time_sum"] = sum(requests_time)
        url_metrics["time_perc"] = url_metrics["time_sum"] / total_request_time * 100
        url_metrics["time_avg"] = mean(requests_time)
        url_metrics["time_max"] = max(requests_time)
        url_metrics["time_med"] = median(requests_time)

        metrics.append(url_metrics)

    return metrics


def generate_report(report_directory: str, log: LogFile, metrics: List):
    report_pattern_name = "report.html"
    report_pattern_path = os.path.join(report_directory, report_pattern_name)

    with open(report_pattern_path, encoding='utf-8') as report_pattern:
        report_text = report_pattern.read()
        report_text = Template(report_text).safe_substitute(table_json=str(metrics))

    report_name = report_name_by_date(log.date)
    report_path = os.path.join(report_directory, report_name)

    with open(report_path, "w+") as report_file:
        report_file.write(report_text)


def analyze(config: Dict):
    latest_log = find_latest_log(config["LOG_DIR"],
                                 config["FNMATCH_LOG_PATTERN"])

    if not latest_log:
        logger.info("No logs or can't parsed")
        return None

    if is_date_report_exists(config["REPORT_DIR"], latest_log.date):
        logger.info("Report already exists")
        return None

    try:
        stats = parse_log_stat(latest_log.path, config)
    except Exception as e:
        logger.exception("Can't parse log: ".format(e), exc_info=True)
        raise e

    if stats is None:
        logger.info("Parsing was finished with errors")
        return None

    metrics = calculate_metrics(stats)
    sorted_metrics = sorted(metrics, key=lambda k: k['time_sum'])
    top_metrics = sorted_metrics[-int(config["REPORT_SIZE"]):]

    try:
        generate_report(config["REPORT_DIR"], latest_log, top_metrics)
    except Exception as e:
        logger.exception("Can't generate report: {}".format(e), exc_info=True)
        raise e


def main():
    args = parse_args()
    config = load_config(args.config)

    setup_logging(config)

    try:
        analyze(config)
    except Exception as e:
        logger.exception(e, exc_info=True)
        raise e


if __name__ == "__main__":
    main()
