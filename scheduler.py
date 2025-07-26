"""
Scheduler Manager for Job Application Reminders
===============================================

This module handles all scheduled tasks including:
- Daily reminders for "Not Applied" jobs
- Application date reminders for "Applied" jobs
- Recurring reminder management

Uses APScheduler for task scheduling.

Author: Senior Python Developer
Version: 1.0
"""

import logging
import json
import requests
from datetime import datetime, timedelta, time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from typing import Dict, Any
import pytz

logger = logging.getLogger(__name__)

class SchedulerManager:
    """Manages scheduled reminders for job applications"""
    
    def __init__(self):
        """Initialize the scheduler with appropriate configuration"""
        
        # Load configuration
        with open('config.json', 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # Configure APScheduler
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
        
        logger.info("Scheduler manager initialized")
    
    def start(self):
        """Start the scheduler"""
        try:
            self.scheduler.start()
            logger.info("Scheduler started successfully")
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
        Schedule a reminder for an applied job on the application date at 1:00 AM
        
        Args:
            user_id: User's identifier
            company: Company name
            application_date: Date when application is due (format: "15 Aug" or "2024-08-15")
        """
        try:
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
            
            # Create job ID
            job_id = f"applied_reminder_{user_id}_{company}_{parsed_date.strftime('%Y%m%d')}"
            
            # Remove existing job if any
            self._remove_job(job_id)
            
            # Schedule the reminder
            self.scheduler.add_job(
                func=self._send_reminder,
                trigger=DateTrigger(run_date=reminder_time),
                args=[user_id, f"🚨 Reminder: Apply to {company} today! Don't forget to submit your application."],
                id=job_id,
                name=f"Applied Reminder - {company}",
                replace_existing=True
            )
            
            logger.info(f"Scheduled applied reminder for {company} on {reminder_time}")
            
        except Exception as e:
            logger.error(f"Error scheduling applied reminder: {e}")
    
    def schedule_daily_reminder(self, user_id: str, company: str):
        """
        Schedule daily reminders for "Not Applied" jobs
        
        Args:
            user_id: User's identifier
            company: Company name
        """
        try:
            # Get reminder time from config
            reminder_config = self.config.get('reminders', {})
            reminder_hour = reminder_config.get('daily_reminder_hour', 9)
            reminder_minute = reminder_config.get('daily_reminder_minute', 0)
            
            # Create job ID
            job_id = f"daily_reminder_{user_id}_{company}"
            
            # Remove existing job if any
            self._remove_job(job_id)
            
            # Schedule daily reminder
            self.scheduler.add_job(
                func=self._send_reminder,
                trigger=CronTrigger(hour=reminder_hour, minute=reminder_minute),
                args=[user_id, f"📝 Daily Reminder: You haven't applied to {company} yet. Consider applying today!"],
                id=job_id,
                name=f"Daily Reminder - {company}",
                replace_existing=True
            )
            
            logger.info(f"Scheduled daily reminder for {company} at {reminder_hour}:{reminder_minute:02d}")
            
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
            # Get all jobs
            jobs = self.scheduler.get_jobs()
            
            # Find and remove jobs for this user and company
            removed_count = 0
            for job in jobs:
                if (f"_{user_id}_{company}" in job.id or 
                    f"_{user_id}_{company}_" in job.id):
                    self.scheduler.remove_job(job.id)
                    removed_count += 1
            
            logger.info(f"Cancelled {removed_count} reminders for {company}")
            
        except Exception as e:
            logger.error(f"Error cancelling reminders: {e}")
    
    def _send_reminder(self, user_id: str, message: str):
        """
        Send a reminder message via the Flask app's reminder endpoint
        
        Args:
            user_id: User's identifier
            message: Reminder message to send
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
            else:
                logger.error(f"Failed to send reminder: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Error sending reminder: {e}")
    
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
    
    def _remove_job(self, job_id: str):
        """
        Remove a job if it exists
        
        Args:
            job_id: ID of the job to remove
        """
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.debug(f"Removed existing job: {job_id}")
        except Exception:
            # Job doesn't exist, which is fine
            pass
    
    def get_scheduled_jobs(self, user_id: str = None) -> list:
        """
        Get list of scheduled jobs, optionally filtered by user
        
        Args:
            user_id: Optional user ID to filter jobs
            
        Returns:
            List of job information dictionaries
        """
        try:
            jobs = self.scheduler.get_jobs()
            job_list = []
            
            for job in jobs:
                if user_id and f"_{user_id}_" not in job.id:
                    continue
                
                job_info = {
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run.isoformat() if job.next_run else None,
                    'trigger': str(job.trigger)
                }
                job_list.append(job_info)
            
            return job_list
            
        except Exception as e:
            logger.error(f"Error getting scheduled jobs: {e}")
            return []
    
    def reschedule_daily_reminders(self, user_id: str, new_hour: int, new_minute: int = 0):
        """
        Reschedule all daily reminders for a user to a new time
        
        Args:
            user_id: User's identifier
            new_hour: New hour (0-23)
            new_minute: New minute (0-59)
        """
        try:
            # Get all jobs for the user
            jobs = self.scheduler.get_jobs()
            rescheduled_count = 0
            
            for job in jobs:
                if f"daily_reminder_{user_id}_" in job.id:
                    # Extract company name from job ID
                    company = job.id.replace(f"daily_reminder_{user_id}_", "")
                    
                    # Reschedule with new time
                    self.scheduler.modify_job(
                        job.id,
                        trigger=CronTrigger(hour=new_hour, minute=new_minute)
                    )
                    rescheduled_count += 1
            
            logger.info(f"Rescheduled {rescheduled_count} daily reminders for user {user_id} to {new_hour}:{new_minute:02d}")
            
        except Exception as e:
            logger.error(f"Error rescheduling daily reminders: {e}")
    
    def get_reminder_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get a summary of all reminders for a user
        
        Args:
            user_id: User's identifier
            
        Returns:
            Dictionary with reminder summary
        """
        try:
            jobs = self.get_scheduled_jobs(user_id)
            
            summary = {
                'total_reminders': len(jobs),
                'daily_reminders': 0,
                'applied_reminders': 0,
                'next_reminder': None,
                'companies_with_reminders': []
            }
            
            next_run = None
            
            for job in jobs:
                if 'daily_reminder' in job['id']:
                    summary['daily_reminders'] += 1
                elif 'applied_reminder' in job['id']:
                    summary['applied_reminders'] += 1
                
                # Extract company name
                if 'daily_reminder' in job['id']:
                    company = job['id'].replace(f"daily_reminder_{user_id}_", "")
                elif 'applied_reminder' in job['id']:
                    parts = job['id'].split('_')
                    if len(parts) >= 4:
                        company = '_'.join(parts[3:-1])  # Get company name between user_id and date
                    else:
                        company = "Unknown"
                
                summary['companies_with_reminders'].append({
                    'company': company,
                    'type': 'daily' if 'daily_reminder' in job['id'] else 'applied',
                    'next_run': job['next_run']
                })
                
                # Track earliest next run time
                if job['next_run']:
                    job_next_run = datetime.fromisoformat(job['next_run'].replace('Z', '+00:00'))
                    if not next_run or job_next_run < next_run:
                        next_run = job_next_run
            
            if next_run:
                summary['next_reminder'] = next_run.isoformat()
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting reminder summary: {e}")
            return {
                'total_reminders': 0,
                'daily_reminders': 0,
                'applied_reminders': 0,
                'next_reminder': None,
                'companies_with_reminders': []
            }
