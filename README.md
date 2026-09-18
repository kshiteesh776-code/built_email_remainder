# 📧 Bulk Email Reminder Tool

A Python command-line application that automates sending personalized reminder emails to multiple recipients using data from a CSV file. The tool parses due dates, filters recipients based on a configurable upcoming window, formats professional multi-part (Plain text + HTML) emails, logs operations to disk, and gracefully handles network or formatting errors.

---

## 🚀 Features

- **CSV-Driven Recipient Ingestion**: Parses recipient lists with automatic schema validation (`name`, `email`, `due_date`, `subject`, `reminder_message`).
- **Dynamic Due Date Filtering**: Configurable threshold (default: 2 days) to notify only recipients with tasks/bills due today or within the target window.
- **Personalized Email Templates**: Automatically generates customized, responsive HTML and plain-text email notifications with recipient greetings, custom subjects, and due dates.
- **Secure Credential Management**: Uses environment variables via `.env` to protect sensitive SMTP credentials (e.g. Gmail App Passwords) without hardcoding secrets.
- **Comprehensive Dual Logging**: Real-time console progress output coupled with persistent timestamped audit logs in `email_log.log`.
- **Fault-Tolerant Error Handling**: Validates email syntaxes, verifies CSV schemas, handles connection timeouts or authentication issues, and continues processing the rest of the batch if an individual email fails.
- **Dry-Run Preview Mode**: Simulate email batches using the `--dry-run` flag without making SMTP connections or sending real emails.
- **Automated Test Suite**: Unit tests covering CSV validation, date parsing, email formatting, and mock SMTP interactions.

---

## 📁 Project Structure

```
bulk_email_reminder/
├── reminder.py         # Main CLI application entry point
├── email_sender.py     # EmailMessage generation & SMTP communication
├── csv_reader.py       # CSV reading, validation, and due date filtering
├── logger_config.py    # Dual logger (file and console) configuration
├── recipients.csv      # Sample recipient dataset
├── .env.example        # Environment variable template
├── .env                # Local credentials file (git-ignored)
├── requirements.txt    # Project dependencies
├── test_reminder.py    # Automated test suite
├── email_log.log       # Output log file generated during runtime
└── README.md           # Project documentation
```

---

## 🛠️ Tech Stack & Prerequisites

- **Python**: 3.8+
- **Standard Libraries**: `smtplib`, `email.message`, `csv`, `logging`, `datetime`, `argparse`, `re`, `os`, `sys`
- **Third-Party Dependencies**:
  - `python-dotenv`: Secure environment variable management

---

## 📦 Installation

1. **Clone or navigate to the project directory**:
   ```bash
   cd "bulk_email_reminder"
   ```

2. **(Optional) Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## ⚙️ Configuration & Environment Setup

1. Copy the sample environment file to create `.env`:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` and fill in your SMTP credentials:
   ```env
   # Sender email address
   EMAIL_ADDRESS=your_email@gmail.com

   # SMTP password or App Password
   EMAIL_PASSWORD=your_app_password

   # SMTP Server details (Defaults to Gmail)
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   ```

> [!NOTE]
> **For Gmail users**: Standard account passwords will not work if 2-Step Verification is enabled. Generate an **App Password** by visiting [Google Account Security](https://myaccount.google.com/security) > **2-Step Verification** > **App passwords**.

---

## 📊 CSV Format (`recipients.csv`)

The CSV file must include headers matching the following column names:

| Column Name | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `name` | String | Recipient's full name | `John Doe` |
| `email` | String | Valid email address | `john@example.com` |
| `due_date` | Date (`YYYY-MM-DD`) | Target due date | `2026-09-20` |
| `subject` | String | Email subject line | `Electricity Bill Due` |
| `reminder_message`| String | Custom reminder message body | `Your electricity bill is due on Sept 20.` |

### Example `recipients.csv`:
```csv
name,email,due_date,subject,reminder_message
John Doe,john@example.com,2026-09-20,Electricity Bill Due,Your electricity bill is due on Sept 20.
Alice Smith,alice@example.com,2026-09-21,Assignment Reminder,Submit your DBMS assignment before Sept 21.
Bob Johnson,bob@example.com,2026-09-18,Server Maintenance Window,Scheduled maintenance is planned for tonight. Please save all work.
```

---

## 🚀 How to Run

### 1. Default Run (2-Day Reminder Window)
Checks for tasks due today or within the next 2 days:
```bash
python3 reminder.py
```

### 2. Custom Day Window (`--days`)
Checks for tasks due within the next 5 days:
```bash
python3 reminder.py --days 5
```

### 3. Dry-Run Mode (`--dry-run`)
Simulate and preview which emails would be dispatched without sending network requests:
```bash
python3 reminder.py --dry-run --days 5
```

### 4. Custom CSV File (`--csv`)
Specify an alternate recipient list file:
```bash
python3 reminder.py --csv /path/to/custom_recipients.csv --days 3
```

### 5. CLI Options Reference
```bash
python3 reminder.py --help
```
```text
options:
  -h, --help           show this help message and exit
  --days DAYS          Reminder window threshold in days (default: 2)
  --csv CSV            Path to the recipients CSV file (default: recipients.csv)
  --dry-run            Run without dispatching actual emails over SMTP (default: False)
  --log-file LOG_FILE  Path to the output log file (default: email_log.log)
  --ref-date REF_DATE  Custom reference date in YYYY-MM-DD format (default: None)
