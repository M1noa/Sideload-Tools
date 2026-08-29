#!/usr/bin/env python3
"""Merge AltStore/ESign sources into 4 catalogs (standard + no-pal, cached + original links)."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, unquote

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_FILE = os.path.join(SCRIPT_DIR, 'repos-sources.txt')
MERGED_JSON = os.path.join(SCRIPT_DIR, 'merged-apps.json')
MERGED_ORIGINAL_JSON = os.path.join(SCRIPT_DIR, 'merged-apps-original-links.json')
MERGED_NO_PAL_JSON = os.path.join(SCRIPT_DIR, 'merged-apps-no-pal.json')
MERGED_ORIGINAL_NO_PAL_JSON = os.path.join(SCRIPT_DIR, 'merged-apps-original-links-no-pal.json')
TRACKING_JSON = os.path.join(SCRIPT_DIR, 'apps-tracking.json')
STATS_JSON = os.path.join(SCRIPT_DIR, 'stats.json')
FILES_DIR = os.path.join(SCRIPT_DIR, 'files')
TEMP_DIR = tempfile.mkdtemp()
SCRIPT_START_TIME = int(time.time())

TIME_LIMIT_SECONDS = 350 * 60  # 350 minutes
MIN_FREE_GB = 8                # stop downloading under 8GB free (runner headroom)
MIN_FREE_BYTES = MIN_FREE_GB * 1024 * 1024 * 1024
MAX_REPO_SIZE_GB = 98          # stop when repo exceeds 98GB (github limit)
MAX_REPO_SIZE_BYTES = MAX_REPO_SIZE_GB * 1024 * 1024 * 1024

SIDELOAD_EXTS = {'.ipa', '.dylib', '.deb', '.app', '.framework', '.bundle', '.tipa', '.a'}
MAX_FILE_SIZE = 104857600      # 100MB (github per-file limit)
DOWNLOAD_TIMEOUT = 80
MAX_NEW_GB = 2                 # per-run new-content budget so git push fits on disk
MAX_NEW_BYTES = MAX_NEW_GB * 1024 * 1024 * 1024
SKIP_DOWNLOADS = os.environ.get('MERGE_SKIP_DOWNLOADS') == '1'

# pal-only fields stripped from the no-pal variants; most apps don't support pal
PAL_FIELDS = ('appID', 'marketplaceID', 'permissions')


def speedtest():
    print('::group::Speedtest')
    url = 'https://speed.hetzner.de/100MB.bin'
    tmp = os.path.join(TEMP_DIR, 'speedtest.tmp')
    parallel = 4
    try:
        subprocess.run(['curl', '-fsSL', '--max-time', '15', '-o', tmp, url],
                       capture_output=True, timeout=20)
        if os.path.exists(tmp):
            byps = os.path.getsize(tmp)
            mbps = byps * 8 // 10000000
            print(f'Downloaded {byps // 1048576} MB => ~{mbps} Mbps')
            if mbps > 200:
                parallel = 12
            elif mbps > 100:
                parallel = 8
            elif mbps > 50:
                parallel = 5
            os.remove(tmp)
        else:
            print('Speedtest failed, using defaults.')
    except Exception:
        print('Speedtest failed, using defaults.')
    print(f'Download concurrency: {parallel}')
    print('::endgroup::')
    return parallel


def url_to_safe(url):
    return ''.join(c if c.isalnum() or c in '._-' else '_' for c in url).rstrip('_')


def is_sideload_file(url):
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in SIDELOAD_EXTS)


def fetch_sources(urls):
    def _fetch(url):
        safe = url_to_safe(url)
        tmp_file = os.path.join(TEMP_DIR, f'{safe}.json')
        print(f'::group::Fetching {url}')
        r = subprocess.run(['curl', '-fsSL', '--max-time', '60', '--retry', '3',
                            '-o', tmp_file, url], capture_output=True)
        print('OK' if r.returncode == 0 else f'::warning::Failed to fetch {url}')
        print('::endgroup::')
    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(_fetch, urls))


def get_git_tracked_files():
    # works with blobless sparse checkout
    result = subprocess.run(['git', 'ls-files', 'files/'], capture_output=True, text=True,
                            cwd=SCRIPT_DIR)
    return set(result.stdout.split()) if result.returncode == 0 else set()


GIT_TRACKED_FILES = get_git_tracked_files()


def local_file_exists(local_path):
    # true only if the cached file is actually on disk (not merely tracked in git)
    return bool(local_path) and os.path.exists(os.path.join(SCRIPT_DIR, local_path))


def elapsed_seconds():
    return int(time.time()) - SCRIPT_START_TIME


def time_remaining():
    return TIME_LIMIT_SECONDS - elapsed_seconds()


def is_time_up():
    return elapsed_seconds() >= TIME_LIMIT_SECONDS


def get_free_disk():
    stat = os.statvfs(FILES_DIR)
    return stat.f_bavail * stat.f_frsize


def get_repo_size():
    total = 0
    for root, _dirs, files in os.walk(FILES_DIR):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def is_disk_full():
    return get_free_disk() < MIN_FREE_BYTES


def is_repo_full():
    return get_repo_size() >= MAX_REPO_SIZE_BYTES


def download_file(url, dest, timeout=DOWNLOAD_TIMEOUT, max_retries=2):
    cmd = ['curl', '-fsSL', '--max-time', str(timeout), '--max-filesize',
           str(MAX_FILE_SIZE), '-o', dest, url]
    for attempt in range(max_retries + 1):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
            if result.returncode == 0:
                return 'success', ''
            if result.returncode == 63:
                return 'too_large', 'curl: file size exceeded'
            err = result.stderr.strip()
            if attempt < max_retries:
                time.sleep(1)
            else:
                return 'failed', err or f'curl exit {result.returncode}'
        except subprocess.TimeoutExpired:
            if attempt < max_retries:
                time.sleep(1)
            else:
                return 'failed', 'TimeoutExpired'
        except Exception as e:
            if attempt < max_retries:
                time.sleep(1)
            else:
                return 'error', str(e)
    return 'failed', 'max_retries'


def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def head_too_large(url, timeout=20):
    # cheap precheck: skip body, read content-length from headers
    try:
        r = subprocess.run(['curl', '-fsIL', '--max-time', str(timeout), url],
                           capture_output=True, text=True, timeout=timeout + 10)
    except Exception:
        return None
    for line in r.stdout.splitlines():
        if line.lower().startswith('content-length:'):
            try:
                return int(line.split(':', 1)[1].strip())
            except ValueError:
                return None
    return None


def detect_store(url):
    u = url.lower()
    if 'esign' in u:
        return 'ESign'
    if 'sidestore' in u or 'sidecommunity' in u:
        return 'SideStore'
    if 'feather' in u or 'app-repo.json' in u:
        return 'Feather'
    if 'ksign' in u:
        return 'KSign'
    if 'trollapps' in u:
        return 'TrollApps'
    if 'livecontainer' in u:
        return 'LiveContainer'
    return 'AltStore'


def flatten_app(app):
    versions = app.get('versions', [])
    if not versions or not isinstance(versions, list):
        return [app]
    app_base = {k: v for k, v in app.items() if k != 'versions'}
    flat = []
    for ver in versions:
        if not isinstance(ver, dict):
            continue
        entry = dict(app_base)
        entry.update(ver)
        if 'date' in ver and 'versionDate' not in ver:
            entry['versionDate'] = ver['date']
        flat.append(entry)
    return flat


def strip_pal(app):
    return {k: v for k, v in app.items() if k not in PAL_FIELDS}


def sort_date(app):
    d = app.get('versionDate', '') or ''
    if not d or d == '0':
        return (1, '')
    return (0, d)


def write_catalog(path, name, identifier, subtitle, description, apps):
    with open(path, 'w') as f:
        json.dump({
            'name': name,
            'identifier': identifier,
            'subtitle': subtitle,
            'description': description,
            'iconURL': 'https://avatars.githubusercontent.com/u/57844837',
            'appCount': len(apps),
            'sourceCount': len(URLS),
            'apps': apps,
        }, f, indent=2)




def main():
    global URLS
    os.makedirs(FILES_DIR, exist_ok=True)
    parallel_count = speedtest()

    # read source urls
    urls = []
    with open(SRC_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                urls.append(line)
    URLS = urls
    fetch_sources(urls)

    # load tracking
    tracking = {}
    if os.path.exists(TRACKING_JSON):
        try:
            with open(TRACKING_JSON) as f:
                tracking = json.load(f)
        except Exception:
            tracking = {}

    # fetch metadata + dedup by (name, bid, version), first source wins
    entries_by_key = {}
    for url in urls:
        jfile = os.path.join(TEMP_DIR, f'{url_to_safe(url)}.json')
        if not os.path.exists(jfile):
            continue
        try:
            with open(jfile) as f:
                data = json.load(f)
        except Exception:
            continue
        store = detect_store(url)
        for app in data.get('apps', data.get('sources', [])):
            if not isinstance(app, dict):
                continue
            for flat_app in flatten_app(app):
                key = (flat_app.get('name', '').lower(), flat_app.get('bundleIdentifier', ''),
                       flat_app.get('version', ''))
                if key not in entries_by_key:
                    entries_by_key[key] = flat_app
                    entries_by_key[key]['__source'] = url
                    entries_by_key[key]['__mirrors'] = []
                    entries_by_key[key]['__stores'] = [store]
                else:
                    if url not in entries_by_key[key]['__mirrors']:
                        entries_by_key[key]['__mirrors'].append(url)
                    if store not in entries_by_key[key]['__stores']:
                        entries_by_key[key]['__stores'].append(store)

    # url-based alias dedup: same downloadURL under different keys
    url_to_keys = defaultdict(list)
    for key, app in entries_by_key.items():
        dl = app.get('downloadURL', '')
        if dl:
            url_to_keys[dl].append(key)
    alias_keys = set()
    for dl, keys in url_to_keys.items():
        if len(keys) <= 1:
            continue
        canonical_key = max(keys, key=lambda k: (
            len(entries_by_key[k].get('__mirrors', [])), entries_by_key[k].get('versionDate', '')))
        canonical = entries_by_key[canonical_key]
        canonical.setdefault('__file_aliases', [])
        for ak in keys:
            if ak == canonical_key or ak in alias_keys:
                continue
            alias = entries_by_key[ak]
            alias_info = {
                'name': alias.get('name', ''),
                'bundleIdentifier': alias.get('bundleIdentifier', ''),
                'version': alias.get('version', ''),
                'source': alias.get('__source', ''),
                'stores': alias.get('__stores', []),
            }
            if alias_info not in canonical['__file_aliases']:
                canonical['__file_aliases'].append(alias_info)
            for m in alias.get('__mirrors', []):
                if m not in canonical['__mirrors']:
                    canonical['__mirrors'].append(m)
            for s in alias.get('__stores', []):
                if s not in canonical['__stores']:
                    canonical['__stores'].append(s)
            alias_keys.add(ak)
    for ak in alias_keys:
        del entries_by_key[ak]

    all_apps = list(entries_by_key.values())
    # newest -> oldest; missing/zero dates sink to the end
    all_apps.sort(key=sort_date, reverse=True)

    write_catalog(
        MERGED_ORIGINAL_JSON,
        "Minoa's Combined (PAL)",
        'com.m1noa.sideload-tools.merged.pal',
        f'Auto-merged from {len(urls)} AltStore/ESign sources. Original download URLs preserved.',
        'Deduplicates by (name, bundleIdentifier, version). __source is the first source; __mirrors lists additional sources.',
        all_apps)

    # build hash map from existing tracking
    hash_map = defaultdict(list)
    for fkey, fdata in tracking.items():
        sha256 = fdata.get('sha256', '')
        if sha256 and fdata.get('local_path'):
            hash_map[sha256].append(fkey)
    # sha256 -> first tracked file_key for O(1) dedup during the download phase
    sha_to_first = {sha: keys[0] for sha, keys in hash_map.items() if keys}

    # urls already known to exceed the file-size limit: skip re-testing
    too_large_cached = set()
    for fdata in tracking.values():
        if fdata.get('too_large') and fdata.get('original_url'):
            too_large_cached.add(fdata['original_url'])

    # build download queue (newest first)
    # O(1) lookup of already-cached download URLs so the per-app scan below
    # stays cheap (was an O(apps x tracking) linear scan per app)
    url_to_tracked = {}
    for fk, fd in tracking.items():
        u = fd.get('original_url')
        if u:
            url_to_tracked.setdefault(u, fk)

    download_queue = []
    already_queued = set()
    skipped_cached = 0
    for app in all_apps:
        name = app.get('name', 'unknown')
        bid = app.get('bundleIdentifier', '')
        ver = app.get('version', '')
        dl_url = app.get('downloadURL', '')
        file_key = f'{name}_{bid}_{ver}'.replace('/', '_').replace(':', '_')[:200]

        if not dl_url or not is_sideload_file(dl_url):
            continue
        if file_key in already_queued:
            continue
        already_queued.add(file_key)

        existing_entry = tracking.get(file_key, {})
        existing_local = existing_entry.get('local_path', '')
        if local_file_exists(existing_local):
            skipped_cached += 1
            continue

        url_already = url_to_tracked.get(dl_url)
        if url_already and local_file_exists(tracking[url_already].get('local_path')):
            skipped_cached += 1
            continue

        parsed = urlparse(dl_url)
        orig_filename = unquote(os.path.basename(parsed.path))
        if not orig_filename:
            orig_filename = f'download_{len(download_queue)}'
        ext = os.path.splitext(orig_filename)[1].lower()
        if ext not in SIDELOAD_EXTS:
            continue

        download_queue.append((file_key, app, dl_url, orig_filename))

    total_downloads = len(download_queue)
    if SKIP_DOWNLOADS:
        print('[progress] MERGE_SKIP_DOWNLOADS=1: skipping download phase, writing catalogs only.')
        download_queue = []
        total_downloads = 0

    print(f'\n[progress] Download queue: {total_downloads} files ({skipped_cached} already cached)')
    print(f'[progress] Free disk: {get_free_disk() / (1024**3):.1f} GB (min {MIN_FREE_GB} GB)')
    print(f'[progress] New-download budget: {MAX_NEW_GB} GB/run (leaves room for git push)')
    print(f'[progress] Repo size: {get_repo_size() / (1024**3):.1f} GB (max {MAX_REPO_SIZE_GB} GB)')
    print(f'[progress] Time limit: {TIME_LIMIT_SECONDS // 60}m. Elapsed: {elapsed_seconds() // 60}m. '
          f'Remaining: {time_remaining() // 60}m')

    completed = 0
    stopped_time = False
    stopped_disk = False
    stopped_budget = False
    new_bytes_lock = threading.Lock()
    state = {'new_bytes_downloaded': 0}

    def process_download(file_key, app, dl_url, orig_filename, idx):
        name = app.get('name', 'unknown')
        ver = app.get('version', '')

        if is_time_up():
            return {'file_key': file_key, 'app': app, 'status': 'skipped_time',
                    'error': 'time_limit', 'now': time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'dl_url': dl_url, 'name': name, 'ver': ver, 'local_path': '',
                    'sha256': '', 'size': 0, 'note': ''}

        if is_disk_full() or is_repo_full():
            return {'file_key': file_key, 'app': app, 'status': 'skipped_disk',
                    'error': 'disk_full', 'now': time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'dl_url': dl_url, 'name': name, 'ver': ver, 'local_path': '',
                    'sha256': '', 'size': 0, 'note': ''}

        now = time.strftime('%Y-%m-%dT%H:%M:%S')

        # skip urls already known to exceed the size limit (cached in tracking)
        if dl_url in too_large_cached:
            return {'file_key': file_key, 'app': app, 'status': 'skipped_size',
                    'error': 'cached too large', 'now': now, 'dl_url': dl_url,
                    'name': name, 'ver': ver, 'local_path': '', 'sha256': '',
                    'size': 0, 'note': 'cached_too_large'}

        # size cap is enforced by curl --max-filesize inside download_file below: it
        # aborts oversized files fast (no body when content-length is known) with no
        # extra HEAD round trip. oversized urls get cached in too_large_cached after.

        tmp_dest = os.path.join(TEMP_DIR, f'dl_{idx}_{orig_filename}')
        status, error = download_file(dl_url, tmp_dest)
        result = {'file_key': file_key, 'app': app, 'dl_url': dl_url, 'status': status,
                  'error': error, 'now': now, 'name': name, 'ver': ver,
                  'local_path': '', 'sha256': '', 'size': 0, 'note': ''}

        # curl refused download due to --max-filesize
        if status == 'too_large':
            result['status'] = 'skipped_size'
            result['note'] = 'too_large'
            sz = head_too_large(dl_url)
            result['size'] = sz if sz is not None else 0
            return result

        if status == 'success' and os.path.exists(tmp_dest) and os.path.getsize(tmp_dest) > 0:
            file_size = os.path.getsize(tmp_dest)
            if file_size > MAX_FILE_SIZE:
                os.remove(tmp_dest)
                result['status'] = 'skipped_size'
                result['error'] = f'file too large ({file_size} > {MAX_FILE_SIZE})'
                result['note'] = 'too_large'
                result['size'] = file_size
                return result

            sha256 = file_hash(tmp_dest)

            # hash dedup against previously committed files (O(1) via sha_to_first)
            existing_file = None
            first_key = sha_to_first.get(sha256)
            if first_key and first_key in tracking:
                ep = tracking[first_key].get('local_path', '')
                if local_file_exists(ep):
                    existing_file = ep
                    if file_key not in hash_map[sha256]:
                        hash_map[sha256].append(file_key)
                        sha_to_first.setdefault(sha256, file_key)

            if existing_file:
                result['local_path'] = existing_file
                result['sha256'] = sha256
                result['size'] = file_size
                os.remove(tmp_dest)
                result['note'] = 'hash_dedup'
            else:
                if is_disk_full() or is_repo_full():
                    os.remove(tmp_dest)
                    result['status'] = 'skipped_disk'
                    result['error'] = (f"disk full after download ({get_free_disk() / 1024**3:.1f} GB free, "
                                       f'repo: {get_repo_size() / 1024**3:.1f} GB)')
                    return result

                # per-run new-content budget keeps git add/commit/push within disk
                with new_bytes_lock:
                    if state['new_bytes_downloaded'] + file_size > MAX_NEW_BYTES:
                        budget_hit = True
                    else:
                        state['new_bytes_downloaded'] += file_size
                        budget_hit = False
                if budget_hit:
                    os.remove(tmp_dest)
                    result['status'] = 'skipped_budget'
                    result['error'] = f'new-download budget ({MAX_NEW_GB} GB/run) reached'
                    return result

                base, ext = os.path.splitext(orig_filename)
                candidate = f'{base}{ext}'
                counter = 0
                while os.path.exists(os.path.join(FILES_DIR, candidate)):
                    candidate = f'{base}_{counter}{ext}'
                    counter += 1
                local_path = f'files/{candidate}'
                shutil.move(tmp_dest, os.path.join(SCRIPT_DIR, local_path))
                result['local_path'] = local_path
                result['sha256'] = sha256
                result['size'] = file_size
                result['note'] = 'downloaded'
                if sha256:
                    hash_map[sha256].append(file_key)
                    sha_to_first.setdefault(sha256, file_key)

        return result

    new_files = []
    with ThreadPoolExecutor(max_workers=parallel_count) as executor:
        futures = {}
        for idx, item in enumerate(download_queue):
            if is_time_up():
                stopped_time = True
                print(f"[progress] Time limit reached at {elapsed_seconds() // 60}m. "
                      f'{completed}/{total_downloads} done.')
                break
            if is_disk_full() or is_repo_full():
                stopped_disk = True
                print(f'[progress] Disk full ({get_free_disk() / 1024**3:.1f} GB free < {MIN_FREE_GB} GB) '
                      f'or repo full ({get_repo_size() / 1024**3:.1f} GB >= {MAX_REPO_SIZE_GB} GB). '
                      f'{completed}/{total_downloads} done.')
                break
            future = executor.submit(process_download, *item, idx)
            futures[future] = item[0]

        for future in as_completed(futures):
            r = future.result()
            file_key = r['file_key']
            app = r['app']
            name = r['name']
            ver = r['ver']
            dl_url = r['dl_url']
            status = r['status']
            error = r['error']
            now = r['now']
            note = r.get('note', '')
            local_path = r.get('local_path', '')
            sha256 = r.get('sha256', '')
            size = r.get('size', 0)
            completed += 1

            if status in ('skipped_time', 'skipped_disk', 'skipped_budget'):
                continue

            entry = {
                'filename': os.path.basename(local_path) if local_path else '',
                'original_url': dl_url,
                'local_path': local_path,
                'size': size,
                'sha256': sha256,
                'duplicate_of': [],
                'status_codes': {now: 200 if status == 'success' else 0},
                'last_checked': now,
                'last_error': error if status != 'success' else '',
                'too_large': note in ('too_large', 'cached_too_large'),
                'app_metadata': {
                    'name': app.get('name', ''),
                    'bundleIdentifier': app.get('bundleIdentifier', ''),
                    'version': app.get('version', ''),
                    'versionDate': app.get('versionDate', ''),
                    'subtitle': app.get('subtitle', ''),
                    'developerName': app.get('developerName', ''),
                },
            }

            if note == 'hash_dedup' and local_path:
                for fk, fdata in tracking.items():
                    if fdata.get('local_path') == local_path:
                        entry['duplicate_of'].append(fk)
                        if fk in tracking:
                            tracking[fk].setdefault('duplicate_of', [])
                            if file_key not in tracking[fk]['duplicate_of']:
                                tracking[fk]['duplicate_of'].append(file_key)
                        break

            tracking[file_key] = entry

            if note in ('too_large', 'cached_too_large'):
                too_large_cached.add(dl_url)

            if note == 'downloaded' and local_path:
                new_files.append(local_path)

            if note == 'downloaded':
                msg = (f'[progress] {completed}/{total_downloads} done: {name} v{ver} -> '
                       f'{os.path.basename(local_path)}')
            elif note == 'hash_dedup':
                msg = (f'[progress] {completed}/{total_downloads} done: {name} v{ver} '
                       f'(hash_dedup -> {os.path.basename(local_path)})')
            elif status != 'success':
                msg = f'[progress] {completed}/{total_downloads} failed: {name} v{ver} ({error})'
            else:
                msg = f'[progress] {completed}/{total_downloads} done: {name} v{ver}'

            if completed % 50 == 0:
                msg += (f' | disk: {get_free_disk() / 1024**3:.1f}GB free | repo: '
                        f"{get_repo_size() / 1024**3:.1f}GB | time: {elapsed_seconds() // 60}m elapsed")
            print(msg)

            if (is_disk_full() or is_repo_full()) and not stopped_disk:
                stopped_disk = True
                print(f'[progress] Disk full ({get_free_disk() / 1024**3:.1f} GB free) or repo full '
                      f'({get_repo_size() / 1024**3:.1f} GB >= {MAX_REPO_SIZE_GB} GB) after download. '
                      f'Stopping. {completed}/{total_downloads} done.')

            if state['new_bytes_downloaded'] >= MAX_NEW_BYTES and not stopped_budget:
                stopped_budget = True
                print(f'[progress] New-content budget ({MAX_NEW_GB} GB/run) reached. Stopping new '
                      f'downloads. {completed}/{total_downloads} done.')

    if stopped_time:
        print('\n[progress] STOPPED: time limit. Remaining downloads resume next run.')
    if stopped_disk:
        print(f'\n[progress] STOPPED: disk full ({get_free_disk() / 1024**3:.1f} GB free) or repo full '
              f'({get_repo_size() / 1024**3:.1f} GB >= {MAX_REPO_SIZE_GB} GB). '
              'Remaining downloads resume next run.')
    if stopped_budget:
        print(f"\n[progress] STOPPED: new-download budget ({MAX_NEW_GB} GB/run) to leave room for git "
              'push. Remaining downloads resume next run.')

    # update tracking for all apps (including cached)
    for app in all_apps:
        name = app.get('name', '')
        bid = app.get('bundleIdentifier', '')
        ver = app.get('version', '')
        dl_url = app.get('downloadURL', '')
        file_key = f'{name}_{bid}_{ver}'.replace('/', '_').replace(':', '_')[:200]
        meta = {
            'name': name,
            'bundleIdentifier': bid,
            'version': ver,
            'versionDate': app.get('versionDate', ''),
            'subtitle': app.get('subtitle', ''),
            'developerName': app.get('developerName', ''),
        }
        if file_key not in tracking:
            tracking[file_key] = {
                'filename': '',
                'original_url': dl_url,
                'local_path': '',
                'size': 0,
                'sha256': '',
                'duplicate_of': [],
                'status_codes': {},
                'last_checked': '',
                'last_error': '',
                'app_metadata': meta,
            }
        else:
            tracking[file_key].setdefault('app_metadata', {})
            tracking[file_key]['app_metadata'].update(meta)
            if dl_url:
                tracking[file_key]['original_url'] = dl_url

    # merged catalog with local raw github urls where cached
    merged_apps = []
    for app in all_apps:
        name = app.get('name', '')
        bid = app.get('bundleIdentifier', '')
        ver = app.get('version', '')
        file_key = f'{name}_{bid}_{ver}'.replace('/', '_').replace(':', '_')[:200]
        tracking_entry = tracking.get(file_key, {})
        local_path = tracking_entry.get('local_path', '')
        app_copy = dict(app)
        if local_path and local_file_exists(local_path):
            app_copy['downloadURL'] = \
                f'https://raw.githubusercontent.com/M1noa/Sideload-Tools/main/{local_path}'
        else:
            app_copy['downloadURL'] = app.get('downloadURL', '')
        dup_of = tracking_entry.get('duplicate_of', [])
        if dup_of:
            hash_dups = []
            for dk in dup_of:
                am = tracking.get(dk, {}).get('app_metadata', {})
                hash_dups.append({
                    'name': am.get('name', ''),
                    'bundleIdentifier': am.get('bundleIdentifier', ''),
                    'version': am.get('version', ''),
                })
            app_copy['__hash_duplicates'] = hash_dups
        merged_apps.append(app_copy)

    merged_apps.sort(key=sort_date, reverse=True)

    write_catalog(
        MERGED_JSON,
        "Minoa's Combined (Cached, PAL)",
        'com.m1noa.sideload-tools.merged.cached.pal',
        f'Auto-merged from {len(urls)} AltStore/ESign sources. Local download URLs provided for cached files.',
        'Deduplicates by (name, bundleIdentifier, version). downloadURL points to local repo copy if available, otherwise original URL. Downloads newest first; resumes from last run.',
        merged_apps)

    # no-pal variants: strip pal fields + leftover nested versions arrays
    write_catalog(
        MERGED_ORIGINAL_NO_PAL_JSON,
        "Minoa's Combined",
        'com.m1noa.sideload-tools.merged',
        f'Auto-merged from {len(urls)} AltStore/ESign sources. Original URLs, PAL fields removed for maximum compatibility.',
        'Same as the original-links catalog but strips appID/marketplaceID/permissions (AltStore PAL) and nested versions arrays.',
        [strip_pal(a) for a in all_apps])

    write_catalog(
        MERGED_NO_PAL_JSON,
        "Minoa's Combined (Cached)",
        'com.m1noa.sideload-tools.merged.cached',
        f'Auto-merged from {len(urls)} AltStore/ESign sources. Local cached URLs where available, PAL fields removed.',
        'Same as the merged catalog but strips appID/marketplaceID/permissions (AltStore PAL) and nested versions arrays.',
        [strip_pal(a) for a in merged_apps])

    # stats for shields.io endpoint badges (sources / total ipas / percent cached)
    sources = len(urls)
    total_apps = len(merged_apps)
    cached = sum(1 for a in merged_apps
                 if str(a.get('downloadURL', '')).startswith(
                     'https://raw.githubusercontent.com/M1noa/Sideload-Tools/main/files/'))
    percent_cached = round(cached / total_apps * 100, 1) if total_apps else 0
    with open(STATS_JSON, 'w') as f:
        json.dump({
            'schemaVersion': 1,
            'sources': sources,
            'total_apps': total_apps,
            'cached': cached,
            'percent_cached': percent_cached,
        }, f, indent=2)

    # static shields.io endpoint badge files (each a complete {label,message} badge,
    # so shields renders directly without JSONPath query)
    badge_files = {
        'badge-sources.json': ('Sources', str(sources), 'blue'),
        'badge-ipas.json': ('IPAs', str(total_apps), 'brightgreen'),
        'badge-cached.json': ('Cached', f'{percent_cached}%', 'orange'),
    }
    for fname, (label, message, color) in badge_files.items():
        with open(os.path.join(SCRIPT_DIR, fname), 'w') as f:
            json.dump({'schemaVersion': 1, 'label': label, 'message': message,
                       'color': color}, f)

    with open(TRACKING_JSON, 'w') as f:
        json.dump(tracking, f, indent=2)

    with open(os.path.join(SCRIPT_DIR, 'new_files.txt'), 'w') as f:
        for nf in new_files:
            f.write(nf + '\n')

    downloaded_count = sum(1 for v in tracking.values()
                           if v.get('local_path')
                           and os.path.exists(os.path.join(SCRIPT_DIR, v['local_path'])))
    pending_count = sum(1 for v in tracking.values() if not v.get('local_path'))
    failed_count = sum(1 for v in tracking.values()
                       if v.get('last_error') and not v.get('local_path'))

    print(f'\nDone. Elapsed: {elapsed_seconds() // 60}m')
    print(f'  merged-apps.json: {len(merged_apps)} apps')
    print(f'  merged-apps-original-links.json: {len(all_apps)} apps')
    print(f'  merged-apps-no-pal.json: {len(merged_apps)} apps')
    print(f'  merged-apps-original-links-no-pal.json: {len(all_apps)} apps')
    print(f'  apps-tracking.json: {len(tracking)} entries')
    print(f'  Cached files: {downloaded_count}')
    print(f'  Pending downloads: {pending_count}')
    print(f'  Failed downloads: {failed_count}')
    print(f'  Free disk: {get_free_disk() / 1024**3:.1f} GB')
    if stopped_time or stopped_disk:
        print('  STOPPED EARLY -- remaining downloads resume next run (every 12h)')


if __name__ == '__main__':
    sys.exit(main())
