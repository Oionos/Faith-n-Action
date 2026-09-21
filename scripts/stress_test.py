#!/usr/bin/env python
"""Stdlib-only load/stress harness for Faith-n-Action (no external deps).

Usage:
    python scripts/stress_test.py --base-url http://127.0.0.1:8000 --requests 200 --concurrency 10
    python scripts/stress_test.py --scenario signin --requests 100 --concurrency 5

Scenarios:
    pages   - anonymous GET / and /sign-in/ (exercises CSRF session writes)
    signin  - full CSRF-aware sign-in POST with invalid credentials
              (exercises auth path + session DB write per attempt)
    mixed   - 70% pages / 30% signin

Reports per-endpoint: count, errors, status histogram, latency
min/mean/p50/p95/p99/max, and overall RPS. Watch for 'database is locked'
errors - that is the SQLite writer-lock ceiling (PERF-1/PERF-3).
"""
import argparse
import http.cookiejar
import re
import statistics
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

CSRF_RE = re.compile(rb'name="csrfmiddlewaretoken" value="([^"]+)"')

results = []
results_lock = threading.Lock()


def make_opener():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def timed(label, fn):
    start = time.perf_counter()
    status, err = fn()
    elapsed_ms = (time.perf_counter() - start) * 1000
    with results_lock:
        results.append((label, status, err, elapsed_ms))


def do_get(base, path):
    def fn():
        opener = make_opener()
        try:
            with opener.open(base + path, timeout=30) as resp:
                resp.read()
                return resp.status, None
        except urllib.error.HTTPError as e:
            return e.code, None
        except Exception as e:
            return 0, f'{type(e).__name__}: {e}'
    return fn


def do_signin(base):
    def fn():
        opener = make_opener()
        try:
            with opener.open(base + '/sign-in/', timeout=30) as resp:
                html = resp.read()
            m = CSRF_RE.search(html)
            if not m:
                return 0, 'no-csrf-token'
            data = urllib.parse.urlencode({
                'csrfmiddlewaretoken': m.group(1).decode(),
                'username': 'stress_test_user',
                'password': 'definitely_wrong_password',
            }).encode()
            req = urllib.request.Request(
                base + '/sign-in/', data=data,
                headers={'Referer': base + '/sign-in/'},
            )
            with opener.open(req, timeout=30) as resp:
                resp.read()
                return resp.status, None
        except urllib.error.HTTPError as e:
            return e.code, None
        except Exception as e:
            return 0, f'{type(e).__name__}: {e}'
    return fn


def percentile(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    k = max(0, min(len(sorted_vals) - 1, int(p * len(sorted_vals))))
    return sorted_vals[k]


def report(base, started, total_wall):
    by_label = {}
    for label, status, err, ms in results:
        by_label.setdefault(label, []).append((status, err, ms))
    print(f'\n{"=" * 72}')
    print(f'STRESS TEST RESULTS  target={base}  wall={total_wall:.1f}s')
    print(f'{"=" * 72}')
    grand_n = len(results)
    total_err = sum(1 for _, s, e, _ in results if e or s == 0 or s >= 500)
    for label, rows in sorted(by_label.items()):
        lat = sorted(r[2] for r in rows)
        n = len(rows)
        errs = sum(1 for s, e, _ in rows if e or s == 0 or s >= 500)
        hist = {}
        for s, e, _ in rows:
            key = str(s) if not e else f'ERR({e})'
            hist[key] = hist.get(key, 0) + 1
        print(f'\n[{label}] n={n} errors={errs} ({100 * errs / max(n, 1):.1f}%)')
        print(f'  statuses: {dict(sorted(hist.items()))}')
        print(f'  latency ms: min={lat[0]:.0f} mean={statistics.mean(lat):.0f} '
              f'p50={percentile(lat, 0.50):.0f} p95={percentile(lat, 0.95):.0f} '
              f'p99={percentile(lat, 0.99):.0f} max={lat[-1]:.0f}')
    print(f'\nOVERALL: {grand_n} requests, {total_err} errors, '
          f'{grand_n / max(total_wall, 0.001):.1f} req/s')
    lock_errs = sum(1 for _, s, e, _ in results if e and 'locked' in str(e).lower())
    if lock_errs:
        print(f'!! {lock_errs} database-lock errors -> SQLite writer-lock ceiling hit (PERF-3)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base-url', default='http://127.0.0.1:8000')
    ap.add_argument('--scenario', choices=['pages', 'signin', 'mixed'], default='mixed')
    ap.add_argument('--requests', type=int, default=200)
    ap.add_argument('--concurrency', type=int, default=10)
    args = ap.parse_args()

    tasks = []
    for i in range(args.requests):
        if args.scenario == 'pages' or (args.scenario == 'mixed' and i % 10 < 7):
            tasks.append(('GET /', do_get(args.base_url, '/')))
        elif args.scenario == 'signin' or (args.scenario == 'mixed'):
            tasks.append(('POST /sign-in/ (bad creds)', do_signin(args.base_url)))
        tasks.append(('GET /sign-in/', do_get(args.base_url, '/sign-in/')))

    print(f'Firing {len(tasks)} requests at {args.base_url} with concurrency={args.concurrency}')
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for label, fn in tasks:
            pool.submit(timed, label, fn)
    report(args.base_url, started, time.perf_counter() - started)


if __name__ == '__main__':
    main()
