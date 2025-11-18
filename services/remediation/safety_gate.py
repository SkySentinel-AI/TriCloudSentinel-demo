from flask import Flask, request, jsonify
import os, requests, time
app = Flask(__name__)

@app.route("/incident", methods=["POST"])
def incident():
    inc = request.json
    print("[safety_gate] received incident:", inc)
    if inc["score"] > 0.95:
        print("[safety_gate] high-score -> require manual approval")
        return jsonify({"action":"manual","reason":"high score"}), 202
    cloud = inc["evidence"][-1][2].get("cloud","azure")
    print(f"[safety_gate] auto-remediating ip {inc['ip']} on cloud {cloud}")
    with open("/app/incidents.log", "a") as f:
        f.write(f"{time.ctime()} REMEDIATE {inc}\n")
    return jsonify({"action":"remediated","cloud":cloud}), 200

@app.route("/", methods=["GET"])
def root():
    return "safety-gate ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9100)
