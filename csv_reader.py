"""
csv_reader.py
=============
Module for loading, validating, and filtering recipient records from CSV files.
"""

import csv
import logging
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional, Tuple

# RFC 5322 compliant regex for basic email syntax validation
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)

REQUIRED_COLUMNS = {"name", "email", "due_date", "subject", "reminder_message"}


@dataclass
class Recipient:
    """Represents a reminder recipient record."""
    name: str
    email: str
    due_date: date
    subject: str
    reminder_message: str
    row_number: int = 0

    @property
    def formatted_due_date(self) -> str:
        """Returns due date in human-friendly format (e.g. 'September 20, 2026')."""
        return self.due_date.strftime("%B %d, %Y")


def validate_email(email_str: str) -> bool:
    """Checks whether the given string is a valid email address."""
    if not email_str or not isinstance(email_str, str):
        return False
    return bool(EMAIL_REGEX.match(email_str.strip()))


def parse_date(date_str: str) -> Optional[date]:
    """
    Parses a date string into a datetime.date object.
    Supports YYYY-MM-DD, YYYY/MM/DD, DD-MM-YYYY, and MM/DD/YYYY formats.
    """
    cleaned_date = date_str.strip()
    formats = ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(cleaned_date, fmt).date()
        except ValueError:
            continue
    return None


def load_recipients_from_csv(
    filepath: str,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Recipient], List[str]]:
    """
    Reads recipient data from a CSV file and validates required columns and fields.

    :param filepath: Path to the CSV file.
    :param logger: Optional logger for warnings and errors.
    :return: A tuple of (valid_recipients, error_messages).
    """
    log = logger or logging.getLogger(__name__)

    if not os.path.exists(filepath):
        err_msg = f"CSV file not found at: {filepath}"
        log.error(err_msg)
        return [], [err_msg]

    valid_recipients: List[Recipient] = []
    errors: List[str] = []

    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)

            if not reader.fieldnames:
                err_msg = f"CSV file '{filepath}' is empty or missing headers."
                log.error(err_msg)
                return [], [err_msg]

            # Normalize column names: lowercase and strip whitespace
            fieldnames_normalized = {name.strip().lower(): name for name in reader.fieldnames if name}
            missing_cols = REQUIRED_COLUMNS - set(fieldnames_normalized.keys())
            if missing_cols:
                err_msg = f"Missing required column(s) in CSV: {', '.join(sorted(missing_cols))}"
                log.error(err_msg)
                return [], [err_msg]

            for row_idx, row in enumerate(reader, start=2):  # Header is row 1
                # Retrieve field values by normalized column name
                raw_name = (row.get(fieldnames_normalized["name"]) or "").strip()
                raw_email = (row.get(fieldnames_normalized["email"]) or "").strip()
                raw_due_date = (row.get(fieldnames_normalized["due_date"]) or "").strip()
                raw_subject = (row.get(fieldnames_normalized["subject"]) or "").strip()
                raw_message = (row.get(fieldnames_normalized["reminder_message"]) or "").strip()

                # Skip completely empty rows
                if not any([raw_name, raw_email, raw_due_date, raw_subject, raw_message]):
                    continue

                row_errors = []
                if not raw_name:
                    row_errors.append("missing 'name'")

                if not validate_email(raw_email):
                    row_errors.append(f"invalid email '{raw_email}'")

                parsed_due_date = parse_date(raw_due_date) if raw_due_date else None
                if not parsed_due_date:
                    row_errors.append(f"invalid date format '{raw_due_date}' (expected YYYY-MM-DD)")

                if not raw_subject:
                    row_errors.append("missing 'subject'")

                if not raw_message:
                    row_errors.append("missing 'reminder_message'")

                if row_errors or parsed_due_date is None:
                    err = f"Row {row_idx}: Skipped due to {', '.join(row_errors)}"
                    log.warning(err)
                    errors.append(err)
                    continue

                valid_recipients.append(
                    Recipient(
                        name=raw_name,
                        email=raw_email,
                        due_date=parsed_due_date,
                        subject=raw_subject,
                        reminder_message=raw_message,
                        row_number=row_idx,
                    )
                )

    except Exception as e:
        err_msg = f"Unexpected error reading '{filepath}': {e}"
        log.error(err_msg)
        return [], [err_msg]

    log.info(f"Loaded {len(valid_recipients)} valid recipient record(s) from '{filepath}'.")
    return valid_recipients, errors


def filter_due_reminders(
    recipients: List[Recipient],
    days_window: int = 2,
    reference_date: Optional[date] = None,
    logger: Optional[logging.Logger] = None
) -> List[Recipient]:
    """
    Filters recipients whose due dates fall between today and (today + days_window).

    :param recipients: List of Recipient instances.
    :param days_window: Number of upcoming days to consider (default: 2).
    :param reference_date: Base date to compare against (defaults to today).
    :param logger: Optional logger for debug/info messages.
    :return: Filtered list of Recipient records due within the window.
    """
    log = logger or logging.getLogger(__name__)
    base_date = reference_date or date.today()

    due_recipients: List[Recipient] = []
    for r in recipients:
        delta_days = (r.due_date - base_date).days
        if 0 <= delta_days <= days_window:
            due_recipients.append(r)
            status_text = "today" if delta_days == 0 else f"in {delta_days} day(s)"
            log.debug(f"Recipient {r.name} ({r.email}) is due {status_text} on {r.due_date}.")

    log.info(
        f"Filtered {len(due_recipients)} of {len(recipients)} reminder(s) due within {days_window} day(s) (Reference date: {base_date})."
    )
    return due_recipients
