"""
WhatsApp Job Application Tracker - Main Flask Application
=========================================================

This is the main Flask application that handles WhatsApp webhook requests
and coordinates between different modules for job application tracking.

Author: Senior Python Developer
Version: 1.0
"""

import os
import json
import logging
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime

# Import custom modules
from google_sheets import GoogleSheetsManager
from scheduler import SchedulerManager
from twillio_bot import TwilioBot
from parser import MessageParser
from commands import CommandHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('job_tracker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Load configuration
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Initialize managers
try:
    sheets_manager = GoogleSheetsManager(config['google_sheets'])
    scheduler_manager = SchedulerManager()
    twilio_bot = TwilioBot(config['twilio'])
    message_parser = MessageParser()
    command_handler = CommandHandler(sheets_manager, scheduler_manager, twilio_bot)
    
    logger.info("All managers initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize managers: {e}")
    raise

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0'
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Main webhook endpoint for receiving WhatsApp messages from Twilio
    
    This endpoint:
    1. Receives incoming messages from Twilio
    2. Parses the message content
    3. Executes appropriate commands or data operations
    4. Sends response back via WhatsApp
    """
    try:
        # Get message details from Twilio
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')
        to_number = request.values.get('To', '')
        
        logger.info(f"Received message from {from_number}: {incoming_msg}")
        
        # Create TwiML response
        resp = MessagingResponse()
        
        if not incoming_msg:
            resp.message("Hello! Send me job application updates like:\n"
                        "• Amazon (15 Aug) - Applied\n"
                        "• Google - Not Applied\n"
                        "Or commands like: Show Applied, Latest Status")
            return str(resp)
        
        # Extract user identifier (phone number without whatsapp: prefix)
        user_id = from_number.replace('whatsapp:', '')
        
        # Check if it's a command
        if message_parser.is_command(incoming_msg):
            response_text = command_handler.handle_command(incoming_msg, user_id)
        else:
            # Try to parse as job application update
            parsed_data = message_parser.parse_job_update(incoming_msg)
            
            if parsed_data:
                # Add/update job application
                result = sheets_manager.add_or_update_job(user_id, parsed_data)
                
                if result['success']:
                    # Schedule reminders if needed
                    if parsed_data['status'].lower() == 'applied' and parsed_data.get('date'):
                        scheduler_manager.schedule_applied_reminder(
                            user_id, parsed_data['company'], parsed_data['date']
                        )
                    elif parsed_data['status'].lower() == 'not applied':
                        scheduler_manager.schedule_daily_reminder(
                            user_id, parsed_data['company']
                        )
                    
                    response_text = f"✅ Updated {parsed_data['company']} - {parsed_data['status']}"
                    if parsed_data.get('date'):
                        response_text += f" ({parsed_data['date']})"
                else:
                    response_text = f"❌ Failed to update: {result['error']}"
            else:
                # Couldn't parse the message
                response_text = ("I couldn't understand that format. Try:\n"
                               "• Company Name (Date) - Status\n"
                               "• Amazon (15 Aug) - Applied\n"
                               "• Or use commands like 'Show Applied'")
        
        # Send response
        resp.message(response_text)
        logger.info(f"Sent response to {from_number}: {response_text}")
        
        return str(resp)
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        resp = MessagingResponse()
        resp.message("Sorry, something went wrong. Please try again later.")
        return str(resp)

@app.route('/send_reminder', methods=['POST'])
def send_reminder():
    """
    Endpoint for scheduler to send reminders
    Used by APScheduler to trigger reminder messages
    """
    try:
        data = request.json
        user_id = data.get('user_id')
        message = data.get('message')
        
        if user_id and message:
            result = twilio_bot.send_message(user_id, message)
            if result['success']:
                logger.info(f"Reminder sent to {user_id}: {message}")
                return jsonify({'status': 'success'})
            else:
                logger.error(f"Failed to send reminder: {result['error']}")
                return jsonify({'status': 'error', 'message': result['error']})
        else:
            return jsonify({'status': 'error', 'message': 'Missing user_id or message'})
            
    except Exception as e:
        logger.error(f"Error sending reminder: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get application statistics"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id parameter required'}), 400
            
        stats = sheets_manager.get_user_stats(user_id)
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Start the scheduler
    scheduler_manager.start()
    
    # Get configuration
    debug_mode = config.get('flask', {}).get('debug', False)
    port = int(os.environ.get('PORT', config.get('flask', {}).get('port', 5000)))
    host = config.get('flask', {}).get('host', '0.0.0.0')
    
    logger.info(f"Starting Flask app on {host}:{port}")
    
    try:
        app.run(host=host, port=port, debug=debug_mode)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        scheduler_manager.shutdown()
    except Exception as e:
        logger.error(f"Failed to start Flask app: {e}")
        scheduler_manager.shutdown()
        raise