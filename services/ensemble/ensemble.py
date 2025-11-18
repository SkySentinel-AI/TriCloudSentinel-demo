from flask import Flask, request, jsonify
from collections import defaultdict
import time, requests





# --- resilient poster ---
def post_incident(incident, retries=3, timeout=2, base_backoff=0.5):
    """Post incident to safety_gate with retries and backoff.
    Returns HTTP status code on success, or None on failure.
    """
    url = "http://safety_gate:9100/incident"
    for attempt in range(1, retries + 1):
        try:
            r = requests.post(url, json=incident, timeout=timeout)
            status = getattr(r, "status_code", None)
            print(f"[ensemble] post_incident attempt {attempt} -> {status}")
            if status and 200 <= status < 300:
                return status
        except Exception as e:
            print(f"[ensemble] post_incident attempt {attempt} failed: {e}")

        if attempt < retries:
            sleep_time = base_backoff * (2 ** (attempt - 1))
            print(f"[ensemble] sleeping {sleep_time:.2f}s before retry")
            time.sleep(sleep_time)

    print("[ensemble] post_incident: all retries failed")
    return None
# --- end resilient poster ---

# --- helper: safely post incidents with retries (handles safety_gate startup race) ---
import socket
import time as _time
from requests.exceptions import RequestException

def post_incident(incident, url="http://safety_gate:9100/incident", retries=4, backoff=0.25):
    """Try to post incident with a few retries. Returns (True, resp) or (False, error)."""
    attempt = 0
    while attempt < retries:
        try:
            r = requests.post(url, json=incident, timeout=2)
            return True, r
        except RequestException as e:
            # common transient errors include DNS/name resolution or connection refused
            # wait with exponential backoff and retry
            _time.sleep(backoff * (2 ** attempt))
            attempt += 1
    return False, "max-retries"
# --- end helper ---

app = Flask(__name__)
ip_scores = defaultdict(list)

@app.route("/ingest", methods=["POST"])
def ingest():
    data = request.json or {}

    # --- defensive context normalization ---
    ctx = data.get("context", None)

    if ctx is None:
        ctx = {}
    elif isinstance(ctx, str):
        ctx = {"note": ctx}
    elif not isinstance(ctx, dict):
        try:
            ctx = dict(ctx)
        except Exception:
            ctx = {"raw_context": str(ctx)}

    data["context"] = ctx
    # --- end defensive block ---

    ip = data["context"].get("ip")
    # Validate presence of ip and score
    if not ip:
        return jsonify({"error": "missing ip in context"}), 400

    try:
        score = float(data.get("score", 0.0))
    except Exception:
        score = 0.0

    ip_scores[ip].append((time.time(), score, data["context"]))
    # keep last 60 seconds of evidence
    ip_scores[ip] = [(t,s,c) for (t,s,c) in ip_scores[ip] if t > time.time() - 60]
    avg = sum(s for (_,s,_) in ip_scores[ip]) / max(1, len(ip_scores[ip]))
    print(f"[ensemble] ip={ip} avg={avg:.3f} entries={len(ip_scores[ip])}")

    if avg > 0.6 and len(ip_scores[ip]) >= 2:
        incident = {"ip": ip, "score": avg, "evidence": ip_scores[ip]}
        try:
            post_incident(incident)
            print("[ensemble] incident posted to safety_gate", incident)
        except Exception as e:
            print("Failed to post incident:", e)

    return jsonify({"status": "ok"}), 200

@app.route("/metrics", methods=["GET"])
def metrics():
    return "ok", 200


# --- simple health endpoint (satisfy docker healthcheck) ---
@app.route('/health', methods=['GET'])
def health():
    return 'ok', 200
# --- end health endpoint ---



# --- incident helper (centralized posting + logging) ---
def post_incident(incident):
    try:
        r = post_incident(incident)
        print("[ensemble] incident posted", getattr(r, "status_code", None))
        return True
    except Exception as e:
        print("Failed to post incident:", e)
        return False

# --- human-readable metrics endpoint ---
@app.route("/metrics/text", methods=["GET"])
def metrics_text():
    lines = []
    for ip, entries in ip_scores.items():
        avg = sum(s for (_,s,_) in entries) / max(1, len(entries))
        lines.append(f"{ip} avg={avg:.3f} entries={len(entries)}")
    return "\n".join(lines), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)

# --- simple health endpoint (added to satisfy docker healthcheck) ---
@app.route("/health", methods=["GET"])
def health():
    return "ok", 200
