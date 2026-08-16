import os
import socket
import sys
import threading
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _find_free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _start_server(port: int):
    import uvicorn
    from app.main import app

    class _Server(uvicorn.Server):
        def install_signal_handlers(self):
            pass

    server = _Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            access_log=False,
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 30
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.05)
    if not server.started:
        raise RuntimeError("Локальный сервер не запустился")
    return server


def _smoke_test(port: int) -> None:
    result = "FAIL: no response"
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=10) as resp:
            result = f"OK {resp.status} {resp.read().decode()}"
    except Exception as exc:  # noqa: BLE001
        result = f"FAIL: {exc}"
    with open("jdbank_smoke_result.txt", "w", encoding="utf-8") as f:
        f.write(result)


def main() -> None:
    os.environ.setdefault("JDBANK_DESKTOP", "1")

    if getattr(sys, "frozen", False) and sys.stdout is None:
        from app.config import config

        log_file = open(
            os.path.join(config.DATA_DIR, "jdbank.log"),
            "a",
            encoding="utf-8",
            buffering=1,
        )
        sys.stdout = sys.stderr = log_file

    port = _find_free_port()
    server = _start_server(port)

    if os.environ.get("JDBANK_SMOKE_TEST") == "1":
        _smoke_test(port)
        server.should_exit = True
        return

    import webview

    webview.create_window(
        "JDBank",
        f"http://127.0.0.1:{port}/",
        width=1280,
        height=820,
        min_size=(960, 600),
    )
    webview.start()
    server.should_exit = True


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback

        with open("jdbank_crash.txt", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise