import json
import logging

from typing import Dict

logger = logging.getLogger(__name__)


def setup_logging(config, log_name="main.log"):
    handlers = []

    log_file = config["LOG_DIR"] + "/" + log_name \
        if "LOG_DIR" in config \
        else None

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
        "LOG_DIR": "./log"
    }

    if not config_path:
        return default_config

    try:
        with open(config_path) as f:
            extra_config = json.loads(f.read())
    except FileNotFoundError:
        logger.error("Wrong config file path: {}".format(config_path))
        return default_config
    except json.decoder.JSONDecodeError:
        logger.error("Can't load config on file path: {}".format(config_path))
        return default_config
    except Exception as e:
        logger.error(e, exc_info=True)
        return default_config

    config = dict(extra_config, **default_config)
    return config
