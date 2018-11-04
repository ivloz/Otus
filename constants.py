#!/usr/bin/env python3

import re

LOG_LINE_PATTERN = re.compile(r'(?P<remote_address>\S+) '
                              r'(?P<remote_user>\S+)  '
                              r'(?P<real_ip>\S+) '
                              r'\[(?P<time_local>[^]]+)\] '
                              r'"(?P<request>[^"]+)" '
                              r'(?P<status>\S+) '
                              r'(?P<bytes_sent>\S+) '
                              r'"(?P<referer>[^"]+)" '
                              r'"(?P<user_agent>[^"]+)" '
                              r'"(?P<forwarded_for>[^"]+)" '
                              r'"(?P<x_request_id>\S+)" '
                              r'"(?P<x_rb_user>\S+)" '
                              r'(?P<request_time>[0-9]*\.?[0-9]*)')

LOG_REQUEST_PATTERN = re.compile(r'(?P<request_type>\w+) '
                                 r'(?P<request_url>\S+) '
                                 r'(?P<request_proto>\S+)')

LOG_DATE_PATTERN = re.compile("nginx-access-ui\.log-(?P<date>\d{7,8})($|(\.gz))")
