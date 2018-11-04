#!/usr/bin/env python3

import unittest

from unittest.mock import patch

from log_analyzer import find_latest_log


class SearchLogTestCase(unittest.TestCase):
    def setUp(self):
        self.fnmatch_log_pattern = "nginx-access-ui.log-*"

    def test_right_latest_log(self):
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = \
                [("path", ("dir",), ('nginx-access-ui.log-20170602',
                                     'nginx-access-ui.log-20170629.gz',
                                     'nginx-access-ui.log-20170630.bz2'))]

            self.assertEqual(find_latest_log('dir', self.fnmatch_log_pattern).name,
                             "nginx-access-ui.log-20170629.gz")

    def test_no_logs(self):
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = []

        self.assertEqual(find_latest_log('dir', self.fnmatch_log_pattern),
                         None)


if __name__ == '__main__':
    unittest.main()
