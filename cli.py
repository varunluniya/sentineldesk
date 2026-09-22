"""
CLI entry point for SentinelDesk.

Usage:
    python3 cli.py                                          # run the bundled demo tickets
    python3 cli.py --text "..." --age 10 --tier standard --refund 0
"""

import argparse

from decision_trace import Ticket, evaluate_ticket
from run_demo import main as run_demo_main


def main():
    parser = argparse.ArgumentParser(description="SentinelDesk: ticket escalation decision trace")
    parser.add_argument("--text", type=str, help="the ticket's text content")
    parser.add_argument("--age", type=float, help="ticket age in hours")
    parser.add_argument("--tier", type=str, choices=["standard", "premium"], default="standard")
    parser.add_argument("--refund", type=float, default=0.0, help="refund amount requested")
    args = parser.parse_args()

    if args.text is None or args.age is None:
        print("No --text/--age given -- running the bundled demo tickets instead.\n")
        run_demo_main()
        return

    ticket = Ticket("cli-ticket", args.text, args.age, args.tier, args.refund)
    decision = evaluate_ticket(ticket)
    print(f"Escalate: {decision.escalate}")
    print(f"Reason:   {decision.reason}")


if __name__ == "__main__":
    main()
