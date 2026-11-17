import hashlib
import math
from array import array


def hash64_pair(key, seed=0):
    # md5 128비트를 반으로 잘라서 64비트 해시 2개로 사용
    d = hashlib.md5(f"{seed}:{key}".encode()).digest()
    h1 = int.from_bytes(d[:8], "little")
    h2 = int.from_bytes(d[8:], "little") | 1   # 홀수로 만들어 둠
    return h1, h2


class BloomFilter:
    def __init__(self, m, k, seed=0):
        self.m = m            # 비트 수
        self.k = k            # 해시 함수 개수
        self.seed = seed
        self.bits = bytearray((m + 7) // 8)

    def _positions(self, key):
        # double hashing: g_i(x) = h1 + i*h2 (mod m)
        h1, h2 = hash64_pair(key, self.seed)
        m = self.m
        return [(h1 + i * h2) % m for i in range(self.k)]

    def add(self, key):
        bits = self.bits
        for p in self._positions(key):
            bits[p >> 3] |= 1 << (p & 7)

    def __contains__(self, key):
        bits = self.bits
        for p in self._positions(key):
            if not bits[p >> 3] & (1 << (p & 7)):
                return False
        return True

    def nbytes(self):
        return len(self.bits)

    @staticmethod
    def theory_fpr(n, m, k):
        return (1 - math.exp(-k * n / m)) ** k


class CountMinSketch:
    def __init__(self, width, depth, seed=0):
        self.w = width
        self.d = depth
        self.seed = seed
        # 행 d개를 1차원 배열 하나에 이어붙임 (4바이트 카운터)
        self.table = array("I", [0]) * (width * depth)

    def _cols(self, key):
        h1, h2 = hash64_pair(key, self.seed)
        w = self.w
        return [i * w + (h1 + i * h2) % w for i in range(self.d)]

    def add(self, key, c=1):
        t = self.table
        for idx in self._cols(key):
            t[idx] += c

    def query(self, key):
        t = self.table
        return min(t[idx] for idx in self._cols(key))

    def nbytes(self):
        return self.table.itemsize * len(self.table)


class HyperLogLog:
    def __init__(self, p, seed=0):
        self.p = p
        self.m = 1 << p
        self.seed = seed
        self.reg = bytearray(self.m)   # 레지스터 하나당 1바이트

    def add(self, key):
        h, _ = hash64_pair(key, self.seed)
        j = h >> (64 - self.p)                    # 앞 p비트 = 버킷 번호
        w = h & ((1 << (64 - self.p)) - 1)        # 나머지 비트
        rho = (64 - self.p) - w.bit_length() + 1  # 첫 1이 나오는 위치
        if rho > self.reg[j]:
            self.reg[j] = rho

    def _alpha(self):
        m = self.m
        if m == 16:
            return 0.673
        if m == 32:
            return 0.697
        if m == 64:
            return 0.709
        return 0.7213 / (1 + 1.079 / m)

    def count(self):
        m = self.m
        z = sum(2.0 ** -r for r in self.reg)
        e = self._alpha() * m * m / z
        if e <= 2.5 * m:
            # 값이 작을 때는 빈 레지스터 수로 보정 (linear counting)
            v = self.reg.count(0)
            if v > 0:
                e = m * math.log(m / v)
        return e

    def nbytes(self):
        return len(self.reg)
