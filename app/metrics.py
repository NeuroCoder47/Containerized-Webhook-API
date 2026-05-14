from collections import defaultdict

http_requests_counter = defaultdict(int)
webhook_results_counter = defaultdict(int)
latency_buckets = defaultdict(int)

def record_request(path, status, latency_ms):
    http_requests_counter[(path,str(status))] += 1
    for bucket in [100,500,float("inf")]:
        if latency_ms <= bucket:
            latency_buckets[bucket] +=1
def record_webhook_result(result):
    webhook_results_counter[result] += 1 


def generate_metrics_text():
    lines =[]
    for (path, status), count in http_requests_counter.items():
        lines.append(f'http_requests_total{{path="{path}",status="{status}"}} {count}')
    for result, count in webhook_results_counter.items():
        lines.append(f'webhook_requests_total{{result="{result}"}} {count}')
    for bucket , count in latency_buckets.items():
        le = "+Inf" if bucket == float("inf") else str(bucket)
        lines.append(f'request_latency_ms_bucket{{le="{le}"}} {count}')
    return "\n".join(lines)



