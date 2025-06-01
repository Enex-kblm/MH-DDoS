# app.py
from flask import Flask, render_template, request, jsonify
import subprocess
import threading
import os
import signal
import re
from urllib.parse import urlparse

app = Flask(__name__)

# Daftar target yang diizinkan (sesuai dengan AUTHORIZED_TARGETS di mhddos.py)
AUTHORIZED_TARGETS = ["client1.com", "client2.net"]  # Ganti dengan target resmi klien

# Status serangan
attack_status = {
    "running": False,
    "process": None,
    "thread": None,
    "method": "",
    "target": "",
    "threads": 0,
    "duration": 0
}

def is_authorized_target(target):
    """Memeriksa apakah target diizinkan berdasarkan AUTHORIZED_TARGETS"""
    try:
        # Ekstrak host dari URL
        parsed = urlparse(target)
        host = parsed.hostname
        
        # Periksa apakah host ada dalam daftar yang diizinkan
        return any(authorized_host in host for authorized_host in AUTHORIZED_TARGETS)
    except:
        return False

def run_attack(method, target, threads, duration, rpc, proxies, rate_limit):
    try:
        # Validasi target sebelum menjalankan serangan
        if not is_authorized_target(target):
            raise Exception("Target tidak diizinkan untuk diserang")
        
        # Set environment variable untuk rate limiting
        os.environ["RATE_LIMIT"] = str(rate_limit)
        
        # Build command berdasarkan parameter serangan
        cmd = f"python mhddos.py {method} {target} {threads} {duration}"
        
        if method in ["GET", "POST", "CFB", "TOR"]:
            cmd += f" {rpc}"
            if proxies:
                with open("files/proxies.txt", "w") as f:
                    f.write(proxies)
                cmd += " files/proxies.txt"
        
        # Jalankan perintah serangan
        attack_status["process"] = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        attack_status["process"].wait()
    except Exception as e:
        print(f"Attack error: {str(e)}")
    finally:
        attack_status["running"] = False
        # Hapus environment variable setelah selesai
        if "RATE_LIMIT" in os.environ:
            del os.environ["RATE_LIMIT"]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_attack', methods=['POST'])
def start_attack():
    if attack_status["running"]:
        return jsonify({"status": "error", "message": "Attack already running"})
    
    data = request.json
    attack_status.update({
        "running": True,
        "method": data["method"],
        "target": data["target"],
        "threads": data["threads"],
        "duration": data["duration"]
    })
    
    # Validasi target
    if not is_authorized_target(data["target"]):
        return jsonify({
            "status": "error",
            "message": "Target tidak diizinkan untuk diserang"
        })
    
    # Start attack in a separate thread
    attack_thread = threading.Thread(
        target=run_attack,
        args=(
            data["method"],
            data["target"],
            data["threads"],
            data["duration"],
            data.get("rpc", 1),
            data.get("proxies", ""),
            data.get("rate_limit", 0)  # Default 0 = unlimited
        )
    )
    attack_thread.start()
    attack_status["thread"] = attack_thread
    
    return jsonify({"status": "success", "message": "Attack started"})

@app.route('/stop_attack', methods=['POST'])
def stop_attack():
    if attack_status["running"] and attack_status["process"]:
        try:
            # Kirim SIGTERM ke grup proses
            os.killpg(os.getpgid(attack_status["process"].pid), signal.SIGTERM)
            attack_status["running"] = False
            return jsonify({"status": "success", "message": "Attack stopped"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    return jsonify({"status": "error", "message": "No attack running"})

@app.route('/get_stats', methods=['GET'])
def get_stats():
    # Dalam implementasi nyata, Anda akan mengumpulkan statistik aktual
    return jsonify({
        "requests": "1,250,456",
        "data": "2.4 GB",
        "time": "125s",
        "status": "RUNNING" if attack_status["running"] else "IDLE"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)