# streaming-sketch

빅데이터 분석 과제 - 스트리밍 알고리즘 구현 및 정확도/메모리 비교

MovieLens 1M 평점 로그(약 100만 건)를 한 줄씩 읽으면서 아래 세 가지를 직접 구현해 정확한 결과(set, dict)와 비교했습니다.

- Bloom Filter : (user, movie) 쌍의 포함 여부
- Count-Min Sketch : 영화별 평점 수
- HyperLogLog : 고유 (user, movie) 쌍 / 사용자 / 영화 수

## 실행

```
# https://files.grouplens.org/datasets/movielens/ml-1m.zip 을 받아서
# ratings.dat 을 data/ 폴더에 넣기
python run_experiments.py          # 전체 실행 (5분 정도)
python run_experiments.py bloom    # 하나만 실행 (bloom / cms / hll)
python plot.py                     # figures/ 에 그래프 저장
```

표준 라이브러리만 사용하고, 그래프 그릴 때만 matplotlib이 필요합니다.

## 파일

- `sketches.py` : BloomFilter, CountMinSketch, HyperLogLog 구현
- `stream.py` : ratings.dat 을 한 줄씩 읽는 제너레이터
- `run_experiments.py` : 파라미터별 실험, 결과를 results/*.csv 로 저장
- `plot.py` : 그래프
- `results/` : 실험 결과 CSV
