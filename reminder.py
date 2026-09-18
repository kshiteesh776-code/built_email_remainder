#!/usr/bin/env python3
"""
reminder.py
===========
Main entry point for the Bulk Email Reminder Tool.

Reads recipient records from CSV, filters due items based on a configurable
window, and sends personalized reminder emails via SMTP.
"""

import argparse
import os
import sys
from datetime import date, datetime

try:
    from dotenv import load_dotenv
except ImportError:
    # Graceful fallback if python-dotenv is not installed
    def load_dotenv(dotenv_path: str = ".env"):
        """Simple native .env loader fallback."""
        if not os.path.exists(dotenv_path):
            return
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = val

from csv_reader import load_recipients_from_csv, filter_due_reminders, parse_date
from email_sender import EmailSender
from logger_config import setup_logger


def parse_arguments() -> argparse.Namespace:
    """Configures and parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Bulk Email Reminder Tool - Automatically send personalized due-date reminder emails.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--days",
        type=int,
        default=2,
        help="Reminder window threshold in days (reminders due today or within next N days).",
    )

    parser.add_argument(
        "--csv",
        type=str,
        default="recipients.csv",
        help="Path to the recipients CSV file.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without dispatching actual emails over SMTP (useful for previewing and testing).",
    )

    parser.add_argument(
        "--log-file",
        type=str,
        default="email_log.log",
        help="Path to the output log file.",
    )

    parser.add_argument(
        "--ref-date",
        type=str,
        default=None,
        help="Custom reference date in YYYY-MM-DD format (defaults to current date).",
    )

    return parser.parse_args()


def print_banner(days_window: int, csv_path: str, dry_run: bool, ref_date: date):
    """Prints a friendly command-line banner."""
    print("=" * 65)
    print("          BULK EMAIL REMINDER TOOL           ")
    print("=" * 65)
    print(f" Reference Date : {ref_date}")
    print(f" Target Window  : Next {days_window} day(s)")
    print(f" CSV Data Source: {csv_path}")
    print(f" Execution Mode : {'DRY-RUN (Simulated)' if dry_run else 'LIVE (Sending Emails)'}")
    print("=" * 65)


def print_summary(
    total_valid: int,
    total_due: int,
    sent_count: int,
    failed_count: int,
    dry_run: bool,
    log_file: str,
):
    """Prints a summary report table to the terminal."""
    print("\n" + "=" * 65)
    print("                 EXECUTION SUMMARY                   ")
    print("=" * 65)
    print(f" Total Valid Recipients in CSV : {total_valid}")
    print(f" Total Reminders Due in Window : {total_due}")
    action_label = "Simulated Dispatched" if dry_run else "Successfully Sent"
    print(f" {action_label:<30}: {sent_count}")
    print(f" {'Failed / Errored':<30}: {failed_count}")
    print(f" Detailed Logs Written To      : {log_file}")
    print("=" * 65 + "\n")


def main() -> int:
    """Main execution function."""
    # Load environment variables from .env file
    load_dotenv()

    args = parse_arguments()
    logger = setup_logger(log_file=args.log_file)

    # Determine reference date
    if args.ref_date:
        parsed_ref = parse_date(args.ref_date)
        if not parsed_ref:
            logger.error(f"Invalid reference date format '{args.ref_date}'. Expected YYYY-MM-DD.")
            return 1
        ref_date = parsed_ref
    else:
        ref_date = date.today()

    print_banner(
        days_window=args.days,
        csv_path=args.csv,
        dry_run=args.dry_run,
        ref_date=ref_date,
    )

    logger.info(
        f"Starting Bulk Email Reminder Tool (Window: {args.days} days, CSV: '{args.csv}', Mode: {'DRY RUN' if args.dry_run else 'LIVE'})"
    )

    # 1. Load and parse CSV
    valid_recipients, csv_errors = load_recipients_from_csv(args.csv, logger=logger)
    if not valid_recipients and csv_errors and not os.path.exists(args.csv):
        print(f"\n[ERROR] CSV file '{args.csv}' not found. Please create it or specify with --csv.")
        return 1

    if not valid_recipients:
        print("\n[INFO] No valid recipient records found to process.")
        return 0

    # 2. Filter recipients due in the given window
    due_recipients = filter_due_reminders(
        recipients=valid_recipients,
        days_window=args.days,
        reference_date=ref_date,
        logger=logger,
    )

    if not due_recipients:
        print(f"\n[INFO] No reminders due within the next {args.days} day(s) from {ref_date}.")
        print_summary(
            total_valid=len(valid_recipients),
            total_due=0,
            sent_count=0,
            failed_count=0,
            dry_run=args.dry_run,
            log_file=args.log_file,
        )
        return 0

    # 3. Initialize Email Sender
    sender = EmailSender(logger=logger)

    # Validate credentials if running live
    if not args.dry_run:
        has_creds, cred_err = sender.validate_credentials()
        if not has_creds:
            logger.error(f"Credential Validation Failed: {cred_err}")
            print(f"\n[ERROR] {cred_err}")
            print("Tip: Run with '--dry-run' to preview emails without sending, or configure your .env file.\n")
            return 1

    # 4. Dispatch reminder emails
    sent_count = 0
    failed_count = 0

    print(f"\nProcessing {len(due_recipients)} reminder(s)...\n")

    for idx, recipient in enumerate(due_recipients, start=1):
        print(f"[{idx}/{len(due_recipients)}] Sending reminder to {recipient.name} <{recipient.email}> (Due: {recipient.due_date})...")
        success, _ = sender.send_single_email(recipient, dry_run=args.dry_run)
        if success:
            sent_count += 1
        else:
            failed_count += 1

    # 5. Print Execution Summary
    print_summary(
        total_valid=len(valid_recipients),
        total_due=len(due_recipients),
        sent_count=sent_count,
        failed_count=failed_count,
        dry_run=args.dry_run,
        log_file=args.log_file,
    )

    logger.info(
        f"Execution completed. Reminders Due: {len(due_recipients)}, Successful: {sent_count}, Failed: {failed_count}."
    )

    return 0 if failed_count == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
