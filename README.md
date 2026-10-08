# Tickect-Agent-Agentic-System-

A Flask-based web application for managing software Ticketss with intelligent query capabilities powered by Groq AI.

✨ Features

Intelligent Query Processing – Convert natural language into SQL queries using Groq AI

Ticketing Management – View and track software Tickets with expiration monitoring

User Authentication – Secure login system with role-based access control

Data Export – Export query results to Excel format

Schema Awareness – AI understands database schema and relationships

Real-time Statistics – Dashboard with Tickets insights and metrics

🛠 Technology Stack

Backend: Flask 2.3.3

Database: Microsoft SQL Server (via pyodbc)

ORM: SQLAlchemy 2.0.19

AI Integration: Groq API with LLaMA 3.3 70B model

Data Processing: Pandas 2.0.3

Authentication: Flask-Login 0.6.2

Frontend: HTML templates with Bootstrap

⚙️ Installation
Prerequisites

Python 3.8+

Microsoft SQL Server

Groq API account (for AI features)

Setup

Clone the repository

git clone <repository-url>
cd Tickets-management-system


Create a virtual environment

python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate


Install dependencies

pip install -r requirements.txt


Configure environment variables
Create a .env file in the root directory:

# Database Configuration
DB_DRIVER=ODBC Driver 17 for SQL Server
DB_SERVER=your-server-name
DB_NAME=your-database-name
DB_USER=your-username
DB_PASSWORD=your-password

# Groq API Configuration
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.3-70b-versatile

# Application Security
SECRET_KEY=your-secret-key-here
SESSION_SECRET=your-session-secret-here


🚀 Usage
Starting the Application
python run.py


The app will be available at: http://localhost:5000

Example Queries

The AI-powered system understands queries such as:

"Show all active Ticketss"

"Ticketss expiring in the next 30 days"

"Top 10 most expensive Ticketss"

"Ticketss by application type"

"Show Ticketss for customer XYZ"

# Output Directory
OUTPUT_DIR=storage/output

🗄 Database Schema

The system supports a comprehensive Tickets management database with key tables:

Tickets – Main Tickets table with activation details

invoice_activity – Invoice and activation records

Tickets_activity – Tickets history tracking

[user] – User accounts (brackets required for SQL)

product – Product catalog

tax_invoices – Tax invoice records

performa_invoices – Proforma invoice records


📡 API Endpoints

GET /Tickets/ – Main Tickets query interface

GET /Tickets/columns – Fetch available Tickets columns

GET /Tickets/schema – Retrieve complete database schema

GET /Tickets/examples – Query examples

GET /Tickets/stats – Tickets statistics

POST /Tickets/process-query – Process natural language queries

GET /Tickets/download – Download query results (Excel)

⚙️ Configuration Classes

DevelopmentConfig – Debug mode enabled

ProductionConfig – Optimized for production

TestingConfig – Testing configuration

📋 Logging

Daily log rotation (30-day retention)

Color-coded console output

Separate error logging

Detailed request tracing

🔐 Security Features

SQL injection protection with query validation

Role-based authentication with secure session handling

Environment-based configuration management

Secure password hashing and storage

🛡 Error Handling

Robust error handling for:

Database connection issues

Groq API failures

Invalid query generation

File I/O operations

📦 Deployment Considerations

Ensure proper database permissions

Configure reverse proxy (nginx/Apache)

Enable SSL certificates for HTTPS

Set correct file permissions for output directories

Monitor Groq API usage

🔧 Troubleshooting

Database Connection Errors

Verify connection string parameters

Confirm SQL Server accessibility

Check ODBC driver installation

Groq API Issues

Ensure API key starts with gsk_

Check internet connectivity

Monitor API usage limits

Query Generation Problems

Verify schema accessibility

Ensure table/column names match the database

🆘 Support

Database connectivity issues: Check SQL Server configuration

Query functionality issues: Verify Groq API key and model availability

Authentication issues: Review [user] table structure

📄 Tickets

This project is proprietary software.
All rights reserved.
