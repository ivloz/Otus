#!/usr/bin/env python3

import re

log_line_regexp = r'(?P<remote_address>\S+) ' \
                  r'(?P<remote_user>\S+)  ' \
                  r'(?P<real_ip>\S+) ' \
                  r'\[(?P<time_local>[^]]+)\] ' \
                  r'"(?P<request>[^"]+)" ' \
                  r'(?P<status>\S+) ' \
                  r'(?P<bytes_sent>\S+) ' \
                  r'"(?P<referer>[^"]+)" ' \
                  r'"(?P<user_agent>[^"]+)" ' \
                  r'"(?P<forwarded_for>[^"]+)" ' \
                  r'"(?P<x_request_id>\S+)" ' \
                  r'"(?P<x_rb_user>\S+)" ' \
                  r'(?P<request_time>[0-9]*\.?[0-9]*)'
log_line_pattern = re.compile(log_line_regexp)

log_request_regexp = r'(?P<request_type>\w+) (?P<request_url>\S+) (?P<request_proto>\S+)'
log_request_pattern = re.compile(log_request_regexp)

log_date_regexp = "nginx-access-ui\.log-(?P<date>\d{7,8})($|(\.gz))"
log_date_pattern = re.compile(log_date_regexp)
