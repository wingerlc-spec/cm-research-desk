"""Synthetic Alpha Vantage style daily CSVs for an offline `screen.py --csv-dir` smoke run. Random walks: not market data."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

def main(folder, n_names=30, bars=1600, seed=7):
    out = Path(folder); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end="2026-11-13", periods=bars)
    for t in ["SPY", "QQQ", "IWM"] + [f"SYN{i:02d}" for i in range(n_names)]:
        r = rng.normal(0.0004, 0.02, bars); c = 50*np.exp(np.cumsum(r))
        if t == "SYN03": c[-5:] *= 1.12                                   # a gap up to trigger an archetype
        h, l = c*(1+rng.uniform(0, 0.02, bars)), c*(1-rng.uniform(0, 0.02, bars))
        v = rng.integers(1_000_000, 3_000_000, bars)
        pd.DataFrame(dict(timestamp=idx, open=c, high=h, low=l, close=c, adjusted_close=c, volume=v)).to_csv(out/f"{t}.csv", index=False)

if __name__ == "__main__":
    main(sys.argv[1])
