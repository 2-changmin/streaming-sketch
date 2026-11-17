import csv
import sys
import time
from collections import Counter

from sketches import BloomFilter, CountMinSketch, HyperLogLog
from stream import rating_stream

N_INSERT = 500_000   # Bloom Filter에 넣을 이벤트 수 (나머지는 조회용)


def deep_size(container):
    # set / dict 의 실제 크기 (컨테이너 + 안에 들어있는 객체)
    size = sys.getsizeof(container)
    if isinstance(container, dict):
        size += sum(sys.getsizeof(k) + sys.getsizeof(v) for k, v in container.items())
    else:
        size += sum(sys.getsizeof(x) for x in container)
    return size


def save(name, header, rows):
    with open(f"results/{name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"-> results/{name}.csv")


# ---------------------------------------------------------------- Bloom Filter
def bloom_experiment():
    print("[Bloom Filter]")
    # ground truth: set
    t0 = time.perf_counter()
    seen = set()
    fp_exact = 0
    for i, (u, m) in enumerate(rating_stream()):
        key = u + ":" + m
        if i < N_INSERT:
            seen.add(key)
        elif key in seen:
            fp_exact += 1
    t_set = time.perf_counter() - t0
    n_query = i + 1 - N_INSERT
    print(f"set: {t_set:.2f}s, {deep_size(seen)/1e6:.1f}MB, 조회 {n_query}건 중 실제 포함 {fp_exact}건")
    rows = [["set", "", "", deep_size(seen), "", 0.0, "", 0, round(t_set, 3),
             round((i + 1) / t_set)]]

    for bits_per in [2, 4, 8, 12, 16]:
        for k in [1, 2, 3, 4, 6, 8, 11]:
            m = bits_per * N_INSERT
            bf = BloomFilter(m, k)
            fp = fn = 0
            t0 = time.perf_counter()
            for i, (u, mv) in enumerate(rating_stream()):
                key = u + ":" + mv
                if i < N_INSERT:
                    bf.add(key)
                elif key in bf:
                    fp += 1      # 뒤쪽 절반은 전부 처음 보는 쌍이므로 True면 오탐
            t = time.perf_counter() - t0
            # 넣은 원소가 빠지지 않는지(false negative) 확인
            for j, (u, mv) in enumerate(rating_stream()):
                if j >= 20000:
                    break
                if (u + ":" + mv) not in bf:
                    fn += 1
            fpr = fp / n_query
            th = BloomFilter.theory_fpr(N_INSERT, m, k)
            rows.append(["bloom", bits_per, k, bf.nbytes(), m, fpr, th, fn,
                         round(t, 3), round((i + 1) / t)])
            print(f"m/n={bits_per:2d} k={k:2d}  FPR={fpr:.5f} (이론 {th:.5f})  {t:.2f}s")
    save("bloom", ["type", "bits_per_elem", "k", "bytes", "m_bits", "fpr",
                   "theory_fpr", "false_neg", "time_s", "events_per_s"], rows)


# ------------------------------------------------------------ Count-Min Sketch
def cms_experiment():
    print("[Count-Min Sketch]")
    t0 = time.perf_counter()
    truth = Counter()
    n = 0
    for _, m in rating_stream():
        truth[m] += 1
        n += 1
    t_dict = time.perf_counter() - t0
    top10 = [k for k, _ in truth.most_common(10)]
    print(f"dict: {t_dict:.2f}s, {deep_size(truth)/1e3:.1f}KB, 항목 {len(truth)}개")
    rows = [["dict", "", "", deep_size(truth), 0, 0, 0, 0, 0, 10, round(t_dict, 3),
             round(n / t_dict)]]

    configs = [(w, d) for w in [128, 256, 512, 1024, 2048, 4096, 8192] for d in [1, 2, 3, 4, 5, 8]]
    for w, d in configs:
        cms = CountMinSketch(w, d)
        t0 = time.perf_counter()
        for _, m in rating_stream():
            cms.add(m)
        t = time.perf_counter() - t0

        errs = [cms.query(k) - c for k, c in truth.items()]
        assert min(errs) >= 0            # 과소추정은 없어야 함
        mae = sum(errs) / len(errs)
        mre = sum(e / truth[k] for e, k in zip(errs, truth)) / len(errs)
        exact = sum(e == 0 for e in errs) / len(errs)
        top_re = sum((cms.query(k) - truth[k]) / truth[k] for k in top10) / 10
        est_top = sorted(truth, key=cms.query, reverse=True)[:10]
        hit = len(set(est_top) & set(top10))
        rows.append(["cms", w, d, cms.nbytes(), round(mae, 2), round(mre, 4),
                     max(errs), round(exact, 4), round(top_re, 5), hit,
                     round(t, 3), round(n / t)])
        print(f"w={w:5d} d={d}  MAE={mae:9.1f}  평균상대오차={mre:8.3f}  top10 일치={hit}  {t:.2f}s")
    save("cms", ["type", "width", "depth", "bytes", "mae", "mean_rel_err", "max_err",
                 "exact_ratio", "top10_rel_err", "top10_hit", "time_s", "events_per_s"], rows)


# ---------------------------------------------------------------- HyperLogLog
def hll_experiment():
    print("[HyperLogLog]")
    t0 = time.perf_counter()
    users, movies, pairs = set(), set(), set()
    n = 0
    for u, m in rating_stream():
        users.add(u)
        movies.add(m)
        pairs.add(u + ":" + m)
        n += 1
    t_all = time.perf_counter() - t0
    t0 = time.perf_counter()
    only_pairs = set()
    for u, m in rating_stream():
        only_pairs.add(u + ":" + m)
    t_set = time.perf_counter() - t0
    truth = {"user": len(users), "movie": len(movies), "pair": len(pairs)}
    print(truth, f"set(pair): {t_set:.2f}s, {deep_size(pairs)/1e6:.1f}MB")
    rows = [["set", "pair", "", "", deep_size(pairs), truth["pair"], truth["pair"], 0,
             round(t_set, 3), round(n / t_set)],
            ["set", "user", "", "", deep_size(users), truth["user"], truth["user"], 0, "", ""],
            ["set", "movie", "", "", deep_size(movies), truth["movie"], truth["movie"], 0, "", ""]]

    seeds = [0, 1, 2, 3, 4]
    # (1) (user,movie) 쌍의 고유 개수 : p 를 바꿔가며
    for p in [4, 6, 8, 10, 12, 14, 16]:
        for s in seeds:
            hll = HyperLogLog(p, seed=s)
            t0 = time.perf_counter()
            for u, m in rating_stream():
                hll.add(u + ":" + m)
            t = time.perf_counter() - t0
            est = hll.count()
            err = abs(est - truth["pair"]) / truth["pair"]
            rows.append(["hll", "pair", p, s, hll.nbytes(), truth["pair"], round(est, 1),
                         round(err, 5), round(t, 3), round(n / t)])
        print(f"p={p:2d} 완료")
    # (2) 고유 사용자 수 / 고유 영화 수
    for target, idx in [("user", 0), ("movie", 1)]:
        for p in [8, 10, 12, 14]:
            for s in seeds:
                hll = HyperLogLog(p, seed=s)
                for rec in rating_stream():
                    hll.add(rec[idx])
                est = hll.count()
                err = abs(est - truth[target]) / truth[target]
                rows.append(["hll", target, p, s, hll.nbytes(), truth[target],
                             round(est, 1), round(err, 5), "", ""])
    save("hll", ["type", "target", "p", "seed", "bytes", "truth", "estimate",
                 "rel_err", "time_s", "events_per_s"], rows)


if __name__ == "__main__":
    which = sys.argv[1:] or ["bloom", "cms", "hll"]
    if "bloom" in which:
        bloom_experiment()
    if "cms" in which:
        cms_experiment()
    if "hll" in which:
        hll_experiment()
