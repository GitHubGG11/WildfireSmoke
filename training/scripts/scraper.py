# scrape_hpwren.py

import argparse
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote, unquote, urljoin

import requests
from bs4 import BeautifulSoup


ROOT_URL = "https://cdn.hpwren.ucsd.edu/HPWREN-FIgLib-Data/"
ROOT_INDEX_URL = urljoin(ROOT_URL, "index.html")

# Matches filenames like:
# 1465066200_+00600.jpg
# 1465065000_-00600.jpg
IMAGE_RE = re.compile(r"^\d+_([+-]\d+)\.jpg$", re.IGNORECASE)
_thread_local = threading.local()
_print_lock = threading.Lock()


def log(message: str) -> None:
    with _print_lock:
        print(message)


def get_session() -> requests.Session:
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        session.headers.update({"User-Agent": "smoke-plume-training-scraper/1.0"})
        _thread_local.session = session
    return session


def fetch_soup(url: str) -> BeautifulSoup:
    log(f"\nFetching: {url}")

    response = get_session().get(url, timeout=30)
    log(f"Status: {response.status_code}")
    response.raise_for_status()

    return BeautifulSoup(response.text, "html.parser")


def normalize_name(value: str) -> str:
    """
    Turns a link or URL path into a clean filename / directory name.

    Examples:
      '20160604_FIRE_rm-n-mobo-c/' -> '20160604_FIRE_rm-n-mobo-c'
      '1465066200_%2B00600.jpg' -> '1465066200_+00600.jpg'
    """
    value = value.strip()
    value = unquote(value)
    value = value.rstrip("/")
    value = value.split("/")[-1]
    return value


def encode_filename_for_url(filename: str) -> str:
    """
    Encodes + as %2B so HPWREN positive-offset JPG URLs work.

    Example:
      1465066200_+00600.jpg -> 1465066200_%2B00600.jpg
    """
    return quote(filename, safe="._-")


def load_dirs_from_file(path: str) -> list[str]:
    dirs = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            dirs.append(line)

    return dirs


def get_available_dirs(debug: bool = False) -> list[str]:
    """
    Reads the main HPWREN index and extracts sequence directory names.
    """
    soup = fetch_soup(ROOT_INDEX_URL)

    dirs = []
    links = soup.find_all("a")

    print(f"Found {len(links)} links on root index.")

    if debug:
        print("\nFirst 25 root links:")
        for a in links[:25]:
            print(f"  text={a.get_text(strip=True)!r}, href={a.get('href')!r}")

    for a in links:
        href = a.get("href", "")
        text = a.get_text(strip=True)

        for candidate in (href, text):
            name = normalize_name(candidate)

            if not name:
                continue

            # Directory examples:
            # 20160604_FIRE_rm-n-mobo-c
            # 20160718_FIRE_lp-n-iqeye
            if re.match(r"^\d{8}[-_].+", name):
                if not name.lower().endswith((".jpg", ".jpeg", ".png", ".html", ".tar", ".gz", ".zip")):
                    dirs.append(name)

    dirs = sorted(set(dirs))

    print(f"Parsed {len(dirs)} sequence directories from root index.")

    if debug:
        print("\nFirst 25 parsed directories:")
        for d in dirs[:25]:
            print(f"  {d}")

    return dirs


def resolve_requested_dirs(requested: list[str], available_dirs: list[str]) -> list[str]:
    """
    Allows exact directory names or partial matches.

    Example:
      20160604
    can match:
      20160604_FIRE_rm-n-mobo-c
    """
    if not requested:
        return available_dirs

    selected = []

    for item in requested:
        request_name = normalize_name(item)

        if not request_name:
            continue

        exact_matches = [d for d in available_dirs if d == request_name]

        if exact_matches:
            selected.extend(exact_matches)
            continue

        partial_matches = [
            d for d in available_dirs
            if request_name.lower() in d.lower()
        ]

        selected.extend(partial_matches)

    return sorted(set(selected))


def get_matching_jpgs(
    sequence_dir: str,
    min_offset: int,
    mode: str,
    debug: bool = False,
) -> list[tuple[str, str]]:
    """
    Reads one sequence index.html and returns matching JPG filenames + URLs.
    """
    sequence_index_url = urljoin(ROOT_URL, f"{sequence_dir}/index.html")

    soup = fetch_soup(sequence_index_url)
    links = soup.find_all("a")

    print(f"Found {len(links)} links in {sequence_dir}.")

    all_jpgs = []
    matching_jpgs = []

    if debug:
        print("\nFirst 25 sequence links:")
        for a in links[:25]:
            print(f"  text={a.get_text(strip=True)!r}, href={a.get('href')!r}")

    for a in links:
        href = a.get("href", "")
        text = a.get_text(strip=True)

        for candidate in (href, text):
            filename = normalize_name(candidate)

            match = IMAGE_RE.match(filename)

            if not match:
                continue

            if filename in all_jpgs:
                continue

            all_jpgs.append(filename)

            offset = int(match.group(1))

            if mode == "positive":
                keep = offset >= min_offset
            elif mode == "abs":
                keep = abs(offset) >= min_offset
            else:
                raise ValueError(f"Unknown mode: {mode}")

            if keep:
                encoded_filename = encode_filename_for_url(filename)
                image_url = urljoin(sequence_index_url, encoded_filename)
                matching_jpgs.append((filename, image_url))

    print(f"Found {len(all_jpgs)} total JPGs in {sequence_dir}.")
    print(f"Found {len(matching_jpgs)} matching JPGs in {sequence_dir}.")

    if debug:
        print("\nFirst 10 total JPGs:")
        for filename in all_jpgs[:10]:
            print(f"  {filename}")

        print("\nFirst 10 matching JPG URLs:")
        for filename, url in matching_jpgs[:10]:
            print(f"  {filename}")
            print(f"    {url}")

    return matching_jpgs


