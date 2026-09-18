"""
test_reminder.py
================
Comprehensive automated test suite for the Bulk Email Reminder Tool.
"""

import os
import smtplib
import tempfile
import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from csv_reader import (
    Recipient,
    filter_due_reminders,
    load_recipients_from_csv,
    parse_date,
    validate_email,
)
from email_sender import EmailSender
from logger_config import setup_logger


class TestCsvReader(unittest.TestCase):
    """Unit tests for csv_reader module."""

    def setUp(self):
        self.logger = setup_logger(log_file="test_log.log")

    def tearDown(self):
        for h in list(self.logger.handlers):
            h.close()
            self.logger.removeHandler(h)
        if os.path.exists("test_log.log"):
            try:
                os.remove("test_log.log")
            except OSError:
                pass

    def test_validate_email(self):
        self.assertTrue(validate_email("user@example.com"))
        self.assertTrue(validate_email("first.last+tag@sub.domain.co"))
        self.assertFalse(validate_email("invalid-email"))
        self.assertFalse(validate_email("@missinguser.com"))
        self.assertFalse(validate_email("user@missingtld"))
        self.assertFalse(validate_email(""))

    def test_parse_date(self):
        self.assertEqual(parse_date("2026-09-20"), date(2026, 9, 20))
        self.assertEqual(parse_date("2026/09/20"), date(2026, 9, 20))
        self.assertEqual(parse_date("20-09-2026"), date(2026, 9, 20))
        self.assertIsNone(parse_date("not-a-date"))

    def test_load_recipients_valid(self):
        csv_content = (
            "name,email,due_date,subject,reminder_message\n"
            "John Doe,john@example.com,2026-09-20,Electricity Bill,Pay bill.\n"
            "Alice Smith,alice@example.com,2026-09-21,Assignment,Submit assignment.\n"
        )
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv") as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name

        try:
            recipients, errors = load_recipients_from_csv(tmp_path, logger=self.logger)
            self.assertEqual(len(recipients), 2)
            self.assertEqual(len(errors), 0)
            self.assertEqual(recipients[0].name, "John Doe")
            self.assertEqual(recipients[0].email, "john@example.com")
            self.assertEqual(recipients[0].due_date, date(2026, 9, 20))
            self.assertEqual(recipients[0].subject, "Electricity Bill")
            self.assertEqual(recipients[0].reminder_message, "Pay bill.")
        finally:
            os.remove(tmp_path)

    def test_load_recipients_missing_file(self):
        recipients, errors = load_recipients_from_csv("non_existent_file.csv", logger=self.logger)
        self.assertEqual(len(recipients), 0)
        self.assertTrue(any("not found" in e.lower() for e in errors))

    def test_load_recipients_missing_columns(self):
        csv_content = "name,email\nJohn Doe,john@example.com\n"
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv") as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name

        try:
            recipients, errors = load_recipients_from_csv(tmp_path, logger=self.logger)
            self.assertEqual(len(recipients), 0)
            self.assertTrue(any("missing required column" in e.lower() for e in errors))
        finally:
            os.remove(tmp_path)

    def test_load_recipients_malformed_rows(self):
        csv_content = (
            "name,email,due_date,subject,reminder_message\n"
            "Valid User,valid@example.com,2026-09-20,Subject,Message\n"
            "Invalid Email,notanemail,2026-09-20,Subject,Message\n"
            "Invalid Date,user@example.com,bad-date,Subject,Message\n"
            ",missingname@example.com,2026-09-20,Subject,Message\n"
        )
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv") as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name

        try:
            recipients, errors = load_recipients_from_csv(tmp_path, logger=self.logger)
            self.assertEqual(len(recipients), 1)
            self.assertEqual(recipients[0].name, "Valid User")
            self.assertEqual(len(errors), 3)
        finally:
            os.remove(tmp_path)

    def test_filter_due_reminders(self):
        today = date(2026, 9, 18)
        recipients = [
            Recipient("Overdue", "o@ex.com", today - timedelta(days=1), "Sub", "Msg"),
            Recipient("Due Today", "t@ex.com", today, "Sub", "Msg"),
            Recipient("Due in 1 Day", "d1@ex.com", today + timedelta(days=1), "Sub", "Msg"),
            Recipient("Due in 2 Days", "d2@ex.com", today + timedelta(days=2), "Sub", "Msg"),
            Recipient("Due in 5 Days", "d5@ex.com", today + timedelta(days=5), "Sub", "Msg"),
        ]

        # Window = 2 days (today, +1 day, +2 days)
        due_2_days = filter_due_reminders(recipients, days_window=2, reference_date=today, logger=self.logger)
        self.assertEqual(len(due_2_days), 3)
        names = [r.name for r in due_2_days]
        self.assertIn("Due Today", names)
        self.assertIn("Due in 1 Day", names)
        self.assertIn("Due in 2 Days", names)
        self.assertNotIn("Overdue", names)
        self.assertNotIn("Due in 5 Days", names)

        # Window = 5 days
        due_5_days = filter_due_reminders(recipients, days_window=5, reference_date=today, logger=self.logger)
        self.assertEqual(len(due_5_days), 4)


