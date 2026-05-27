"""
main.py — CLI entry point for the Agentic BI Analyst.

Usage:
    python -m src.main
    python -m src.main "Why did MRR drop in Q3 2025?"
"""

import sys
from src.agent import run_agent

DEFAULT_QUESTION = "Why did MRR drop in Q3 2025?"


def main():
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = DEFAULT_QUESTION

    answer = run_agent(question)

    print("\n" + "="*60)
    print("AGENT ANSWER")
    print("="*60)
    print(answer)


if __name__ == "__main__":
    main()
