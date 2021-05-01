import math


class StdevFunc:
    def __init__(self):
        self.M = 0.0  # Mean
        self.S = 0.0  # std
        self.k = 1  # counter

    def step(self, value):
        if value is None:
            return
        tM = self.M
        self.M += (value - tM) / self.k
        self.S += (value - tM) * (value - self.M)
        self.k += 1

    def finalize(self):
        if self.k < 3:
            return None
        return math.sqrt(self.S / (self.k - 2))
