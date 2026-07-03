# review_hpwren_plus900.py

import argparse
import queue
import re
import threading
from io import BytesIO
from pathlib import Path
from urllib.parse import quote, unquote, urljoin

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageTk
import tkinter as tk


ROOT_URL = "https://cdn.hpwren.ucsd.edu/HPWREN-FIgLib-Data/"
ROOT_INDEX_URL = urljoin(ROOT_URL, "index.html")

DIR_RE = re.compile(r"^\d{8}[-_].+")
IMAGE_RE = re.compile(r"^\d+_([+-]\d+)\.jpg$", re.IGNORECASE)
_thread_local = threading.local()


def get_session() -> requests.Session:
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        session.headers.update({"User-Agent": "smoke-plume-reviewer/1.0"})
        _thread_local.session = session
    return session


def fetch_soup(url: str) -> BeautifulSoup:
    response = get_session().get(url, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def normalize_name(value: str) -> str:
    value = value.strip()
    value = unquote(value)
    value = value.rstrip("/")
    value = value.split("/")[-1]
    return value


def encode_filename_for_url(filename: str) -> str:
    return quote(filename, safe="._-")


def load_dirs_from_file(path: str) -> list[str]:
    dirs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                dirs.append(line)
    return dirs


def get_available_dirs() -> list[str]:
    soup = fetch_soup(ROOT_INDEX_URL)
    dirs = []

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = a.get_text(strip=True)

        for candidate in (href, text):
            name = normalize_name(candidate)
            if not name:
                continue
            if DIR_RE.match(name) and not name.lower().endswith(
                (".jpg", ".jpeg", ".png", ".html", ".mp4", ".tar", ".gz", ".zip")
            ):
                dirs.append(name)

    return sorted(set(dirs))


def resolve_requested_dirs(requested: list[str], available_dirs: list[str]) -> list[str]:
    if not requested:
        return available_dirs

    selected = []
    for item in requested:
        item = normalize_name(item)
        exact = [d for d in available_dirs if d == item]
        if exact:
            selected.extend(exact)
            continue
        selected.extend(d for d in available_dirs if item.lower() in d.lower())

    return sorted(set(selected))


def find_plus900_image_url(sequence_dir: str) -> tuple[str, str] | None:
    index_url = urljoin(ROOT_URL, f"{sequence_dir}/index.html")
    soup = fetch_soup(index_url)

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = a.get_text(strip=True)

        for candidate in (href, text):
            filename = normalize_name(candidate)
            match = IMAGE_RE.match(filename)
            if not match:
                continue

            if int(match.group(1)) == 900:
                encoded_filename = encode_filename_for_url(filename)
                return filename, urljoin(index_url, encoded_filename)

    return None


def download_image(image_url: str) -> Image.Image:
    response = get_session().get(image_url, timeout=60)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content))
    image.load()
    return image


def fetch_review_item(sequence_dir: str, index: int, total: int) -> dict:
    found = find_plus900_image_url(sequence_dir)
    if found is None:
        return {
            "kind": "skip",
            "sequence_dir": sequence_dir,
            "index": index,
            "total": total,
            "message": "No +00900 image found.",
        }

    filename, image_url = found
    image = download_image(image_url)
    return {
        "kind": "image",
        "sequence_dir": sequence_dir,
        "filename": filename,
        "image_url": image_url,
        "image": image,
        "index": index,
        "total": total,
    }


def append_accepted_dir(output_file: Path, sequence_dir: str) -> None:
    existing = set()
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            existing = {line.strip() for line in f if line.strip()}

    if sequence_dir in existing:
        print(f"Already saved: {sequence_dir}")
        return

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(sequence_dir + "\n")
    print(f"Saved directory: {sequence_dir}")


