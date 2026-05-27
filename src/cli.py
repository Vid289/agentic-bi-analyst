"""
cli.py — Command-line interface for the Agentic BI Analyst.

Usage:
    # Ask a one-off question
    python -m src.cli "Why did MRR drop in Q3 2025?"

    # Interactive mode (asks for questions in a loop)
    python -m src.cli

Ctrl+C or typing 'exit' / 'quit' ends the session.
"""

from __future__ import annotations

import sys
from src.agent import run_agent

# A few starter questions the user can try
EXAMPLE_QUESTIONS = [
    "Why did MRR drop in Q3 2025?",
    "Which customer segments have the highest churn rate?",
    "What is the relationship between support ticket volume and churn?",
    "Which acquisition channels produce the highest LTV customers?",
]


def _print_examples() -> None:
    print("\nExample questions to try:")
    for i, q in enumerate(EXAMPLE_QUESTIONS, 1):
        print(f"  {i}. {q}")
    print()


def _run_once(question: str) -> None:
    """Run the agent for a single question and print the answer."""
    answer = run_agent(question, verbose=True)
    print("\n" + "=" * 60)
    print("ANALYST REPORT")
    print("=" * 60)
    print(answer)
    print("=" * 60 + "\n")


def _interactive_loop() -> None:
    """Prompt the user for questions until they quit."""
    print("\nAgentic BI Analyst — interactive mode")
    print("Type a business question and press Enter. Type 'exit' to quit.\n")
    _print_examples()

    while True:
        try:
            question = input("Your question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not question:
            continue
        if question.lower() in {"exit", "quit", "q"}:
            print("Bye!")
            break

        _run_once(question)


def main() -> None:
    if len(sys.argv) > 1:
        # Question passed as a command-line argument
        question = " ".join(sys.argv[1:])
        _run_once(question)
    else:
        # No argument — drop into interactive mode
        _interactive_loop()


if __name__ == "__main__":
    main()
