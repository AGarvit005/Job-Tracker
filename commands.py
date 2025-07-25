"""
Command Handler for Job Application Tracker
===========================================

This module handles all text commands including:
- Show applications by status
- Delete applications
- View statistics
- Manage reminders
- Help and utility commands

Author: Senior Python Developer
Version: 1.0
"""

import logging
from typing import Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CommandHandler:
    """Handles processing of text commands from WhatsApp messages"""
    
    def __init__(self, sheets_manager, scheduler_manager, twilio_bot):
        """
        Initialize command handler with required managers
        
        Args:
            sheets_manager: GoogleSheetsManager instance
            scheduler_manager: SchedulerManager instance
            twilio_bot: TwilioBot instance
        """
        self.sheets_manager = sheets_manager
        self.scheduler_manager = scheduler_manager
        self.twilio_bot = twilio_bot
        
        # Map command types to handler methods
        self.command_handlers = {
            'show_applied': self._handle_show_applied,
            'show_not_applied': self._handle_show_not_applied,
            'show_not_eligible': self._handle_show_not_eligible,
            'show_not_fixed': self._handle_show_not_fixed,
            'latest_status': self._handle_latest_status,
            'upcoming': self._handle_upcoming,
            'stats': self._handle_stats,
            'help': self._handle_help,
            'my_reminders': self._handle_my_reminders,
            'delete': self._handle_delete,
            'add': self._handle_add
        }
        
        logger.info("Command handler initialized")
    
    def handle_command(self, message: str, user_id: str) -> str:
        """
        Handle a command message
        
        Args:
            message: Command message from user
            user_id: User's identifier
            
        Returns:
            Response message for the user
        """
        try:
            # Import parser here to avoid circular imports
            from parser import MessageParser
            parser = MessageParser()
            
            # Parse the command
            command_data = parser.parse_command(message)
            
            if not command_data:
                return self._handle_unknown_command(message)
            
            command_type = command_data['command']
            
            # Get the appropriate handler
            handler = self.command_handlers.get(command_type)
            if not handler:
                return self._handle_unknown_command(message)
            
            # Execute the command
            logger.info(f"Executing command '{command_type}' for user {user_id}")
            return handler(command_data, user_id)
            
        except Exception as e:
            logger.error(f"Error handling command '{message}' for user {user_id}: {e}")
            return "❌ Sorry, something went wrong processing your command. Please try again."
    
    def _handle_show_applied(self, command_data: Dict[str, Any], user_id: str) -> str:
        """Handle 'Show Applied' command"""
        try:
            jobs = self.sheets_manager.get_jobs_by_status(user_id, 'Applied')
            return self.twilio_bot.format_job_list(jobs, "✅ Applied Jobs")
        except Exception as e:
            logger.error(f"Error showing applied jobs: {e}")
            return "❌ Error retrieving applied jobs. Please try again."
    
    def _handle_show_not_applied(self, command_data: Dict[str, Any], user_id: str) -> str:
        """Handle 'Show Not Applied' command"""
        try:
            jobs = self.sheets_manager.get_jobs_by_status(user_id, 'Not Applied')
            return self.twilio_bot.format_job_list(jobs, "⏳ Not Applied Jobs")
        except Exception as e:
            logger.error(f"Error showing not applied jobs: {e}")
            return "❌ Error retrieving not applied jobs. Please try again."
    
    def _handle_show_not_eligible(self, command_data: Dict[str, Any], user_id: str) -> str:
        """Handle 'Show Not Eligible' command"""
        try:
            jobs = self.sheets_manager.get_jobs_by_status(user_id, 'Not Eligible')
            return self.twilio_bot.format_job_list(jobs, "❌ Not Eligible Jobs")
        except Exception as e:
            logger.error(f"Error showing not eligible jobs: {e}")
            return "❌ Error retrieving not eligible jobs. Please try again."
    
    def _handle_show_not_fixed(self, command_data: Dict[str, Any], user_id: str) -> str:
        """Handle 'Show Not Fixed' command"""
        try:
            jobs = self.sheets_manager.get_jobs_by_status(user_id, 'Not Fixed')
            return self.twilio_bot.format_job_list(jobs, "🔄 Not Fixed Jobs")
        except Exception as e:
            logger.error(f"Error showing not fixed jobs: {e}")
            return "❌ Error retrieving not fixed jobs. Please try again."
    
    def _handle_latest_status(self, command_data: Dict[str, Any], user_id: str) -> str:
        """Handle 'Latest Status' command"""
        try:
            all_jobs = self.sheets_manager.get_all_jobs(user_id)
            
            if not all_jobs:
                return "📋 No job applications found. Add some jobs to get started!"
            
            # Sort by added date (most recent first)
            sorted_jobs = sorted(
                all_jobs, 
                key=lambda x: x.get('Added Date', ''), 
                reverse=True
            )
            
            # Get the last 5 entries
            recent_jobs = sorted_jobs[:5]
            
            return self.twilio_bot.format_job_list(recent_jobs, "🕒 Latest Job Updates")
            
        except Exception as e:
            logger.error(f"Error showing latest status: {e}")
            return "❌ Error retrieving latest status. Please try again."
    
    def _handle_upcoming(self, command_data: Dict[str, Any], user_id: str) -> str:
        """Handle 'Upcoming Applications' command"""
        try:
            upcoming_jobs = self.sheets_manager.get_upcoming_applications(user_id, 7)
            return self.twilio_bot.format_upcoming_applications(upcoming_jobs)
        except Exception as e:
            logger.error(f"Error showing upcoming applications: {e}")
            return "❌ Error retrieving upcoming applications. Please try again."
    
    def _handle_stats(self, command_data: Dict[str, Any], user_id: str) -> str:
        """Handle 'Stats' command"""
        try:
            stats = self.sheets_manager.get_user_stats(user_id)
            return self.twilio_bot.format_stats_message(stats)
        except Exception as e:
            logger.error(f"Error showing stats: {e}")
            return "❌ Error retrieving statistics. Please try again."
    
    def _handle_help(self, command_data: Dict[str, Any], user_id: str) -> str:
        """Handle 'Help' command"""
        return self.twilio_bot.format_help_message()
    
    def _handle_my_reminders(self, command_data: Dict[str, Any], user_id: str) -> str:
        """Handle 'My Reminders' command"""
        try:
            reminder_summary = self.scheduler_manager.get_reminder_summary(user_id)
            return self.twilio_bot.format_reminder_summary(reminder_summary)
        except Exception as e:
            logger.error(f"Error showing reminders: {e}")
            return "❌ Error retrieving reminders. Please try again."
    
    def _handle_delete(self, command_data: Dict[str, Any], user_id: str) -> str:
        """Handle 'Delete [Company]' command"""
        try:
            company = command_data.get('company')
            if not company:
                return "❌ Please specify a company name to delete.\nExample: Delete Google"
            
            # Delete from sheets
            result = self.sheets_manager.delete_job(user_id, company)
            
            if result['success']:
                # Cancel any reminders for this company
                self.scheduler_manager.cancel_reminders(user_id, company)
                return f"✅ {result['message']} and cancelled all reminders."
            else:
                return f"❌ {result['error']}"
                
        except Exception as e:
            logger.error(f"Error deleting job: {e}")
            return "❌ Error deleting job. Please try again."
    
    def _handle_add(self, command_data: Dict[str, Any], user_id: str) -> str:
        """Handle 'Add [Job Info]' command"""
        try:
            job_data = command_data.get('job_data')
            if not job_data:
                return ("❌ Invalid format for add command.\n"
                       "Example: Add Amazon (15 Aug) - Applied")
            
            # Add/update the job
            result = self.sheets_manager.add_or_update_job(user_id, job_data)
            
            if result['success']:
                # Schedule reminders if needed
                if job_data['status'].lower() == 'applied' and job_data.get('date'):
                    self.scheduler_manager.schedule_applied_reminder(
                        user_id, job_data['company'], job_data['date']
                    )
                elif job_data['status'].lower() == 'not applied':
                    self.scheduler_manager.schedule_daily_reminder(
                        user_id, job_data['company']
                    )
                
                response = f"✅ {result['message']}"
                if job_data.get('date'):
                    response += f" ({job_data['date']})"
                return response
            else:
                return f"❌ Failed to add job: {result['error']}"
                
        except Exception as e:
            logger.error(f"Error adding job: {e}")
            return "❌ Error adding job. Please try again."
    
    def _handle_unknown_command(self, message: str) -> str:
        """Handle unknown or invalid commands"""
        return (f"❓ I didn't understand that command.\n\n"
               f"Available commands:\n"
               f"• Show Applied/Not Applied/Not Eligible/Not Fixed\n"
               f"• Latest Status\n"
               f"• Upcoming Applications\n"
               f"• Stats\n"
               f"• My Reminders\n"
               f"• Delete [Company]\n"
               f"• Help\n\n"
               f"Or send job updates like:\n"
               f"• Amazon (15 Aug) - Applied")
    
    def get_all_commands(self) -> Dict[str, str]:
        """
        Get all available commands with descriptions
        
        Returns:
            Dictionary mapping command names to descriptions
        """
        return {
            'Show Applied': 'Display all jobs you have applied to',
            'Show Not Applied': 'Display jobs you haven\'t applied to yet',
            'Show Not Eligible': 'Display jobs you\'re not eligible for',
            'Show Not Fixed': 'Display jobs with undetermined status',
            'Latest Status': 'Show your most recent job updates',
            'Upcoming Applications': 'Show applications due in the next 7 days',
            'Stats': 'Display your job application statistics',
            'My Reminders': 'Show all your scheduled reminders',
            'Delete [Company]': 'Delete a specific company from your list',
            'Add [Job Info]': 'Add a new job (same format as regular updates)',
            'Help': 'Show this help message'
        }
    
    def search_jobs(self, user_id: str, search_term: str) -> str:
        """
        Search for jobs containing a specific term
        
        Args:
            user_id: User's identifier
            search_term: Term to search for
            
        Returns:
            Formatted search results
        """
        try:
            all_jobs = self.sheets_manager.get_all_jobs(user_id)
            
            if not all_jobs:
                return "📋 No jobs found to search through."
            
            # Search in company names (case-insensitive)
            search_lower = search_term.lower()
            matching_jobs = [
                job for job in all_jobs 
                if search_lower in job.get('Company Name', '').lower()
            ]
            
            if not matching_jobs:
                return f"🔍 No jobs found matching '{search_term}'"
            
            return self.twilio_bot.format_job_list(matching_jobs, f"🔍 Search Results for '{search_term}'")
            
        except Exception as e:
            logger.error(f"Error searching jobs: {e}")
            return "❌ Error searching jobs. Please try again."
    
    def get_jobs_by_date_range(self, user_id: str, days_back: int = 7) -> str:
        """
        Get jobs added within a specific date range
        
        Args:
            user_id: User's identifier
            days_back: Number of days to look back
            
        Returns:
            Formatted job list
        """
        try:
            all_jobs = self.sheets_manager.get_all_jobs(user_id)
            
            if not all_jobs:
                return "📋 No jobs found."
            
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=days_back)
            cutoff_str = cutoff_date.strftime('%Y-%m-%d')
            
            # Filter jobs by added date
            recent_jobs = []
            for job in all_jobs:
                added_date_str = job.get('Added Date', '')
                if added_date_str:
                    try:
                        # Parse added date (assuming YYYY-MM-DD HH:MM:SS format)
                        added_date = datetime.strptime(added_date_str[:10], '%Y-%m-%d')
                        if added_date >= cutoff_date:
                            recent_jobs.append(job)
                    except ValueError:
                        continue
            
            if not recent_jobs:
                return f"📋 No jobs added in the last {days_back} days."
            
            return self.twilio_bot.format_job_list(recent_jobs, f"📅 Jobs Added in Last {days_back} Days")
            
        except Exception as e:
            logger.error(f"Error getting jobs by date range: {e}")
            return "❌ Error retrieving jobs by date. Please try again."
    
    def update_reminder_time(self, user_id: str, new_hour: int, new_minute: int = 0) -> str:
        """
        Update the daily reminder time for a user
        
        Args:
            user_id: User's identifier
            new_hour: New hour (0-23)
            new_minute: New minute (0-59)
            
        Returns:
            Confirmation message
        """
        try:
            if not (0 <= new_hour <= 23) or not (0 <= new_minute <= 59):
                return "❌ Invalid time format. Hour should be 0-23, minute should be 0-59."
            
            # Reschedule all daily reminders
            self.scheduler_manager.reschedule_daily_reminders(user_id, new_hour, new_minute)
            
            time_str = f"{new_hour:02d}:{new_minute:02d}"
            return f"✅ Daily reminder time updated to {time_str}. All your daily reminders have been rescheduled."
            
        except Exception as e:
            logger.error(f"Error updating reminder time: {e}")
            return "❌ Error updating reminder time. Please try again."
    
    def get_command_usage_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get statistics about command usage (for analytics)
        
        Args:
            user_id: User's identifier
            
        Returns:
            Dictionary with usage statistics
        """
        # This would typically track command usage in a database
        # For now, return basic info about available commands
        return {
            'total_commands': len(self.command_handlers),
            'available_commands': list(self.command_handlers.keys()),
            'user_id': user_id,
            'last_updated': datetime.now().isoformat()
        }