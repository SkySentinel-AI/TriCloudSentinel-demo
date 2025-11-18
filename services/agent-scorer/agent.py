# simple local online scorer that exposes prometheus metric and posts score metadata to ensemble
import argparse, time, json, os, requests, random, signal, threading
from prometheus_client import start_http_server, Gauge

# env-configured default interval (can be overridden by CLI --interval)
SEND_INTERVAL = float(os.environ.get("SEND_INTERVAL", "1.0"))

_running = True
def _graceful_stop(signum, frame):
    global _running
    _running = False

signal.signal(signal.SIGINT, _graceful_stop)
signal.signal(signal.SIGTERM, _graceful_stop)

ANOM_GAUGE = Gauge("local_anomaly_score", "Local anomaly score")

def run_metrics_server(port=8000):
    start_http_server(port)
    while _running:
        time.sleep(1)

def main_loop(name, interval, ensemble_url):
    while _running:
        features = {
            "req_per_min": random.randint(1,200),
            "failed_logins": random.randint(0,10),
            "bytes_in": random.randint(100,5000)
        }
        score = min(1.0, (features["failed_logins"]*0.2 + features["req_per_min"]/500.0 + features["bytes_in"]/10000.0))
        ANOM_GAUGE.set(score)
        payload = {
            "agent": name,
            "score": score,
            "context": {
                "ip": f"192.0.2.{random.randint(2,200)}",
                "user": "demo_user",
                "cloud": name.split('-')[1] if '-' in name else name
            }
        }
        try:
            requests.post(ensemble_url + "/ingest", json=payload, timeout=1)
        except Exception as e:
            print("Warning: failed to post to ensemble:", e)
        print(f"[{name}] score={score:.3f} payload_ip={payload['context']['ip']}")
        # sleep in small increments to be more responsive to shutdown
        slept = 0.0
        step = 0.1 if interval > 0.1 else interval
        while _running and slept < interval:
            time.sleep(step)
            slept += step

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="agent-demo")
    # make default None so we can detect when CLI interval was explicitly provided
    parser.add_argument("--interval", type=float, default=None, help="send interval in seconds (CLI overrides SEND_INTERVAL env)")
    parser.add_argument("--ensemble", default="http://ensemble:9000")
    args = parser.parse_args()

    # choose interval: CLI value if provided, else env SEND_INTERVAL
    interval = args.interval if args.interval is not None else SEND_INTERVAL

    # metrics server thread (daemon)
    t = threading.Thread(target=run_metrics_server, args=(8000,), daemon=True)
    t.start()

    main_loop(args.name, interval, args.ensemble)
