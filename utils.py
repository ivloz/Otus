#!/usr/bin/env python3

import os
import json
import logging

from typing import Dict

logger = logging.getLogger(__name__)


def setup_logging(config, log_name="main.log"):
    handlers = []

    if "LOG_DIR" in config:
        log_file = os.path.join(config["LOG_DIR"], log_name)
    else:
        log_file = None

    if log_file is None:
        handlers.append(logging.StreamHandler())
    else:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S',
                        handlers=handlers)


def load_config(config_path=None) -> Dict:
    default_config = {
        "REPORT_SIZE": 1000,
        "REPORT_DIR": "./reports",
        "LOG_DIR": "./log",
        "FNMATCH_LOG_PATTERN": "nginx-access-ui.log-*",
        "ERROR_PERCENT_THRESHOLD": 5
    }

    if not config_path:
        return default_config

    try:
        with open(config_path) as f:
            extra_config = json.loads(f.read())
    except FileNotFoundError as e:
        logger.error("Wrong config file path: {}".format(config_path))
        raise e
    except json.decoder.JSONDecodeError as e:
        logger.error("Can't load config on file path: {}".format(config_path))
        raise e

    if not isinstance(extra_config, dict):
        raise TypeError("Config has not json format")

    config = dict(extra_config, **default_config)
    return config