def download_file(url: str, output_path: Path) -> None:
    if output_path.exists():
        log(f"Skipping existing: {output_path}")
        return

    with get_session().get(url, stream=True, timeout=60) as response:
        log(f"Downloading: {url}")
        log(f"Status: {response.status_code}")
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    log(f"Saved: {output_path}")


def download_files_parallel(
    matching_jpgs: list[tuple[str, str]],
    output_dir: Path,
    workers: int,
) -> None:
    if workers <= 1:
        for filename, image_url in matching_jpgs:
            download_file(image_url, output_dir / filename)
        return

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(download_file, image_url, output_dir / filename): filename
            for filename, image_url in matching_jpgs
        }

        for future in as_completed(futures):
            filename = futures[future]
            try:
                future.result()
            except Exception as exc:
                log(f"FAILED download {filename}: {exc}")


def scrape_sequence(
    sequence_dir: str,
    output_root: Path,
    min_offset: int,
    mode: str,
    list_only: bool,
    debug: bool,
    download_workers: int,
) -> None:
    log(f"\n=== Sequence: {sequence_dir} ===")

    matching_jpgs = get_matching_jpgs(
        sequence_dir=sequence_dir,
        min_offset=min_offset,
        mode=mode,
        debug=debug,
    )

    if list_only:
        return

    output_dir = output_root / sequence_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    download_files_parallel(matching_jpgs, output_dir, download_workers)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "dirs",
        nargs="*",
        help=(
            "Directory names or partial matches. "
            "Example: 20160604_FIRE_rm-n-mobo-c or 20160604"
        ),
    )

    parser.add_argument(
        "--dirs-file",
        help="Text file containing one directory name or partial match per line.",
    )

    parser.add_argument(
        "--out",
        default="hpwren_images",
        help="Output save directory. Default: hpwren_images",
    )

    parser.add_argument(
        "--min-offset",
        type=int,
        default=600,
        help="Minimum offset. Default: 600",
    )

    parser.add_argument(
        "--mode",
        choices=["positive", "abs"],
        default="positive",
        help=(
            "positive = only +00600 and above; "
            "abs = include both +00600 and above and -00600 and below."
        ),
    )

    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only print matched directories and JPG counts; do not download.",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print extra parsing details.",
    )

    parser.add_argument(
        "--sequence-workers",
        type=int,
        default=4,
        help="Number of sequence directories to scrape in parallel. Default: 4",
    )

    parser.add_argument(
        "--download-workers",
        type=int,
        default=8,
        help="Number of image downloads per sequence to run in parallel. Default: 8",
    )

    args = parser.parse_args()

    requested_dirs = list(args.dirs)

    if args.dirs_file:
        requested_dirs.extend(load_dirs_from_file(args.dirs_file))

    available_dirs = get_available_dirs(debug=args.debug)
    selected_dirs = resolve_requested_dirs(requested_dirs, available_dirs)

    print("\nSelected directories:")
    for d in selected_dirs:
        print(f"  {d}")

    if not selected_dirs:
        raise SystemExit(
            "\nERROR: 0 directories matched. "
            "Try running with --debug or check your directory names."
        )

    output_root = Path(args.out)
    output_root.mkdir(parents=True, exist_ok=True)

    def run_sequence(sequence_dir: str) -> None:
        scrape_sequence(
            sequence_dir=sequence_dir,
            output_root=output_root,
            min_offset=args.min_offset,
            mode=args.mode,
            list_only=args.list_only,
            debug=args.debug,
            download_workers=args.download_workers,
        )

    if args.sequence_workers <= 1:
        for sequence_dir in selected_dirs:
            try:
                run_sequence(sequence_dir)
            except Exception as e:
                log(f"\nFAILED sequence {sequence_dir}: {e}")
    else:
        with ThreadPoolExecutor(max_workers=args.sequence_workers) as executor:
            futures = {
                executor.submit(run_sequence, sequence_dir): sequence_dir
                for sequence_dir in selected_dirs
            }

            for future in as_completed(futures):
                sequence_dir = futures[future]
                try:
                    future.result()
                except Exception as e:
                    log(f"\nFAILED sequence {sequence_dir}: {e}")


if __name__ == "__main__":
    main()
