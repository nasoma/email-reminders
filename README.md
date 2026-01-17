# Email Reminders for Sports Teams

Automated email reminder system for practice and game schedules. This script parses schedule and contact information to send personalized reminders via Gmail SMTP.

## Features
- **Practice & Game Reminders**: Differing templates for event types.
- **CSV Data Sources**: Easy management of schedules and contacts.
- **Logging**: Keeps track of sent emails to prevent duplicates.
- **Configurable**: Simple `.ini` configuration.

## Setup

1. **Clone the repository**:
   ```bash
   git clone <your-repository-url>
   cd email-reminders-2
   ```

2. **Set up virtual environment**:
   ```bash
   uv venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

4. **Configure the application**:
   - Copy `config/config.ini.template` to `config/config.ini`.
   - Update `config/config.ini` with your Gmail credentials (use an App Password).

5. **Run the script**:
   ```bash
   python run_reminders.py
   ```

## Requirements
- Python 3.10+
- `uv` (recommended) or `pip`
- Gmail account with App Passwords enabled