class TestEmailSender(unittest.TestCase):
    """Unit tests for EmailSender module."""

    def setUp(self):
        self.logger = setup_logger(log_file="test_log.log")
        self.sender = EmailSender(
            email_address="sender@test.com",
            email_password="secretpassword",
            smtp_server="smtp.test.com",
            smtp_port=587,
            sender_name="Reminder Bot",
            logger=self.logger,
        )
        self.sample_recipient = Recipient(
            name="John Doe",
            email="john@example.com",
            due_date=date(2026, 9, 20),
            subject="Electricity Bill Due",
            reminder_message="Your electricity bill is due on Sept 20.",
        )

    def tearDown(self):
        for h in list(self.logger.handlers):
            h.close()
            self.logger.removeHandler(h)
        if os.path.exists("test_log.log"):
            try:
                os.remove("test_log.log")
            except OSError:
                pass

    def test_create_message(self):
        msg = self.sender.create_message(self.sample_recipient)
        self.assertEqual(msg["Subject"], "Electricity Bill Due")
        self.assertEqual(msg["To"], "john@example.com")
        self.assertIn("Reminder Bot", msg["From"])

        # Check plain text content
        body_part = msg.get_body(preferencelist=("plain",))
        self.assertIsNotNone(body_part)
        assert body_part is not None
        body = body_part.get_content()
        self.assertIn("Hello John Doe,", body)
        self.assertIn("September 20, 2026", body)
        self.assertIn("Your electricity bill is due on Sept 20.", body)

    def test_send_dry_run(self):
        success, err = self.sender.send_single_email(self.sample_recipient, dry_run=True)
        self.assertTrue(success)
        self.assertIsNone(err)

    def test_missing_credentials(self):
        bad_sender = EmailSender(email_address="", email_password="", logger=self.logger)
        success, err = bad_sender.send_single_email(self.sample_recipient, dry_run=False)
        self.assertFalse(success)
        self.assertIsNotNone(err)
        assert err is not None
        self.assertIn("EMAIL_ADDRESS is missing", err)

    @patch("email_sender.smtplib.SMTP")
    def test_send_live_success(self, mock_smtp_cls):
        mock_instance = MagicMock()
        mock_smtp_cls.return_value = mock_instance
        mock_instance.__enter__.return_value = mock_instance

        success, err = self.sender.send_single_email(self.sample_recipient, dry_run=False)
        self.assertTrue(success)
        self.assertIsNone(err)
        mock_instance.login.assert_called_once_with("sender@test.com", "secretpassword")
        mock_instance.send_message.assert_called_once()

    @patch("email_sender.smtplib.SMTP")
    def test_send_live_auth_error(self, mock_smtp_cls):
        mock_instance = MagicMock()
        mock_smtp_cls.return_value = mock_instance
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Invalid credentials")

        success, err = self.sender.send_single_email(self.sample_recipient, dry_run=False)
        self.assertFalse(success)
        self.assertIsNotNone(err)
        assert err is not None
        self.assertIn("Authentication Error", err)


if __name__ == "__main__":
    unittest.main()
