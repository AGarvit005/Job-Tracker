"""
Google Sheets Manager for Job Application Tracker
=================================================

This module handles all interactions with Google Sheets including:
- Reading and writing job application data
- Creating user-specific worksheets
- Updating existing entries
- Filtering and retrieving data by status

Author: Senior Python Developer
Version: 1.0
"""

import logging
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class GoogleSheetsManager:
    """Manages Google Sheets operations for job application tracking"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Google Sheets manager
        
        Args:
            config: Configuration dictionary containing credentials and sheet info
        """
        self.config = config
        self.spreadsheet_id = config['spreadsheet_id']
        self.credentials_file = config['credentials_file']
        
        # Define the scope for Google Sheets API
        self.scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Column headers for the job tracking sheet
        self.headers = ['Company Name', 'Status', 'Application Date', 'Added Date', 'Notes']
        
        # Initialize Google Sheets client
        self._init_client()
    
    def _init_client(self):
        """Initialize the Google Sheets client with service account credentials"""
        try:
            credentials = Credentials.from_service_account_file(
                self.credentials_file, 
                scopes=self.scope
            )
            self.client = gspread.authorize(credentials)
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            logger.info("Google Sheets client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            raise
    
    def _get_or_create_worksheet(self, user_id: str) -> gspread.Worksheet:
        """
        Get or create a worksheet for a specific user
        
        Args:
            user_id: User's phone number or identifier
            
        Returns:
            gspread.Worksheet: The user's worksheet
        """
        # Clean user_id to be a valid sheet name
        sheet_name = f"User_{user_id.replace('+', '').replace('-', '_')}"
        
        try:
            # Try to get existing worksheet
            worksheet = self.spreadsheet.worksheet(sheet_name)
            logger.info(f"Found existing worksheet: {sheet_name}")
        except gspread.WorksheetNotFound:
            # Create new worksheet
            worksheet = self.spreadsheet.add_worksheet(
                title=sheet_name, 
                rows=1000, 
                cols=10
            )
            # Add headers
            worksheet.append_row(self.headers)
            logger.info(f"Created new worksheet: {sheet_name}")
        
        return worksheet
    
    def add_or_update_job(self, user_id: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new job application or update existing one
        
        Args:
            user_id: User's identifier
            job_data: Dictionary containing company, status, date, etc.
            
        Returns:
            Dict with success status and message
        """
        try:
            worksheet = self._get_or_create_worksheet(user_id)
            
            company = job_data['company']
            status = job_data['status']
            app_date = job_data.get('date', '')
            notes = job_data.get('notes', '')
            
            # Check if company already exists
            existing_row = self._find_company_row(worksheet, company)
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if existing_row:
                # Update existing entry
                row_num = existing_row['row']
                worksheet.update(f'B{row_num}', status)  # Status
                worksheet.update(f'C{row_num}', app_date)  # Application Date
                worksheet.update(f'D{row_num}', current_time)  # Updated Date
                if notes:
                    worksheet.update(f'E{row_num}', notes)  # Notes
                
                logger.info(f"Updated {company} for user {user_id}")
                return {
                    'success': True, 
                    'message': f'Updated {company}',
                    'action': 'updated'
                }
            else:
                # Add new entry
                new_row = [company, status, app_date, current_time, notes]
                worksheet.append_row(new_row)
                
                logger.info(f"Added {company} for user {user_id}")
                return {
                    'success': True, 
                    'message': f'Added {company}',
                    'action': 'added'
                }
                
        except Exception as e:
            logger.error(f"Error adding/updating job for user {user_id}: {e}")
            return {
                'success': False, 
                'error': str(e)
            }
    
    def _find_company_row(self, worksheet: gspread.Worksheet, company: str) -> Optional[Dict[str, Any]]:
        """
        Find the row number for a specific company
        
        Args:
            worksheet: The worksheet to search
            company: Company name to find
            
        Returns:
            Dictionary with row info or None if not found
        """
        try:
            # Get all values in the first column (Company Name)
            companies = worksheet.col_values(1)
            
            # Search for the company (case-insensitive)
            for i, comp in enumerate(companies):
                if comp.lower() == company.lower():
                    # Return row number (1-indexed) and row data
                    row_data = worksheet.row_values(i + 1)
                    return {
                        'row': i + 1,
                        'data': row_data
                    }
            return None
            
        except Exception as e:
            logger.error(f"Error finding company row: {e}")
            return None
    
    def get_jobs_by_status(self, user_id: str, status: str) -> List[Dict[str, Any]]:
        """
        Get all jobs with a specific status
        
        Args:
            user_id: User's identifier
            status: Status to filter by
            
        Returns:
            List of job dictionaries
        """
        try:
            worksheet = self._get_or_create_worksheet(user_id)
            
            # Get all records
            records = worksheet.get_all_records()
            
            # Filter by status (case-insensitive)
            filtered_jobs = [
                job for job in records 
                if job['Status'].lower() == status.lower()
            ]
            
            logger.info(f"Found {len(filtered_jobs)} jobs with status '{status}' for user {user_id}")
            return filtered_jobs
            
        except Exception as e:
            logger.error(f"Error getting jobs by status for user {user_id}: {e}")
            return []
    
    def get_all_jobs(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all jobs for a user
        
        Args:
            user_id: User's identifier
            
        Returns:
            List of all job dictionaries
        """
        try:
            worksheet = self._get_or_create_worksheet(user_id)
            records = worksheet.get_all_records()
            
            logger.info(f"Retrieved {len(records)} jobs for user {user_id}")
            return records
            
        except Exception as e:
            logger.error(f"Error getting all jobs for user {user_id}: {e}")
            return []
    
    def delete_job(self, user_id: str, company: str) -> Dict[str, Any]:
        """
        Delete a job entry
        
        Args:
            user_id: User's identifier
            company: Company name to delete
            
        Returns:
            Dict with success status and message
        """
        try:
            worksheet = self._get_or_create_worksheet(user_id)
            
            # Find the company row
            existing_row = self._find_company_row(worksheet, company)
            
            if existing_row:
                # Delete the row
                worksheet.delete_rows(existing_row['row'])
                
                logger.info(f"Deleted {company} for user {user_id}")
                return {
                    'success': True,
                    'message': f'Deleted {company}'
                }
            else:
                return {
                    'success': False,
                    'error': f'Company {company} not found'
                }
                
        except Exception as e:
            logger.error(f"Error deleting job for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_upcoming_applications(self, user_id: str, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """
        Get applications with dates in the next N days
        
        Args:
            user_id: User's identifier
            days_ahead: Number of days to look ahead
            
        Returns:
            List of upcoming applications
        """
        try:
            worksheet = self._get_or_create_worksheet(user_id)
            records = worksheet.get_all_records()
            
            upcoming = []
            today = datetime.now()
            cutoff_date = today + timedelta(days=days_ahead)
            
            for job in records:
                app_date_str = job.get('Application Date', '').strip()
                if app_date_str:
                    try:
                        # Try different date formats
                        for date_format in ['%d %b', '%d %B', '%Y-%m-%d', '%d/%m/%Y']:
                            try:
                                app_date = datetime.strptime(app_date_str, date_format)
                                # If no year specified, assume current year
                                if app_date.year == 1900:
                                    app_date = app_date.replace(year=today.year)
                                
                                if today <= app_date <= cutoff_date:
                                    upcoming.append(job)
                                break
                            except ValueError:
                                continue
                    except Exception:
                        continue
            
            logger.info(f"Found {len(upcoming)} upcoming applications for user {user_id}")
            return upcoming
            
        except Exception as e:
            logger.error(f"Error getting upcoming applications for user {user_id}: {e}")
            return []
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get statistics for a user's job applications
        
        Args:
            user_id: User's identifier
            
        Returns:
            Dictionary with various statistics
        """
        try:
            worksheet = self._get_or_create_worksheet(user_id)
            records = worksheet.get_all_records()
            
            stats = {
                'total_applications': len(records),
                'applied': 0,
                'not_applied': 0,
                'not_eligible': 0,
                'not_fixed': 0,
                'recent_activity': []
            }
            
            # Count by status
            for job in records:
                status = job['Status'].lower()
                if status == 'applied':
                    stats['applied'] += 1
                elif status == 'not applied':
                    stats['not_applied'] += 1
                elif status == 'not eligible':
                    stats['not_eligible'] += 1
                elif status == 'not fixed':
                    stats['not_fixed'] += 1
            
            # Get recent activity (last 5 entries)
            stats['recent_activity'] = records[-5:] if len(records) > 5 else records
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats for user {user_id}: {e}")
            return {
                'total_applications': 0,
                'applied': 0,
                'not_applied': 0,
                'not_eligible': 0,
                'not_fixed': 0,
                'recent_activity': []
            }