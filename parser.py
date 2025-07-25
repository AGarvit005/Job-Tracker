"""
Message Parser for Job Application Tracker
==========================================

This module handles parsing of WhatsApp messages to extract:
- Company names
- Job application status
- Application dates
- Commands

Uses regex patterns and natural language processing techniques.

Author: Senior Python Developer
Version: 1.0
"""

import re
import logging
from datetime import datetime
from typing import Dict, Optional, Any, List

logger = logging.getLogger(__name__)

class MessageParser:
    """Parses WhatsApp messages for job application data and commands"""
    
    def __init__(self):
        """Initialize the message parser with regex patterns"""
        
        # Valid job application statuses
        self.valid_statuses = [
            'applied', 'not applied', 'not eligible', 'not fixed'
        ]
        
        # Command patterns
        self.command_patterns = {
            'show_applied': r'^show\s+applied$',
            'show_not_applied': r'^show\s+not\s+applied$',
            'show_not_eligible': r'^show\s+not\s+eligible$',
            'show_not_fixed': r'^show\s+not\s+fixed$',
            'latest_status': r'^latest\s+status$',
            'upcoming': r'^upcoming\s+(applications?)?$',
            'stats': r'^stats?$',
            'help': r'^help$',
            'my_reminders': r'^(my\s+)?reminders?$',
            'delete': r'^delete\s+(.+)$',
            'add': r'^add\s+(.+)$'
        }
        
        # Job update patterns
        # Pattern: Company Name (optional date) - Status
        self.job_patterns = [
            # Company (Date) - Status
            r'^([^()]+?)\s*\(([^)]+)\)\s*-\s*(.+)$',
            # Company - Status (no date)
            r'^([^-]+?)\s*-\s*(.+)$'
        ]
        
        # Date patterns to recognize
        self.date_patterns = [
            r'\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',
            r'\d{1,2}\s+(january|february|march|april|may|june|july|august|september|october|november|december)',
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{1,2}/\d{1,2}/\d{4}',  # DD/MM/YYYY
            r'\d{1,2}-\d{1,2}-\d{4}'   # DD-MM-YYYY
        ]
        
        logger.info("Message parser initialized")
    
    def parse_job_update(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Parse a job application update message
        
        Args:
            message: Raw message from user
            
        Returns:
            Dictionary with parsed data or None if parsing fails
        """
        if not message or not message.strip():
            return None
        
        message = message.strip()
        logger.info(f"Parsing job update: {message}")
        
        # Try each job pattern
        for pattern in self.job_patterns:
            match = re.match(pattern, message, re.IGNORECASE)
            if match:
                if len(match.groups()) == 3:
                    # Pattern with date: Company (Date) - Status
                    company, date_str, status = match.groups()
                    return self._process_job_match(company, status, date_str)
                elif len(match.groups()) == 2:
                    # Pattern without date: Company - Status
                    company, status = match.groups()
                    return self._process_job_match(company, status)
        
        # If no pattern matches, try to extract basic info
        return self._fallback_parsing(message)
    
    def _process_job_match(self, company: str, status: str, date_str: str = None) -> Optional[Dict[str, Any]]:
        """
        Process matched job components
        
        Args:
            company: Company name
            status: Job status
            date_str: Optional date string
            
        Returns:
            Processed job data or None if invalid
        """
        # Clean and validate company name
        company = company.strip()
        if not company:
            return None
        
        # Clean and validate status
        status = status.strip()
        normalized_status = self._normalize_status(status)
        if not normalized_status:
            logger.warning(f"Invalid status: {status}")
            return None
        
        # Process date if provided
        parsed_date = None
        if date_str:
            parsed_date = self._parse_date_string(date_str.strip())
        
        result = {
            'company': company,
            'status': normalized_status,
            'original_status': status,
            'date': parsed_date,
            'raw_message': f"{company} - {status}"
        }
        
        if date_str:
            result['raw_message'] = f"{company} ({date_str}) - {status}"
        
        logger.info(f"Successfully parsed job update: {result}")
        return result
    
    def _normalize_status(self, status: str) -> Optional[str]:
        """
        Normalize status to one of the valid statuses
        
        Args:
            status: Raw status string
            
        Returns:
            Normalized status or None if invalid
        """
        status_lower = status.lower().strip()
        
        # Direct matches
        if status_lower in self.valid_statuses:
            return status_lower.title()  # Capitalize properly
        
        # Status aliases and variations
        status_aliases = {
            'applied': ['applied', 'submitted', 'sent', 'done'],
            'not applied': ['not applied', 'pending', 'todo', 'to do', 'not done', 'not submitted'],
            'not eligible': ['not eligible', 'ineligible', 'rejected', 'not qualified', 'no match'],
            'not fixed': ['not fixed', 'uncertain', 'maybe', 'considering', 'thinking', 'undecided']
        }
        
        # Check aliases
        for normalized, aliases in status_aliases.items():
            if status_lower in aliases:
                return normalized.title()
        
        # Fuzzy matching for common typos
        fuzzy_matches = {
            'applied': ['aplied', 'applyed', 'apllied'],
            'not applied': ['not aplied', 'not applyed', 'notapplied'],
            'not eligible': ['not eligable', 'noteligible', 'not elligible'],
            'not fixed': ['not fixd', 'notfixed', 'not fixxed']
        }
        
        for normalized, fuzzy_list in fuzzy_matches.items():
            if status_lower in fuzzy_list:
                return normalized.title()
        
        return None
    
    def _parse_date_string(self, date_str: str) -> Optional[str]:
        """
        Parse and validate date string
        
        Args:
            date_str: Raw date string
            
        Returns:
            Formatted date string or None if invalid
        """
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # Common date formats
        date_formats = [
            ('%d %b', '%d %b'),           # "15 Aug" -> "15 Aug"
            ('%d %B', '%d %b'),           # "15 August" -> "15 Aug"
            ('%Y-%m-%d', '%d %b'),        # "2024-08-15" -> "15 Aug"
            ('%d/%m/%Y', '%d %b'),        # "15/08/2024" -> "15 Aug"
            ('%d-%m-%Y', '%d %b')         # "15-08-2024" -> "15 Aug"
        ]
        
        current_year = datetime.now().year
        
        for input_format, output_format in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, input_format)
                
                # If no year specified, assume current year
                if parsed_date.year == 1900:
                    parsed_date = parsed_date.replace(year=current_year)
                
                # Format for output
                return parsed_date.strftime(output_format)
                
            except ValueError:
                continue
        
        # If no format matches, return the original string if it looks like a date
        if any(re.search(pattern, date_str, re.IGNORECASE) for pattern in self.date_patterns):
            return date_str
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _fallback_parsing(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Fallback parsing for messages that don't match standard patterns
        
        Args:
            message: Raw message
            
        Returns:
            Parsed data or None
        """
        # Look for status keywords in the message
        message_lower = message.lower()
        
        found_status = None
        for status in self.valid_statuses:
            if status in message_lower:
                found_status = status.title()
                break
        
        if not found_status:
            # Try aliases
            for status, aliases in {
                'Applied': ['applied', 'submitted', 'sent', 'done'],
                'Not Applied': ['not applied', 'pending', 'todo'],
                'Not Eligible': ['not eligible', 'rejected', 'ineligible'],
                'Not Fixed': ['not fixed', 'uncertain', 'maybe']
            }.items():
                if any(alias in message_lower for alias in aliases):
                    found_status = status
                    break
        
        if not found_status:
            return None
        
        # Extract company name (everything before the status)
        status_pos = message_lower.find(found_status.lower())
        if status_pos > 0:
            company_part = message[:status_pos].strip()
            
            # Remove common separators
            company_part = re.sub(r'\s*[-–—]\s*$', '', company_part)
            company_part = re.sub(r'\s*[()]\s*$', '', company_part)
            
            if company_part:
                return {
                    'company': company_part.strip(),
                    'status': found_status,
                    'original_status': found_status,
                    'date': None,
                    'raw_message': message
                }
        
        return None
    
    def is_command(self, message: str) -> bool:
        """
        Check if message is a command
        
        Args:
            message: Message to check
            
        Returns:
            True if message is a command
        """
        if not message:
            return False
        
        message_lower = message.lower().strip()
        
        # Check against all command patterns
        for command_type, pattern in self.command_patterns.items():
            if re.match(pattern, message_lower):
                return True
        
        return False
    
    def parse_command(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Parse a command message
        
        Args:
            message: Command message
            
        Returns:
            Dictionary with command type and parameters
        """
        if not message:
            return None
        
        message_lower = message.lower().strip()
        
        # Check each command pattern
        for command_type, pattern in self.command_patterns.items():
            match = re.match(pattern, message_lower)
            if match:
                result = {
                    'command': command_type,
                    'raw_message': message
                }
                
                # Extract parameters for commands that have them
                if command_type == 'delete' and match.groups():
                    result['company'] = match.group(1).strip()
                elif command_type == 'add' and match.groups():
                    # Parse the add command as a job update
                    add_content = match.group(1).strip()
                    job_data = self.parse_job_update(add_content)
                    if job_data:
                        result['job_data'] = job_data
                    else:
                        return None  # Invalid add command
                
                logger.info(f"Parsed command: {result}")
                return result
        
        return None
    
    def extract_company_names(self, text: str) -> List[str]:
        """
        Extract potential company names from text
        
        Args:
            text: Text to extract company names from
            
        Returns:
            List of potential company names
        """
        if not text:
            return []
        
        # Common company suffixes and prefixes to help identify companies
        company_indicators = [
            r'\b\w+\s+(inc|corp|ltd|llc|company|technologies|tech|systems|solutions|group|enterprises)\b',
            r'\b(google|amazon|microsoft|apple|facebook|meta|netflix|uber|airbnb|tesla|spacex)\b',
            r'\b\w+\s+(labs|studios|ventures|capital|partners|consulting|services)\b'
        ]
        
        potential_companies = []
        
        for pattern in company_indicators:
            matches = re.findall(pattern, text, re.IGNORECASE)
            potential_companies.extend(matches)
        
        # Remove duplicates and clean up
        unique_companies = list(set([company.strip() for company in potential_companies if company.strip()]))
        
        return unique_companies
    
    def validate_message_format(self, message: str) -> Dict[str, Any]:
        """
        Validate if a message follows expected formats
        
        Args:
            message: Message to validate
            
        Returns:
            Validation result with suggestions if invalid
        """
        if not message or not message.strip():
            return {
                'valid': False,
                'reason': 'Empty message',
                'suggestions': ['Try: Company Name - Status', 'Example: Amazon - Applied']
            }
        
        message = message.strip()
        
        # Check if it's a command
        if self.is_command(message):
            return {'valid': True, 'type': 'command'}
        
        # Check if it can be parsed as job update
        if self.parse_job_update(message):
            return {'valid': True, 'type': 'job_update'}
        
        # Provide specific feedback
        suggestions = []
        
        if '-' not in message:
            suggestions.append('Add a dash (-) between company name and status')
            suggestions.append('Example: Google - Applied')
        
        # Check for valid status
        has_valid_status = False
        message_lower = message.lower()
        for status in self.valid_statuses:
            if status in message_lower:
                has_valid_status = True
                break
        
        if not has_valid_status:
            suggestions.append('Use valid status: Applied, Not Applied, Not Eligible, Not Fixed')
        
        if '(' in message and ')' not in message:
            suggestions.append('Close parentheses for dates: Company (15 Aug) - Status')
        
        return {
            'valid': False,
            'reason': 'Invalid format',
            'suggestions': suggestions if suggestions else [
                'Try: Company Name - Status',
                'Or: Company (Date) - Status',
                'Example: Amazon (15 Aug) - Applied'
            ]
        }
    
    def get_format_examples(self) -> List[str]:
        """
        Get list of format examples for user guidance
        
        Returns:
            List of example formats
        """
        return [
            "Amazon (15 Aug) - Applied",
            "Google - Not Applied",
            "Microsoft (20 Sep) - Not Eligible",
            "Apple - Not Fixed",
            "Netflix - Applied",
            "Show Applied",
            "Latest Status",
            "Delete Google",
            "Stats"
        ]
    
    def extract_date_from_text(self, text: str) -> Optional[str]:
        """
        Extract date from any text string
        
        Args:
            text: Text containing potential date
            
        Returns:
            Extracted date string or None
        """
        if not text:
            return None
        
        # Look for date patterns in the text
        for pattern in self.date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Return the first match and try to parse it
                return self._parse_date_string(matches[0])
        
        return None
    
    def clean_company_name(self, company: str) -> str:
        """
        Clean and standardize company name
        
        Args:
            company: Raw company name
            
        Returns:
            Cleaned company name
        """
        if not company:
            return ""
        
        # Remove extra whitespace
        company = re.sub(r'\s+', ' ', company.strip())
        
        # Remove common suffixes for consistency (optional)
        # company = re.sub(r'\s+(inc|corp|ltd|llc)\.?, '', company, flags=re.IGNORECASE)
        
        # Capitalize properly
        # company = company.title()
        
        return company
    
    def get_status_variations(self) -> Dict[str, List[str]]:
        """
        Get all status variations for reference
        
        Returns:
            Dictionary mapping normalized status to variations
        """
        return {
            'Applied': ['applied', 'submitted', 'sent', 'done', 'complete'],
            'Not Applied': ['not applied', 'pending', 'todo', 'to do', 'not done', 'not submitted'],
            'Not Eligible': ['not eligible', 'ineligible', 'rejected', 'not qualified', 'no match'],
            'Not Fixed': ['not fixed', 'uncertain', 'maybe', 'considering', 'thinking', 'undecided']
        }