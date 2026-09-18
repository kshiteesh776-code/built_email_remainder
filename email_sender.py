"""
email_sender.py
===============
SMTP email construction and dispatch module for the Bulk Email Reminder Tool.
Uses standard Python smtplib and email.message.EmailMessage.
"""

import logging
import os
import smtplib
import socket
from email.message import EmailMessage
from typing import Optional, Tuple
from csv_reader import Recipient


class EmailSender:
    """
    Manages SMTP connection, formatting, and dispatching of reminder emails.
    """

    def __init__(
        self,
        email_address: Optional[str] = None,
        email_password: Optional[str] = None,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        sender_name: str = "Reminder Bot",
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initializes the EmailSender with credentials and SMTP configuration.
        Falls back to environment variables if parameters are not provided.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.email_address = email_address or os.getenv("EMAIL_ADDRESS", "").strip()
        self.email_password = email_password or os.getenv("EMAIL_PASSWORD", "").strip()
        self.smtp_server = smtp_server or os.getenv("SMTP_SERVER", "smtp.gmail.com").strip()
        self.smtp_port = int(smtp_port or os.getenv("SMTP_PORT", "587"))
        self.sender_name = sender_name

    def validate_credentials(self) -> Tuple[bool, str]:
        """
        Validates whether the required credentials are present.
        """
        if not self.email_address:
            return False, "EMAIL_ADDRESS is missing. Please set it in your .env file."
        if not self.email_password:
            return False, "EMAIL_PASSWORD is missing. Please set it in your .env file."
        return True, ""

    def create_message(self, recipient: Recipient) -> EmailMessage:
        """
        Constructs a structured multipart (Plain text + HTML) EmailMessage.

        :param recipient: Recipient object with name, email, subject, due_date, reminder_message.
        :return: Prepared EmailMessage object.
        """
        msg = EmailMessage()
        msg["Subject"] = recipient.subject
        msg["From"] = f"{self.sender_name} <{self.email_address}>"
        msg["To"] = recipient.email

        # Plain-text body
        plain_body = (
            f"Hello {recipient.name},\n\n"
            f"This is a friendly reminder that your {recipient.subject.lower()} is due on {recipient.formatted_due_date}.\n\n"
            f"{recipient.reminder_message}\n\n"
            f"Please complete it before the due date.\n\n"
            f"Regards,\n"
            f"{self.sender_name}"
        )
        msg.set_content(plain_body)

        # HTML body for rich email clients
        html_body = f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #f8fafc;
      color: #1e293b;
      margin: 0;
      padding: 24px;
    }}
    .card {{
      background: #ffffff;
      max-width: 560px;
      margin: 0 auto;
      padding: 32px;
      border-radius: 12px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
      border: 1px solid #e2e8f0;
    }}
    .badge {{
      display: inline-block;
      background-color: #e0f2fe;
      color: #0369a1;
      padding: 4px 12px;
      border-radius: 9999px;
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 16px;
    }}
    h2 {{
      color: #0f172a;
      margin-top: 0;
      font-size: 20px;
    }}
    .message-box {{
      background-color: #f1f5f9;
      border-left: 4px solid #3b82f6;
      padding: 16px;
      margin: 20px 0;
      border-radius: 4px;
      font-size: 15px;
      line-height: 1.6;
    }}
    .due-info {{
      font-weight: 600;
      color: #b91c1c;
    }}
    .footer {{
      margin-top: 28px;
      padding-top: 16px;
      border-top: 1px solid #e2e8f0;
      color: #64748b;
      font-size: 14px;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">Reminder Notification</div>
    <h2>Hello {recipient.name},</h2>
    <p>This is a friendly reminder that your <strong>{recipient.subject}</strong> is due on <span class="due-info">{recipient.formatted_due_date}</span>.</p>
    <div class="message-box">
      {recipient.reminder_message}
    </div>
    <p>Please complete it before the due date.</p>
    <div class="footer">
      Regards,<br>
      <strong>{self.sender_name}</strong>
    </div>
  </div>
</body>
</html>
"""
        msg.add_alternative(html_body, subtype="html")
        return msg

    def send_single_email(self, recipient: Recipient, dry_run: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Sends an email to a single recipient over SMTP.

        :param recipient: Recipient to send the email to.
        :param dry_run: If True, simulates the email dispatch without network activity.
        :return: (is_success, error_message_or_none)
        """
        if dry_run:
            self.logger.info(
                f"[DRY RUN] Email would be sent to {recipient.email} | Subject: '{recipient.subject}' (Due: {recipient.due_date})"
            )
            return True, None

        is_valid, cred_error = self.validate_credentials()
        if not is_valid:
            err = f"Failed to send email to {recipient.email}: {cred_error}"
            self.logger.error(err)
            return False, cred_error

        msg = self.create_message(recipient)

        try:
            # Handle standard STARTTLS (typically Port 587) or SSL (Port 465)
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=15)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=15)
                server.ehlo()
                server.starttls()
                server.ehlo()

            with server:
                server.login(self.email_address, self.email_password)
                server.send_message(msg)

            self.logger.info(f"Email sent successfully to {recipient.email}")
            return True, None

        except smtplib.SMTPAuthenticationError as e:
            err = f"Failed to send email to {recipient.email}: Authentication Error (Check EMAIL_ADDRESS and EMAIL_PASSWORD)"
            self.logger.error(err)
            return False, f"Authentication Error: {e.smtp_error.decode() if isinstance(e.smtp_error, bytes) else str(e)}"

        except (smtplib.SMTPConnectError, ConnectionRefusedError, socket.gaierror) as e:
            err = f"Failed to send email to {recipient.email}: Connection Error (Could not reach {self.smtp_server}:{self.smtp_port})"
            self.logger.error(err)
            return False, f"Connection Error: {e}"

        except smtplib.SMTPServerDisconnected as e:
            err = f"Failed to send email to {recipient.email}: SMTPServerDisconnected ({e})"
            self.logger.error(err)
            return False, f"Server Disconnected: {e}"

        except smtplib.SMTPRecipientsRefused as e:
            err = f"Failed to send email to {recipient.email}: Recipient Refused by server"
            self.logger.error(err)
            return False, f"Recipient Refused: {e}"

        except (socket.timeout, TimeoutError) as e:
            err = f"Failed to send email to {recipient.email}: Network Timeout"
            self.logger.error(err)
            return False, f"Timeout: {e}"

        except Exception as e:
            err = f"Failed to send email to {recipient.email}: {type(e).__name__} - {e}"
            self.logger.error(err)
            return False, str(e)