class ReviewApp:
    def __init__(self, selected_dirs, accepted_file, workers=6, prefetch=24):
        self.selected_dirs = selected_dirs
        self.accepted_file = accepted_file
        self.workers = max(1, workers)
        self.prefetch = max(1, prefetch)
        self.input_queue = queue.Queue()
        self.result_queue = queue.Queue(maxsize=self.prefetch)
        self.stop_event = threading.Event()
        self.current = None
        self.photo = None
        self.completed = 0

        self.root = tk.Tk()
        self.root.title("HPWREN directory review")
        self.root.geometry("1220x900")

        self.image_label = tk.Label(self.root)
        self.image_label.pack()

        self.info = tk.Label(self.root, text="Starting prefetch...", font=("Arial", 14), justify="left")
        self.info.pack(pady=10)

        self.status = tk.Label(self.root, text="", font=("Arial", 11), justify="left")
        self.status.pack(pady=4)

        self.root.bind("y", lambda event: self.choose("y"))
        self.root.bind("Y", lambda event: self.choose("y"))
        self.root.bind("n", lambda event: self.choose("n"))
        self.root.bind("N", lambda event: self.choose("n"))
        self.root.bind("q", lambda event: self.choose("q"))
        self.root.bind("Q", lambda event: self.choose("q"))
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.choose("q"))

    def start_workers(self):
        total = len(self.selected_dirs)
        for index, sequence_dir in enumerate(self.selected_dirs, start=1):
            self.input_queue.put((sequence_dir, index, total))

        for _ in range(self.workers):
            thread = threading.Thread(target=self.worker_loop, daemon=True)
            thread.start()

    def worker_loop(self):
        while not self.stop_event.is_set():
            try:
                sequence_dir, index, total = self.input_queue.get_nowait()
            except queue.Empty:
                return

            try:
                item = fetch_review_item(sequence_dir, index, total)
            except Exception as exc:
                item = {
                    "kind": "error",
                    "sequence_dir": sequence_dir,
                    "index": index,
                    "total": total,
                    "message": str(exc),
                }

            while not self.stop_event.is_set():
                try:
                    self.result_queue.put(item, timeout=0.2)
                    break
                except queue.Full:
                    continue

    def run(self):
        self.start_workers()
        self.root.after(100, self.show_next)
        self.root.mainloop()

    def show_next(self):
        if self.stop_event.is_set():
            self.root.destroy()
            return

        while True:
            try:
                item = self.result_queue.get_nowait()
            except queue.Empty:
                if self.completed >= len(self.selected_dirs):
                    self.info.config(text="Done reviewing directories.")
                    self.status.config(text=f"Accepted directories saved in: {self.accepted_file.resolve()}")
                    return

                self.info.config(text="Waiting for prefetched images...")
                self.status.config(
                    text=f"Queue: {self.result_queue.qsize()} ready | remaining: {len(self.selected_dirs) - self.completed}"
                )
                self.root.after(150, self.show_next)
                return

            self.completed += 1

            if item["kind"] == "image":
                self.current = item
                self.render_current()
                return

            print(f"Skipping {item['sequence_dir']}: {item['message']}")

    def render_current(self):
        item = self.current
        display_image = item["image"].copy()
        display_image.thumbnail((1200, 760))
        self.photo = ImageTk.PhotoImage(display_image)
        self.image_label.config(image=self.photo)
        self.root.title(f"[{item['index']}/{item['total']}] {item['sequence_dir']} - {item['filename']}")
        self.info.config(
            text=(
                f"[{item['index']}/{item['total']}] {item['sequence_dir']}\n"
                f"{item['filename']}\n\n"
                "Press y = save directory, n = skip, q = quit"
            )
        )
        self.status.config(
            text=f"Queue: {self.result_queue.qsize()} ready | fetched: {self.completed}/{len(self.selected_dirs)}"
        )

    def choose(self, choice: str):
        if choice == "q":
            print("Quitting.")
            self.stop_event.set()
            self.root.destroy()
            return

        if not self.current:
            return

        if choice == "y":
            append_accepted_dir(self.accepted_file, self.current["sequence_dir"])
        elif choice == "n":
            print(f"Skipped: {self.current['sequence_dir']}")

        self.current = None
        self.show_next()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dirs", nargs="*", help="Optional directory names or partial matches.")
    parser.add_argument("--dirs-file", help="Optional text file with one directory name or partial match per line.")
    parser.add_argument("--accepted-file", default="accepted_dirs.txt", help="Where accepted directory names are saved.")
    parser.add_argument("--start-at", default=None, help="Skip directories until this directory name is reached.")
    parser.add_argument("--workers", type=int, default=6, help="Number of background request/download workers. Default: 6")
    parser.add_argument("--prefetch", type=int, default=24, help="Maximum images to keep ready in memory. Default: 24")
    args = parser.parse_args()

    requested_dirs = list(args.dirs)
    if args.dirs_file:
        requested_dirs.extend(load_dirs_from_file(args.dirs_file))

    print("Reading root HPWREN index...")
    available_dirs = get_available_dirs()
    print(f"Found {len(available_dirs)} directories.")

    selected_dirs = resolve_requested_dirs(requested_dirs, available_dirs)

    if args.start_at:
        start_name = normalize_name(args.start_at)
        if start_name in selected_dirs:
            selected_dirs = selected_dirs[selected_dirs.index(start_name) :]
        else:
            print(f"WARNING: --start-at directory not found: {start_name}")

    if not selected_dirs:
        raise SystemExit("No matching directories found.")

    print(f"Reviewing {len(selected_dirs)} directories.")

    accepted_file = Path(args.accepted_file)
    app = ReviewApp(selected_dirs, accepted_file, workers=args.workers, prefetch=args.prefetch)
    app.run()

    print(f"\nAccepted directories saved in: {accepted_file.resolve()}")


if __name__ == "__main__":
    main()
