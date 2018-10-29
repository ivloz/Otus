#!/usr/bin/env python3

import json
import unittest

from unittest.mock import patch, mock_open

from utils import load_config


class ImportConfigTestCase(unittest.TestCase):
    def test_no_config_path(self):
        config_path = None
        config = load_config(config_path)
        self.assertIsInstance(config, dict, "Incorrect default dict")

    def test_wrong_config_path(self):
        config_path = "test/wrong/path/qwe.qq"
        self.assertRaises(FileNotFoundError, load_config, config_path)

    def test_config_file_with_wrong_config(self):
        with patch("utils.open", mock_open(read_data="{'1': 3};")) as mock_file:
            self.assertRaises(json.decoder.JSONDecodeError, load_config, "path/to/open")
            mock_file.assert_called_with("path/to/open")

    def test_file_config_is_not_json(self):
        with patch("utils.open", mock_open(read_data="123")) as mock_file:
            self.assertRaises(TypeError, load_config, "path/to/open")
            mock_file.assert_called_with("path/to/open")


if __name__ == '__main__':
    unittest.main()
