"""
Twilio WhatsApp Bot for Job Application Tracker
===============================================

This module handles all Twilio WhatsApp API interactions including:
- Sending messages to users
- Formatting messages for WhatsApp
- Managing Twilio client configuration

Author: Senior Python Developer
Version: 1.0
"""
import os
import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class TwilioBot:
    """Manages Twilio WhatsApp API interactions"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Twilio client
        
        Args:
            config: Configuration dictionary containing Twilio credentials
        """
        self.config = config
        self.account_sid = config['account_sid']
        self.auth_token = config['auth_token'] or os.environ.get('TWILIO_AUTH_TOKEN')
        self.from_number = config['from_number']  # Format: whatsapp:+14155238886
        
        # Initialize Twilio client
        try:
            self.client = Client(self.account_sid, self.auth_token)
            logger.info("Twilio client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            raise
    
    def send_message(self, to_number: str, message: str) -> Dict[str, Any]:
        """
        Send a WhatsApp message to a user
        
        Args:
            to_number: Recipient's phone number (without whatsapp: prefix)
            message: Message content to send
            
        Returns:
            Dictionary with success status and message info
        """
        try:
            # Format the recipient number for WhatsApp
            formatted_to = f"whatsapp:{to_number}" if not to_number.startswith('whatsapp:') else to_number
            
            # Send the message
            message_obj = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=formatted_to
            )
            
            logger.info(f"Message sent successfully to {formatted_to}. SID: {message_obj.sid}")
            
            return {
                'success': True,
                'message_sid': message_obj.sid,
                'status': message_obj.status,
                'to': formatted_to
            }
            
        except TwilioException as e:
            logger.error(f"Twilio error sending message to {to_number}: {e}")
            return {
                'success': False,
                'error': f"Twilio error: {str(e)}",
                'error_code': getattr(e, 'code', None)
            }
        except Exception as e:
            logger.error(f"Unexpected error sending message to {to_number}: {e}")
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}"
            }
    
    def send_bulk_message(self, recipients: List[str], message: str) -> Dict[str, Any]:
        """
        Send the same message to multiple recipients
        
        Args:
            recipients: List of phone numbers
            message: Message content to send
            
        Returns:
            Dictionary with results for each recipient
        """
        results = {
            'successful': [],
            'failed': [],
            'total_sent': 0,
            'total_failed': 0
        }
        
        for recipient in recipients:
            result = self.send_message(recipient, message)
            
            if result['success']:
                results['successful'].append({
                    'number': recipient,
                    'message_sid': result['message_sid']
                })
                results['total_sent'] += 1
            else:
                results['failed'].append({
                    'number': recipient,
                    'error': result['error']
                })
                results['total_failed'] += 1
        
        logger.info(f"Bulk message sent: {results['total_sent']} successful, {results['total_failed']} failed")
        return results
    
    def format_job_list(self, jobs: List[Dict[str, Any]], title: str = "Job Applications") -> str:
        """
        Format a list of jobs for WhatsApp display
        
        Args:
            jobs: List of job dictionaries
            title: Title for the list
            
        Returns:
            Formatted string suitable for WhatsApp
        """
        if not jobs:
            return f"📋 {title}\n\nNo jobs found."
        
        # WhatsApp has a character limit, so we'll limit the display
        max_jobs = 20
        
        formatted_message = f"📋 {title}\n{'=' * len(title)}\n\n"
        
        for i, job in enumerate(jobs[:max_jobs]):
            company = job.get('Company Name', 'Unknown')
            status = job.get('Status', 'Unknown')
            app_date = job.get('Application Date', '')
            
            # Use emoji for status
            status_emoji = self._get_status_emoji(status)
            
            job_line = f"{i+1}. {status_emoji} {company}"
            if app_date:
                job_line += f" ({app_date})"
            job_line += f" - {status}\n"
            
            formatted_message += job_line
        
        # Add truncation notice if needed
        if len(jobs) > max_jobs:
            formatted_message += f"\n... and {len(jobs) - max_jobs} more jobs.\n"
        
        formatted_message += f"\nTotal: {len(jobs)} jobs"
        
        return formatted_message
    
    def format_stats_message(self, stats: Dict[str, Any]) -> str:
        """
        Format user statistics for WhatsApp display
        
        Args:
            stats: Statistics dictionary from GoogleSheetsManager
            
        Returns:
            Formatted statistics message
        """
        message = "📊 Your Job Application Stats\n"
        message += "=" * 30 + "\n\n"
        
        message += f"📈 Total Applications: {stats['total_applications']}\n\n"
        
        # Status breakdown
        message += "📋 Status Breakdown:\n"
        message += f"✅ Applied: {stats['applied']}\n"
        message += f"⏳ Not Applied: {stats['not_applied']}\n"
        message += f"❌ Not Eligible: {stats['not_eligible']}\n"
        message += f"🔄 Not Fixed: {stats['not_fixed']}\n\n"
        
        # Recent activity
        if stats['recent_activity']:
            message += "🕒 Recent Activity:\n"
            for job in stats['recent_activity'][-3:]:  # Show last 3
                company = job.get('Company Name', 'Unknown')
                status = job.get('Status', 'Unknown')
                emoji = self._get_status_emoji(status)
                message += f"{emoji} {company} - {status}\n"
        
        return message
    
    def format_upcoming_applications(self, upcoming_jobs: List[Dict[str, Any]]) -> str:
        """
        Format upcoming applications for WhatsApp display
        
        Args:
            upcoming_jobs: List of upcoming job applications
            
        Returns:
            Formatted message
        """
        if not upcoming_jobs:
            return "📅 Upcoming Applications\n\nNo upcoming applications in the next 7 days."
        
        message = "📅 Upcoming Applications\n"
        message += "=" * 25 + "\n\n"
        
        for job in upcoming_jobs:
            company = job.get('Company Name', 'Unknown')
            app_date = job.get('Application Date', '')
            status = job.get('Status', 'Unknown')
            emoji = self._get_status_emoji(status)
            
            message += f"{emoji} {company}\n"
            if app_date:
                message += f"   📅 Due: {app_date}\n"
            message += f"   Status: {status}\n\n"
        
        return message
    
    def format_reminder_summary(self, summary: Dict[str, Any]) -> str:
        """
        Format reminder summary for WhatsApp display
        
        Args:
            summary: Reminder summary from SchedulerManager
            
        Returns:
            Formatted message
        """
        message = "⏰ Your Reminders\n"
        message += "=" * 18 + "\n\n"
        
        message += f"📊 Total Reminders: {summary['total_reminders']}\n"
        message += f"🔄 Daily Reminders: {summary['daily_reminders']}\n"
        message += f"📅 Application Reminders: {summary['applied_reminders']}\n\n"
        
        if summary['next_reminder']:
            try:
                from datetime import datetime
                next_time = datetime.fromisoformat(summary['next_reminder'].replace('Z', '+00:00'))
                message += f"⏰ Next Reminder: {next_time.strftime('%d %b %Y at %I:%M %p')}\n\n"
            except:
                message += f"⏰ Next Reminder: {summary['next_reminder']}\n\n"
        
        if summary['companies_with_reminders']:
            message += "🏢 Companies with Reminders:\n"
            for reminder in summary['companies_with_reminders'][:10]:  # Limit to 10
                company = reminder['company']
                reminder_type = reminder['type']
                type_emoji = "🔄" if reminder_type == "daily" else "📅"
                message += f"{type_emoji} {company} ({reminder_type})\n"
        
        return message
    
    def _get_status_emoji(self, status: str) -> str:
        """
        Get emoji for job status
        
        Args:
            status: Job status string
            
        Returns:
            Appropriate emoji
        """
        status_lower = status.lower()
        
        emoji_map = {
            'applied': '✅',
            'not applied': '⏳',
            'not eligible': '❌',
            'not fixed': '🔄'
        }
        
        return emoji_map.get(status_lower, '📝')
    
    def format_help_message(self) -> str:
        """
        Format help message with available commands
        
        Returns:
            Formatted help message
        """
        message = "🤖 WhatsApp Job Tracker Help\n"
        message += "=" * 30 + "\n\n"
        
        message += "📝 Add/Update Jobs:\n"
        message += "• Company Name (Date) - Status\n"
        message += "• Amazon (15 Aug) - Applied\n"
        message += "• Google - Not Applied\n\n"
        
        message += "📋 Commands:\n"
        message += "• Show Applied\n"
        message += "• Show Not Applied\n"
        message += "• Show Not Eligible\n"
        message += "• Show Not Fixed\n"
        message += "• Latest Status\n"
        message += "• Upcoming Applications\n"
        message += "• Delete [Company]\n"
        message += "• Stats\n"
        message += "• My Reminders\n"
        message += "• Help\n\n"
        
        message += "⏰ Statuses:\n"
        message += "• Applied ✅ - Applied to the job\n"
        message += "• Not Applied ⏳ - Haven't applied yet\n"
        message += "• Not Eligible ❌ - Not eligible for role\n"
        message += "• Not Fixed 🔄 - Status not determined\n\n"
        
        message += "Need help? Just send 'Help' anytime!"
        
        return message
    
    def format_error_message(self, error: str) -> str:
        """
        Format error messages for user-friendly display
        
        Args:
            error: Error message
            
        Returns:
            Formatted error message
        """
        return f"❌ Error: {error}\n\nTry sending 'Help' for available commands."
    
    def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """
        Get the status of a sent message
        
        Args:
            message_sid: Twilio message SID
            
        Returns:
            Dictionary with message status information
        """
        try:
            message = self.client.messages(message_sid).fetch()
            
            return {
                'success': True,
                'status': message.status,
                'error_code': message.error_code,
                'error_message': message.error_message,
                'date_sent': message.date_sent,
                'date_updated': message.date_updated
            }
            
        except TwilioException as e:
            logger.error(f"Error fetching message status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_phone_number(self, phone_number: str) -> bool:
        """
        Basic validation for phone number format
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            True if format appears valid
        """
        # Remove whatsapp: prefix if present
        number = phone_number.replace('whatsapp:', '')
        
        # Basic validation - should start with + and contain only digits and +
        if not number.startswith('+'):
            return False
        
        # Remove + and check if remaining characters are digits
        digits_only = number[1:]
        if not digits_only.isdigit():
            return False
        
        # Should be between 10-15 digits (international standard)
        if len(digits_only) < 10 or len(digits_only) > 15:
            return False
        
        return True
