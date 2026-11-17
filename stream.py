DATA_PATH = "data/ratings.dat"


def rating_stream(path=DATA_PATH):
    """ratings.dat을 한 줄씩 읽어서 (user, movie) 를 넘겨준다."""
    with open(path, encoding="latin-1") as f:
        for line in f:
            user, movie, _rating, _ts = line.rstrip("\n").split("::")
            yield user, movie
