\# 📱 WhatsApp Job Application Tracker



A powerful WhatsApp-based chatbot built with Flask and Twilio that helps you track job applications using simple natural language messages. Store data in Google Sheets and receive automated reminders.



\## 🚀 Features



\- \*\*Natural Language Processing\*\*: Send updates like "Amazon (15 Aug) - Applied"

\- \*\*Google Sheets Integration\*\*: All data stored in organized spreadsheets

\- \*\*Smart Reminders\*\*: Automated WhatsApp reminders for applications

\- \*\*Multiple Status Types\*\*: Applied, Not Applied, Not Eligible, Not Fixed

\- \*\*Rich Commands\*\*: Show stats, filter by status, view upcoming applications

\- \*\*Multi-User Support\*\*: Each user gets their own data sheet

\- \*\*Real-time Updates\*\*: Instant responses via WhatsApp



\## 📋 System Requirements



\- Python 3.8+

\- Twilio Account with WhatsApp Business API

\- Google Cloud Platform account (for Sheets API)

\- Docker (optional)



\## 🛠️ Quick Setup



\### 1. Clone and Install Dependencies



```bash

git clone <repository-url>

cd whatsapp-job-tracker

pip install -r requirements.txt

```



\### 2. Set Up Twilio WhatsApp



1\. \*\*Create Twilio Account\*\*: Visit \[twilio.com](https://www.twilio.com/)

2\. \*\*Enable WhatsApp Sandbox\*\*:

&nbsp;  - Go to Console → Messaging → Try it out → Send a WhatsApp message

&nbsp;  - Follow instructions to connect your WhatsApp number

&nbsp;  - Note down your Account SID, Auth Token, and WhatsApp number



3\. \*\*Configure Webhook\*\*:

&nbsp;  - Set webhook URL to: `https://your-domain.com/webhook`

&nbsp;  - For local development, use ngrok (see below)



\### 3. Set Up Google Sheets API



1\. \*\*Create Google Cloud Project\*\*:

&nbsp;  - Go to \[Google Cloud Console](https://console.cloud.google.com/)

&nbsp;  - Create a new project or select existing one



2\. \*\*Enable Google Sheets API\*\*:

&nbsp;  - Navigate to APIs \& Services → Library

&nbsp;  - Search for "Google Sheets API" and enable it



3\. \*\*Create Service Account\*\*:

&nbsp;  - Go to APIs \& Services → Credentials

&nbsp;  - Click "Create Credentials" → "

