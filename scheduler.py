"""
Scheduler Manager for Job Application Reminders - FIXED VERSION
===============================================

Fixed the user ID matching issue and added debug logging.

Author: Senior Python Developer
Version: 1.1 (Fixed)
"""

import logging
import json
import requests
from datetime import datetime, timedelta, time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from typing import Dict, Any, List
import pytz

logger = logging.getLogger(__name__)

class SchedulerManager:
    """Manages scheduled reminders for job applications using Google Sheets storage"""
    
    def __init__(self):
        """Initialize the scheduler with Google Sheets storage"""
        
        # Load configuration
        with open('config.json', 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # Configure APScheduler (only for the checker job)
        jobstores = {
            'default': MemoryJobStore()
        }
        
        executors = {
            'default': ThreadPoolExecutor(max_workers=20)
        }
        
        job_defaults = {
            'coalesce': False,
            'max_instances': 3,
            'misfire_grace_time': 30
        }
        
        # Initialize scheduler
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='Asia/Kolkata'
        )
        
        logger.info("Scheduler manager initialized with Google Sheets storage")
    
    def _get_reminders_worksheet(self):
        """Get or create the reminders worksheet"""
        try:
            from google_sheets import GoogleSheetsManager
            sheets_manager = GoogleSheetsManager(self.config['google_sheets'])
            
            try:
                worksheet = sheets_manager.spreadsheet.worksheet("Reminders")
            except:
                worksheet = sheets_manager.spreadsheet.add_worksheet(
                    title="Reminders", rows=1000, cols=8
                )
                worksheet.append_row([
                    'Reminder ID', 'User ID', 'Company', 'Reminder Type', 
                    'Trigger Time', 'Message', 'Status', 'Created Date'
                ])
            
            return worksheet
        except Exception as e:
            logger.error(f"Error getting reminders worksheet: {e}")
            return None
    
    def start(self):
        """Start the scheduler with periodic reminder checker"""
        try:
            self.scheduler.start()
            # Check for due reminders every minute
            self.scheduler.add_job(
                func=self._check_and_send_reminders,
                trigger=CronTrigger(minute='*'),  # Every minute
                id='reminder_checker'
            )
            logger.info("Scheduler started with reminder checker")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    def shutdown(self):
        """Shutdown the scheduler"""
        try:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler shutdown successfully")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}")
    
    def schedule_applied_reminder(self, user_id: str, company: str, application_date: str):
        """
        Store applied reminder in Google Sheets
        
        Args:
            user_id: User's identifier
            company: Company name
            application_date: Date when application is due
        """
        try:
            logger.info(f"Scheduling applied reminder for user {user_id}, company {company}, date {application_date}")
            
            # Parse the application date
            parsed_date = self._parse_date(application_date)
            if not parsed_date:
                logger.warning(f"Could not parse date: {application_date}")
                return
            
            # Set reminder time to 1:00 AM on the application date
            naive_reminder_time = datetime.combine(parsed_date.date(), time(1, 0))
            IST = pytz.timezone('Asia/Kolkata')
            reminder_time = IST.localize(naive_reminder_time)
            now = datetime.now(IST)
            
            # Only schedule if the date is in the future
            if reminder_time <= now:
                logger.info(f"Application date {application_date} is in the past, skipping reminder")
                return
            
            # Store in Google Sheets
            worksheet = self._get_reminders_worksheet()
            if worksheet:
                reminder_id = f"applied_reminder_{user_id}_{company}_{parsed_date.strftime('%Y%m%d')}"
                message = f"🚨 Reminder: Apply to {company} today! Don't forget to submit your application."
                
                # Remove existing reminder if any
                self._remove_reminder_from_sheet(reminder_id)
                
                # Add new reminder
                worksheet.append_row([
                    reminder_id,
                    user_id,
                    company,
                    'applied',
                    reminder_time.isoformat(),
                    message,
                    'pending',
                    datetime.now().isoformat()
                ])
                
                logger.info(f"Stored applied reminder for {company} in Google Sheets with user_id: {user_id}")
            
        except Exception as e:
            logger.error(f"Error scheduling applied reminder: {e}")
    
    def schedule_daily_reminder(self, user_id: str, company: str):
        """
        Store daily reminder in Google Sheets
        
        Args:
            user_id: User's identifier
            company: Company name
        """
        try:
            logger.info(f"Scheduling daily reminder for user {user_id}, company {company}")
            
            # Get reminder time from config
            reminder_config = self.config.get('reminders', {})
            reminder_hour = reminder_config.get('daily_reminder_hour', 9)
            reminder_minute = reminder_config.get('daily_reminder_minute', 0)
            
            # Store in Google Sheets
            worksheet = self._get_reminders_worksheet()
            if worksheet:
                reminder_id = f"daily_reminder_{user_id}_{company}"
                message = f"📝 Daily Reminder: You haven't applied to {company} yet. Consider applying today!"
                
                # Remove existing reminder if any
                self._remove_reminder_from_sheet(reminder_id)
                
                # For daily reminders, we store the time pattern instead of specific datetime
                trigger_time = f"daily_{reminder_hour:02d}:{reminder_minute:02d}"
                
                # Add new reminder
                worksheet.append_row([
                    reminder_id,
                    user_id,
                    company,
                    'daily',
                    trigger_time,
                    message,
                    'pending',
                    datetime.now().isoformat()
                ])
                
                logger.info(f"Stored daily reminder for {company} in Google Sheets with user_id: {user_id}")
            
        except Exception as e:
            logger.error(f"Error scheduling daily reminder: {e}")
    
    def cancel_reminders(self, user_id: str, company: str):
        """
        Cancel all reminders for a specific company
        
        Args:
            user_id: User's identifier
            company: Company name
        """
        try:
            worksheet = self._get_reminders_worksheet()
            if not worksheet:
                return
            
            # Get all reminders
            records = worksheet.get_all_records()
            rows_to_delete = []
            
            # Find rows to delete (collect row numbers first)
            for i, record in enumerate(records):
                if (record.get('User ID') == user_id and 
                    record.get('Company') == company and 
                    record.get('Status') == 'pending'):
                    rows_to_delete.append(i + 2)  # +2 because sheets are 1-indexed and we have headers
            
            # Delete rows in reverse order to avoid index shifting issues
            removed_count = 0
            for row_num in reversed(rows_to_delete):
                try:
                    worksheet.delete_rows(row_num)
                    removed_count += 1
                    logger.info(f"Deleted reminder row {row_num}")
                except Exception as e:
                    logger.error(f"Error deleting row {row_num}: {e}")
            
            logger.info(f"Cancelled {removed_count} reminders for {company}")
            
        except Exception as e:
            logger.error(f"Error cancelling reminders: {e}")
    
    def _remove_reminder_from_sheet(self, reminder_id: str):
        """Remove a specific reminder from the sheet"""
        try:
            worksheet = self._get_reminders_worksheet()
            if not worksheet:
                return
            
            records = worksheet.get_all_records()
            row_to_delete = None
            
            # Find the row to delete
            for i, record in enumerate(records):
                if record.get('Reminder ID') == reminder_id:
                    row_to_delete = i + 2  # +2 for 1-indexing and headers
                    break
            
            # Delete the row if found
            if row_to_delete:
                try:
                    worksheet.delete_rows(row_to_delete)
                    logger.info(f"Removed reminder {reminder_id} from row {row_to_delete}")
                except Exception as e:
                    logger.error(f"Error deleting reminder row {row_to_delete}: {e}")
                    
        except Exception as e:
            logger.error(f"Error removing reminder from sheet: {e}")
    
    def _check_and_send_reminders(self):
        """Check Google Sheets for due reminders and send them"""
        try:
            worksheet = self._get_reminders_worksheet()
            if not worksheet:
                return
            
            records = worksheet.get_all_records()
            now = datetime.now(pytz.timezone('Asia/Kolkata'))
            sent_count = 0
            rows_to_update = []
            
            for i, record in enumerate(records):
                if record.get('Status') != 'pending':
                    continue
                
                should_send = False
                row_num = i + 2  # +2 for 1-indexing and headers
                
                if record.get('Reminder Type') == 'applied':
                    # Check if it's time for applied reminder
                    try:
                        trigger_time = datetime.fromisoformat(record['Trigger Time'])
                        if now >= trigger_time:
                            should_send = True
                    except Exception as e:
                        logger.error(f"Error parsing applied reminder time: {e}")
                        continue
                        
                elif record.get('Reminder Type') == 'daily':
                    # Check if it's time for daily reminder
                    trigger_info = record.get('Trigger Time', '')
                    if trigger_info.startswith('daily_'):
                        try:
                            time_part = trigger_info.replace('daily_', '')
                            hour, minute = map(int, time_part.split(':'))
                            
                            # Check if current time matches the daily reminder time
                            if now.hour == hour and now.minute == minute:
                                should_send = True
                        except Exception as e:
                            logger.error(f"Error parsing daily reminder time: {e}")
                            continue
                
                if should_send:
                    # Send the reminder
                    result = self._send_reminder(record.get('User ID'), record.get('Message'))
                    if result:
                        sent_count += 1
                        
                        # For applied reminders, mark as sent (one-time)
                        if record.get('Reminder Type') == 'applied':
                            rows_to_update.append((row_num, 'sent'))
                        # For daily reminders, keep as pending for next day
                        # (they will be checked again tomorrow)
            
            # Update status for sent reminders
            for row_num, status in rows_to_update:
                try:
                    worksheet.update(f'G{row_num}', status)  # Status column
                except Exception as e:
                    logger.error(f"Error updating reminder status for row {row_num}: {e}")
            
            if sent_count > 0:
                logger.info(f"Sent {sent_count} reminders")
                
        except Exception as e:
            logger.error(f"Error checking and sending reminders: {e}")
    
    def _send_reminder(self, user_id: str, message: str) -> bool:
        """
        Send a reminder message via the Flask app's reminder endpoint
        
        Args:
            user_id: User's identifier
            message: Reminder message to send
            
        Returns:
            True if sent successfully
        """
        try:
            # Get the Flask app URL from config
            app_config = self.config.get('flask', {})
            base_url = app_config.get('base_url', 'https://job-tracker-1-9su6.onrender.com')
            
            # Send POST request to the reminder endpoint
            response = requests.post(
                f"{base_url}/send_reminder",
                json={
                    'user_id': user_id,
                    'message': message
                },
                timeout=10
            )
            
            if response.ok:
                logger.info(f"Reminder sent successfully to {user_id}")
                return True
            else:
                logger.error(f"Failed to send reminder: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending reminder: {e}")
            return False
    
    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse various date formats
        
        Args:
            date_str: Date string to parse
            
        Returns:
            datetime object or None if parsing fails
        """
        if not date_str:
            return None
        
        # Common date formats to try
        formats = [
            '%d %b',      # "15 Aug"
            '%d %B',      # "15 August"  
            '%Y-%m-%d',   # "2024-08-15"
            '%d/%m/%Y',   # "15/08/2024"
            '%d-%m-%Y',   # "15-08-2024"
        ]
        
        current_year = datetime.now().year
        
        for date_format in formats:
            try:
                parsed_date = datetime.strptime(date_str.strip(), date_format)
                
                # If no year specified, assume current year
                if parsed_date.year == 1900:
                    parsed_date = parsed_date.replace(year=current_year)
                
                return parsed_date
                
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def get_scheduled_jobs(self, user_id: str = None) -> list:
        """
        Get list of scheduled reminders from Google Sheets
        
        Args:
            user_id: Optional user ID to filter reminders
            
        Returns:
            List of reminder information dictionaries
        """
        try:
            worksheet = self._get_reminders_worksheet()
            if not worksheet:
                return []
            
            records = worksheet.get_all_records()
            reminders = []
            
            for record in records:
                # Skip non-pending reminders
                if record.get('Status') != 'pending':
                    continue
                    
                # Filter by user if specified
                if user_id and record.get('User ID') != user_id:
                    continue
                
                # Calculate next run time
                next_run = None
                if record.get('Reminder Type') == 'applied':
                    try:
                        next_run = record.get('Trigger Time')
                    except:
                        pass
                elif record.get('Reminder Type') == 'daily':
                    # For daily reminders, calculate next occurrence
                    try:
                        trigger_info = record.get('Trigger Time', '')
                        if trigger_info.startswith('daily_'):
                            time_part = trigger_info.replace('daily_', '')
                            hour, minute = map(int, time_part.split(':'))
                            
                            now = datetime.now(pytz.timezone('Asia/Kolkata'))
                            next_run_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                            
                            # If today's time has passed, schedule for tomorrow
                            if next_run_time <= now:
                                next_run_time += timedelta(days=1)
                                
                            next_run = next_run_time.isoformat()
                    except Exception as e:
                        logger.error(f"Error calculating next run for daily reminder: {e}")
                        pass
                
                reminder_info = {
                    'id': record.get('Reminder ID', ''),
                    'name': f"{record.get('Reminder Type', '').title()} Reminder - {record.get('Company', '')}",
                    'next_run': next_run,
                    'trigger': record.get('Trigger Time', '')
                }
                reminders.append(reminder_info)
            
            return reminders
            
        except Exception as e:
            logger.error(f"Error getting scheduled jobs: {e}")
            return []
    
    def get_reminder_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get a summary of all reminders for a user from Google Sheets
        
        Args:
            user_id: User's identifier
            
        Returns:
            Dictionary with reminder summary
        """
        try:
            logger.info(f"Getting reminder summary for user: {user_id}")
            
            worksheet = self._get_reminders_worksheet()
            if not worksheet:
                logger.warning("Could not get reminders worksheet")
                return self._empty_summary()
            
            records = worksheet.get_all_records()
            logger.info(f"Found {len(records)} total records in reminders sheet")
            
            user_reminders = []
            
            # Debug: Log all records to see what's in the sheet
            for i, record in enumerate(records):
                logger.info(f"Record {i}: User ID='{record.get('User ID')}', Company='{record.get('Company')}', Status='{record.get('Status')}'")
                
                # Normalize both user IDs for comparison (remove + sign and whitespace)
                sheet_user_id = str(record.get('User ID', '')).strip().lstrip('+')
                lookup_user_id = str(user_id).strip().lstrip('+')
                
                logger.info(f"Comparing: sheet_user_id='{sheet_user_id}' vs lookup_user_id='{lookup_user_id}'")
                
                # Filter reminders for this user that are pending
                if (sheet_user_id == lookup_user_id and 
                    str(record.get('Status', '')).strip().lower() == 'pending'):
                    user_reminders.append(record)
                    logger.info(f"Matched reminder for user {user_id}: {record.get('Company')} - {record.get('Reminder Type')}")
            
            logger.info(f"Found {len(user_reminders)} reminders for user {user_id}")
            
            summary = {
                'total_reminders': len(user_reminders),
                'daily_reminders': 0,
                'applied_reminders': 0,
                'next_reminder': None,
                'companies_with_reminders': []
            }
            
            next_run_times = []
            
            for reminder in user_reminders:
                reminder_type = reminder.get('Reminder Type', '')
                company = reminder.get('Company', 'Unknown')
                
                logger.info(f"Processing reminder: {company} - {reminder_type}")
                
                # Count by type
                if reminder_type == 'daily':
                    summary['daily_reminders'] += 1
                elif reminder_type == 'applied':
                    summary['applied_reminders'] += 1
                
                # Calculate next run time
                next_run = None
                if reminder_type == 'applied':
                    try:
                        next_run = reminder.get('Trigger Time')
                        if next_run:
                            next_run_times.append(datetime.fromisoformat(next_run))
                    except:
                        pass
                elif reminder_type == 'daily':
                    try:
                        trigger_info = reminder.get('Trigger Time', '')
                        if trigger_info.startswith('daily_'):
                            time_part = trigger_info.replace('daily_', '')
                            hour, minute = map(int, time_part.split(':'))
                            
                            now = datetime.now(pytz.timezone('Asia/Kolkata'))
                            next_run_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                            
                            if next_run_time <= now:
                                next_run_time += timedelta(days=1)
                            
                            next_run = next_run_time.isoformat()
                            next_run_times.append(next_run_time)
                    except Exception as e:
                        logger.error(f"Error calculating next run time: {e}")
                        pass
                
                # Add to companies list
                summary['companies_with_reminders'].append({
                    'company': company,
                    'type': reminder_type,
                    'next_run': next_run
                })
            
            # Find earliest next reminder
            if next_run_times:
                earliest = min(next_run_times)
                summary['next_reminder'] = earliest.isoformat()
            
            logger.info(f"Reminder summary for {user_id}: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error getting reminder summary: {e}")
            return self._empty_summary()
    
    def _empty_summary(self) -> Dict[str, Any]:
        """Return empty reminder summary"""
        return {
            'total_reminders': 0,
            'daily_reminders': 0,
            'applied_reminders': 0,
            'next_reminder': None,
            'companies_with_reminders': []
        }
    
    def reschedule_daily_reminders(self, user_id: str, new_hour: int, new_minute: int = 0):
        """
        Reschedule all daily reminders for a user to a new time
        
        Args:
            user_id: User's identifier
            new_hour: New hour (0-23)
            new_minute: New minute (0-59)
        """
        try:
            worksheet = self._get_reminders_worksheet()
            if not worksheet:
                return
            
            records = worksheet.get_all_records()
            rescheduled_count = 0
            
            for i, record in enumerate(records):
                if (record.get('User ID') == user_id and 
                    record.get('Reminder Type') == 'daily' and 
                    record.get('Status') == 'pending'):
                    
                    row_num = i + 2  # +2 for 1-indexing and headers
                    
                    # Update trigger time
                    new_trigger = f"daily_{new_hour:02d}:{new_minute:02d}"
                    try:
                        worksheet.update(f'E{row_num}', new_trigger)  # Trigger Time column
                        rescheduled_count += 1
                    except Exception as e:
                        logger.error(f"Error updating trigger time for row {row_num}: {e}")
            
            logger.info(f"Rescheduled {rescheduled_count} daily reminders for user {user_id} to {new_hour}:{new_minute:02d}")
            
        except Exception as e:
            logger.error(f"Error rescheduling daily reminders: {e}")
