import sys
import webbrowser
import threading
import time
import uvicorn

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def open_browser():
    time.sleep(1.2)
    print("Đang mở PDF & Image Studio trên trình duyệt...")
    webbrowser.open("http://127.0.0.1:8005")


def main():
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("server:app", host="127.0.0.1", port=8005, reload=True)


if __name__ == "__main__":
    main()