```

---

## 📋 Sample Output

### Console Output:
```text
=================================================================
          BULK EMAIL REMINDER TOOL           
=================================================================
 Reference Date : 2026-09-18
 Target Window  : Next 2 day(s)
 CSV Data Source: recipients.csv
 Execution Mode : LIVE (Sending Emails)
=================================================================
2026-09-18 21:07:37 - INFO - Starting Bulk Email Reminder Tool (Window: 2 days, CSV: 'recipients.csv', Mode: LIVE)
2026-09-18 21:07:37 - INFO - Loaded 5 valid recipient record(s) from 'recipients.csv'.
2026-09-18 21:07:37 - INFO - Filtered 2 of 5 reminder(s) due within 2 day(s) (Reference date: 2026-09-18).

Processing 2 reminder(s)...

[1/2] Sending reminder to John Doe <john@example.com> (Due: 2026-09-20)...
2026-09-18 21:07:38 - INFO - Email sent successfully to john@example.com
[2/2] Sending reminder to Bob Johnson <bob@example.com> (Due: 2026-09-18)...
2026-09-18 21:07:39 - INFO - Email sent successfully to bob@example.com

=================================================================
                 EXECUTION SUMMARY                   
=================================================================
 Total Valid Recipients in CSV : 5
 Total Reminders Due in Window : 2
 Successfully Sent             : 2
 Failed / Errored              : 0
 Detailed Logs Written To      : email_log.log
=================================================================

2026-09-18 21:07:39 - INFO - Execution completed. Reminders Due: 2, Successful: 2, Failed: 0.
```

### Log File Output (`email_log.log`):
```text
2026-09-18 21:07:37 - INFO - Starting Bulk Email Reminder Tool (Window: 2 days, CSV: 'recipients.csv', Mode: LIVE)
2026-09-18 21:07:37 - INFO - Loaded 5 valid recipient record(s) from 'recipients.csv'.
2026-09-18 21:07:37 - INFO - Filtered 2 of 5 reminder(s) due within 2 day(s) (Reference date: 2026-09-18).
2026-09-18 21:07:38 - INFO - Email sent successfully to john@example.com
2026-09-18 21:07:39 - INFO - Email sent successfully to bob@example.com
2026-09-18 21:07:39 - INFO - Execution completed. Reminders Due: 2, Successful: 2, Failed: 0.
```

---

## 🧪 Running Automated Tests

Run the full unit test suite with verbose output:

```bash
python3 -m unittest test_reminder.py -v
```

---

## 🛡️ Error Handling Details

1. **Missing or Corrupted CSV**: Emits an explicit log error and exits gracefully without unhandled tracebacks.
2. **Missing Columns**: Validates required header columns against schema.
3. **Invalid Email / Date Formats**: Skips malformed rows, logs warning details with row numbers, and continues processing valid rows.
4. **SMTP Authentication / Connection Failures**: Catches specific SMTP and socket errors, logs the root cause with the affected recipient email, and resumes sending remaining reminders.
