from typing import List, Dict, Optional
from statistics import mean, median


def calculate_metrics(stats: Dict) -> List:
    metrics = []

    total_url_count = len(stats.keys())
    total_request_time = sum([sum(request_time) for request_time in stats.values()])

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
