"""
Football Team Email Reminder System
Main script to check schedule and send reminders
"""

import csv
import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path
import configparser
import logging

class EmailReminderSystem:
    def __init__(self, config_path='config/config.ini'):
        self.config_path = config_path
        self.config = self._load_config()
        self.setup_logging()
        self.email_log = self._load_email_log()
        
    def _load_config(self):
        config = configparser.ConfigParser()
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        config.read(self.config_path)
        return config
    
    def setup_logging(self):
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/reminder_system.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _load_email_log(self):
        """Load log of previously sent emails to prevent duplicates"""
        log_file = Path('logs/sent_emails.json')
        if log_file.exists():
            with open(log_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_email_log(self):
        """Save email log to prevent duplicate sends"""
        log_file = Path('logs/sent_emails.json')
        log_file.parent.mkdir(exist_ok=True)
        with open(log_file, 'w') as f:
            json.dump(self.email_log, f, indent=2)
    
    def read_schedule(self):
        """Read schedule from CSV file ideal? discuss firther with client"""
        schedule_file = self.config['Files']['schedule_file']
        events = []
        
        try:
            with open(schedule_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    events.append({
                        'event_type': row['event_type'].strip(),
                        'date': row['date'].strip(),
                        'time': row['time'].strip(),
                        'location': row['location'].strip(),
                        'notes': row.get('notes', '').strip()
                    })
            self.logger.info(f"Loaded {len(events)} events from schedule")
            return events
        except FileNotFoundError:
            self.logger.error(f"Schedule file not found: {schedule_file}")
            return []
        except Exception as e:
            self.logger.error(f"Error reading schedule: {e}")
            return []
    
    def read_contacts(self):
        """Read parent contact information from CSV file"""
        contacts_file = self.config['Files']['contacts_file']
        contacts = []
        
        try:
            with open(contacts_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    contacts.append({
                        'parent_name': row['parent_name'].strip(),
                        'email': row['email'].strip()
                    })
            self.logger.info(f"Loaded {len(contacts)} contacts")
            return contacts
        except FileNotFoundError:
            self.logger.error(f"Contacts file not found: {contacts_file}")
            return []
        except Exception as e:
            self.logger.error(f"Error reading contacts: {e}")
            return []
    
    def get_events_needing_reminders(self, events):
        """Determine which events need reminders sent today"""
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        events_to_remind = []
        
        for event in events:
            try:
                event_date = datetime.strptime(event['date'], '%Y-%m-%d').date()
                
                # Practice: remind 1 day before
                if event['event_type'].lower() == 'practice' and event_date == tomorrow:
                    events_to_remind.append({
                        **event,
                        'reminder_type': 'practice_reminder',
                        'send_date': today
                    })
                
                # Game: remind same day
                elif event['event_type'].lower() == 'game' and event_date == today:
                    events_to_remind.append({
                        **event,
                        'reminder_type': 'game_reminder',
                        'send_date': today
                    })
                    
            except ValueError as e:
                self.logger.warning(f"Invalid date format in event: {event['date']}")
                continue
        
        self.logger.info(f"Found {len(events_to_remind)} events needing reminders")
        return events_to_remind
    
    def create_email_message(self, event, contact):
        """Create email message from template"""
        template_file = self.config['Files']['email_templates']
        
        try:
            with open(template_file, 'r') as f:
                templates = json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Template file not found: {template_file}")
            return None
        
        # Select appropriate template
        if event['reminder_type'] == 'practice_reminder':
            template = templates['practice_reminder']
        else:
            template = templates['game_reminder']
        
        # Format date for email
        event_date = datetime.strptime(event['date'], '%Y-%m-%d')
        formatted_date = event_date.strftime('%A, %B %d, %Y')
        
        # Replace placeholders
        subject = template['subject'].replace('[TIME]', event['time'])
        
        body = template['body']
        body = body.replace('[PARENT_NAME]', contact['parent_name'])
        body = body.replace('[DATE]', formatted_date)
        body = body.replace('[TIME]', event['time'])
        body = body.replace('[LOCATION]', event['location'])
        body = body.replace('[COACH_NAME]', self.config['Email']['coach_name'])
        
        # Add notes if present
        if event['notes']:
            body = body.replace('[NOTES]', f"\nAdditional Info: {event['notes']}")
        else:
            body = body.replace('[NOTES]', '')
        
        return subject, body
    
    def send_email(self, to_email, subject, body):
        """Send email via Google SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = f"{self.config['Email']['coach_name']} <{self.config['Email']['sender_email']}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to SMTP server
            server = smtplib.SMTP(
                self.config['Email']['smtp_server'],
                int(self.config['Email']['smtp_port'])
            )
            server.starttls()
            server.login(
                self.config['Email']['sender_email'],
                self.config['Email']['sender_password']
            )
            
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def has_been_sent(self, event, contact_email):
        """Check if reminder has already been sent for this event"""
        log_key = f"{event['date']}_{event['event_type']}_{contact_email}"
        return log_key in self.email_log
    
    def mark_as_sent(self, event, contact_email):
        """Mark reminder as sent"""
        log_key = f"{event['date']}_{event['event_type']}_{contact_email}"
        self.email_log[log_key] = {
            'sent_date': datetime.now().isoformat(),
            'event_date': event['date'],
            'event_type': event['event_type'],
            'recipient': contact_email
        }
    
    def run(self):
        """Main execution: check schedule and send reminders"""
        self.logger.info("=" * 60)
        self.logger.info("Starting Email Reminder System")
        self.logger.info("=" * 60)
        
        # Read data
        events = self.read_schedule()
        contacts = self.read_contacts()
        
        if not events:
            self.logger.warning("No events found in schedule")
            return
        
        if not contacts:
            self.logger.warning("No contacts found")
            return
        
        # Get events needing reminders
        events_to_remind = self.get_events_needing_reminders(events)
        
        if not events_to_remind:
            self.logger.info("No reminders to send today")
            return
        
        # Send reminders
        total_sent = 0
        total_skipped = 0
        
        for event in events_to_remind:
            self.logger.info(f"\nProcessing {event['event_type']} on {event['date']}")
            
            for contact in contacts:
                # Check if already sent
                if self.has_been_sent(event, contact['email']):
                    self.logger.info(f"  Skipping {contact['email']} - already sent")
                    total_skipped += 1
                    continue
                
                # Create and send email
                subject, body = self.create_email_message(event, contact)
                
                if self.send_email(contact['email'], subject, body):
                    self.mark_as_sent(event, contact['email'])
                    total_sent += 1
                    self.logger.info(f"  ✓ Sent to {contact['parent_name']} ({contact['email']})")
                else:
                    self.logger.error(f"  ✗ Failed to send to {contact['email']}")
        
    
        self._save_email_log()
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info(f"Summary: {total_sent} emails sent, {total_skipped} skipped")
        self.logger.info("=" * 60)

if __name__ == "__main__":
    try:
        system = EmailReminderSystem()
        system.run()
    except Exception as e:
        logging.error(f"Critical error: {e}", exc_info=True)