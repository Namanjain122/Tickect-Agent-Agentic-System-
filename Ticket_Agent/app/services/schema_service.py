from typing import Dict
from app.models.database import get_connection

def get_complete_schema() -> str:
    """
    Return complete schema with ALL raw tables and calculated report view.
    """
    return f"""
--- RAW DATABASE TABLES (for basic data) ---
{get_table_schema()}

--- TICKET SUMMARY TABLE (CSV-based with all derived columns) ---
ticket_summary: {', '.join(get_available_columns()["ticket_report_view"])}

This table contains pre-calculated columns like resolution time, assigned users, status, etc.
The data is stored in a CSV file and loaded into an in-memory SQLite database for querying.
Use this table for report queries instead of recalculating everything.

IMPORTANT: This is a CSV-based virtual table, not a physical database table.
Queries using this table will be executed against the in-memory SQLite database.
"""

def get_column_descriptions() -> Dict[str, str]:
    """Detailed descriptions of each calculated column"""
    return {
        "ticketNo": "Unique ticket identifier",
        "ticketType": "Type (Application, Device, Internal)",
        "issue": "Description of the issue",
        "CustomerName": "Name of the customer",
        "Product": "Product name",
        "createDate": "When ticket was created",
        "openDate": "When ticket was opened",
        "ResolvedDate": "When ticket was resolved",
        "closedDate": "When ticket was closed",
        "CreatedBy": "User who created the ticket",
        "OpenBy": "User who opened the ticket",
        "ResolvedBy": "User who resolved the ticket",
        "closedBy": "User who closed the ticket",
        "LastStatus": "Current status (Open, Resolved, Closed, Reopened)",
        "ResolutionMinutes": "Time to resolve in minutes",
        "ResolutionDays": "Time to resolve in days",
        "ReopenBy": "User who reopened the ticket",
        "jobNo": "Job card number",
        "jobCardVerifiedBy": "User who verified job card",
        "jobCardTestedBy": "User who tested job card",
        "InvoiceNo": "Invoice number",
        "ChallanNo": "Challan number",
        "PINumber": "PI number",
        "JobCardInitiateDate": "When job card was initiated",
        "jobCardApprovedBy": "User who approved job card",
        "JobCard_ClosedDate": "When job card was closed",
        "escalatedBy": "user who escalate ticket"
    }

def get_table_schema():
    """Get schema of raw database tables"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
        """)
        tables = [row[0] for row in cursor.fetchall()]

        schema_parts = []
        for table in tables:
            cursor.execute(f"""
                SELECT COLUMN_NAME, DATA_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = '{table}'
                ORDER BY ORDINAL_POSITION
            """)
            cols = [f"{col} ({dtype})" for col, dtype in cursor.fetchall()]
            schema_parts.append(f"{table}: {', '.join(cols)}")

        conn.close()
        return "\n".join(schema_parts)

    except Exception:
        return """ticket: id (int), ticketNo (varchar), ticketType (int), issue (varchar), timestamp (datetime)
user: id (int), userName (varchar), email (varchar)
product: id (int), name (varchar)
job_card: id (int), ticketId (int), jobNo (varchar), customerName (varchar)
ticket_activity: id (int), ticketId (int), ticketActivityTypeId (int), timestamp (datetime), userId (int)
invoice: id (int), ticketId (int), invoiceNo (varchar)
status: id (int), name (varchar)"""

def get_available_columns() -> Dict[str, list]:
    """Get available columns for both sources"""
    return {
        "ticket_report_view": [
            "ticketNo", "ticketType", "issue", "CustomerName", "Product",
            "createDate", "openDate", "ResolvedDate", "closedDate", 
            "CreatedBy", "OpenBy", "ResolvedBy", "closedBy", "LastStatus",
            "ResolutionMinutes", "ResolutionDays", "ReopenBy", "jobNo",
            "jobCardVerifiedBy", "jobCardTestedBy", "InvoiceNo", "ChallanNo",
            "PINumber", "JobCardInitiateDate", "jobCardApprovedBy", "JobCard_ClosedDate","escalatedBy"
        ],
        "raw_tables": {
            "ticket": ["id", "ticketNo", "ticketType", "issue", "timestamp"],
            "[user]": ["id", "userName", "email"],
            "product": ["id", "name"],
            "job_card": ["id", "ticketId", "jobNo", "customerName"],
            "ticket_activity": ["id", "ticketId", "ticketActivityTypeId", "timestamp", "userId"],
            "invoice": ["id", "ticketId", "invoiceNo"],
            "status": ["id", "name"]
        }
    }

def get_enhanced_schema():
    """Get enhanced schema including both raw tables and CSV-based summary"""
    raw_schema = get_table_schema()
    calculated_schema = f"""
--- TICKET SUMMARY (CSV-based virtual table) ---
ticket_summary: {', '.join(get_available_columns()["ticket_report_view"])}

This table is available for queries and can be joined with other tables.
Example: SELECT * FROM ticket_summary WHERE ResolutionDays > 2
"""
    return f"{raw_schema}\n\n{calculated_schema}"