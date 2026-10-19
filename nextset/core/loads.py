"""Deterministic arithmetic shared by coaching and validation."""
import math

def round_down(weight, step):
    return round(math.floor((weight+1e-9)/step)*step, 2)
