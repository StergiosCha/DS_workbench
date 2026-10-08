"""Compare grammar rules, templates, lexicon rows and semantic declarations."""

import argparse
from dylan.grammar_tools import diff_grammars


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left")
    parser.add_argument("right")
    args = parser.parse_args()
    print(diff_grammars(args.left, args.right))


if __name__ == "__main__":
    main()
