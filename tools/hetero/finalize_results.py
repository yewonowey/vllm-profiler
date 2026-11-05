# SPDX-License-Identifier: Apache-2.0
"""Result-table generation is deferred to WP11."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sweep-dir", type=Path, required=True)
    parser.parse_args(argv)
    print("WP11에서 구현 예정", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
