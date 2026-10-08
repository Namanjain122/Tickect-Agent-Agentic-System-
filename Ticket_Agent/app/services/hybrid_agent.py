import os
import requests
import re
import pandas as pd
import sqlite3
import threading
import logging
import colorlog
from datetime import datetime
from app.config import Config
from app.services.report_generator import complete_report_generator
from app.services.schema_service import get_available_columns
from app.utils.login_config import get_logger  # ✅ use your logging setup


logger = get_logger("hybrid_agent")


class HybridSQLGenerator:
    def __init__(self, api_key: str = Config.GROQ_API_KEY):
        logger.info("🚀 Initializing HybridSQLGenerator")
        self.api_key = api_key
        # Don't generate report immediately - wait for financial year selection
        self.ticket_summary_df = None
        self.csv_path = None
        
        # Store column mappings
        logger.info("📋 Loading available columns")
        self.available_columns = get_available_columns()
        self.calculated_columns = self.available_columns["ticket_report_view"]
        self.raw_table_columns = self.available_columns["raw_tables"]
        logger.info(f"✅ Loaded {len(self.calculated_columns)} calculated columns and {len(self.raw_table_columns)} raw tables")

        # Thread-local storage for SQLite connections
        self.local = threading.local()
        self.current_financial_year = None
        logger.info("✅ HybridSQLGenerator initialized successfully")

    def _get_thread_connection(self):
        """Get or create a thread-local SQLite connection"""
        try:
            logger.debug("🔗 Getting thread-local SQLite connection")
            if not hasattr(self.local, 'conn') or self.local.conn is None:
                logger.info("🆕 Creating new SQLite connection")
                self.local.conn = sqlite3.connect(':memory:', check_same_thread=False)
                # Enable foreign keys and better performance
                self.local.conn.execute("PRAGMA foreign_keys = ON")
                self.local.conn.execute("PRAGMA journal_mode = WAL")
                logger.info("✅ SQLite connection created and optimized")
            return self.local.conn
        except Exception as e:
            logger.error(f"❌ Error getting SQLite connection: {e}")
            # Create a new connection if there's an issue
            self.local.conn = sqlite3.connect(':memory:', check_same_thread=False)
            logger.info("🔄 Created fallback SQLite connection after error")
            return self.local.conn

    def _load_data_for_financial_year(self, financial_year: str = None):
        """Load data for the specified financial year"""
        logger.info(f"📂 Starting data load for financial year: {financial_year}")
        
        if financial_year is None:
            financial_year = complete_report_generator.current_financial_year
            logger.info(f"📅 Using default financial year: {financial_year}")
        
        # Only reload if financial year changed
        if financial_year != self.current_financial_year:
            logger.info(f"🔄 Financial year changed from {self.current_financial_year} to {financial_year}, loading new data")
            
            try:
                logger.info(f"📊 Loading ticket summary for financial year: {financial_year}")
                self.ticket_summary_df = complete_report_generator.get_ticket_summary(financial_year)
                self.csv_path = complete_report_generator.get_csv_path()
                self.current_financial_year = financial_year
                
                logger.info(f"✅ Successfully loaded {len(self.ticket_summary_df)} rows, {len(self.ticket_summary_df.columns)} columns")
                
                # Load CSV data into SQLite
                conn = self._get_thread_connection()
                logger.info("💾 Loading data into SQLite database")
                self.ticket_summary_df.to_sql('ticket_summary', conn, index=False, if_exists='replace')
                logger.info(f"✅ Data loaded into SQLite for financial year {financial_year}")
                
            except Exception as e:
                logger.error(f"❌ Failed to load data for financial year {financial_year}: {e}")
                raise e
        else:
            logger.info(f"✅ Financial year unchanged ({financial_year}), using cached data")

    def process_query(self, prompt: str, financial_year: str = None):
        """Main method to process queries - returns SQL for execution"""
        logger.info(f"🔍 Processing query: '{prompt}' for financial year: {financial_year}")
        
        # Load data for the specified financial year
        self._load_data_for_financial_year(financial_year)
        
        clean_prompt = self._clean_prompt(prompt)
        logger.debug(f"🧹 Cleaned prompt: '{clean_prompt}'")

        # Generate the schema description for Groq
        groq_prompt = f"""
You are a SQL query generator with access to multiple data sources:

SOURCE 1: RAW DATABASE TABLES (for basic data):
{self._format_raw_tables_schema()}

SOURCE 2: TICKET SUMMARY TABLE (pre-calculated report with derived columns):
Available columns: {', '.join(self.calculated_columns)}

The ticket_summary table contains data for financial year {financial_year or complete_report_generator.current_financial_year}.

User asked: "{clean_prompt}"

RULES:
1. If the query involves CALCULATED FIELDS (resolution time, resolved by, customer names) → Use ticket_summary table
2. If the query involves BASIC DATA (users, products) → Use raw database tables  
3. Return ONLY the SQL query, no explanations
4. Use proper SQL syntax
5. For ticket_summary queries, you don't need to filter by date as the data is already filtered by financial year

EXAMPLES:
- "show all users" → "SELECT * FROM [user]"
- "tickets with resolution time > 2 days" → "SELECT * FROM ticket_summary WHERE ResolutionDays > 2"
- "tickets resolved by ravi" → "SELECT * FROM ticket_summary WHERE ResolvedBy LIKE '%ravi%'"
- "list products" → "SELECT name FROM product"

Complex Queries Example
- "get tickets resolve by clouddev at 15 sep 2025" -> "SELECT * FROM ticket_summary WHERE ResolvedBy LIKE '%clouddev%' AND ResolvedDate > '2025-09-15'"
- "get tickets resolve by (user entry) at (given date)" ->"SELECT * FROM ticket_summary WHERE ResolvedBy LIKE '(user enrty)' and ResolvedDate>'2025-09-15'"


Return ONLY the SQL query for the most appropriate approach.
"""

        logger.debug("🤖 Calling Groq API to generate SQL query")
        response = self._call_groq_api(groq_prompt)
        logger.info(f"📝 Generated SQL query: {response}")
        
        # Execute the query and return results
        logger.info("⚡ Executing generated SQL query")
        df = self.execute_query(response, financial_year)
        logger.info(f"✅ Query execution completed, returned {len(df)} rows")
        
        return {
            "type": "sql", 
            "query": response,
            "dataframe": df
        }

    def execute_query(self, sql_query: str, financial_year: str = None):
        """
        Execute SQL query - determines whether to use database or in-memory SQLite
        Returns: DataFrame with results
        """
        logger.info(f"⚡ Executing query: {sql_query}")
        
        # Load data for the specified financial year
        self._load_data_for_financial_year(financial_year)
        
        sql_lower = sql_query.lower()
        
        # Check if this is a ticket_summary query (should use in-memory SQLite)
        if 'ticket_summary' in sql_lower:
            logger.info("📊 Query targets ticket_summary table, using SQLite")
            try:
                conn = self._get_thread_connection()
                
                # Check if the table exists and has data
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ticket_summary'")
                table_exists = cursor.fetchone()
                
                if not table_exists:
                    logger.warning("⚠️ ticket_summary table doesn't exist in SQLite, creating it")
                    self.ticket_summary_df.to_sql('ticket_summary', conn, index=False, if_exists='replace')
                    logger.info("✅ ticket_summary table created in SQLite")
                else:
                    # Check if table is empty
                    cursor.execute("SELECT COUNT(*) FROM ticket_summary")
                    count = cursor.fetchone()[0]
                    if count == 0:
                        logger.warning("⚠️ ticket_summary table is empty, repopulating")
                        self.ticket_summary_df.to_sql('ticket_summary', conn, index=False, if_exists='replace')
                        logger.info("✅ ticket_summary table repopulated")
                
                # Execute the query
                logger.info(f"🔍 Executing SQLite query: {sql_query}")
                result = pd.read_sql_query(sql_query, conn)
                logger.info(f"✅ SQLite query executed successfully, returned {len(result)} rows")
                return result
            except Exception as e:
                logger.error(f"❌ SQLite query failed: {e}")
                logger.info("🔄 Falling back to pandas execution")
                return self._fallback_to_pandas(sql_query)
        else:
            # This is a regular database query
            logger.info("🗄️ Query targets raw database tables, using direct database connection")
            try:
                from app.models.database import run_sql_query
                logger.info(f"🔍 Executing database query: {sql_query}")
                result = run_sql_query(sql_query)
                logger.info(f"✅ Database query executed successfully, returned {len(result)} rows")
                return result
            except Exception as e:
                logger.error(f"❌ Database query failed: {e}")
                return pd.DataFrame()

    def _fallback_to_pandas(self, sql_query: str):
        """Fallback method to execute SQL-like queries using pandas"""
        logger.info(f"🔄 Using pandas fallback for query: {sql_query}")
        
        if self.ticket_summary_df is None:
            logger.warning("⚠️ No data loaded, attempting to load default data")
            self._load_data_for_financial_year()
            if self.ticket_summary_df is None:
                logger.error("❌ Failed to load data for pandas fallback")
                return pd.DataFrame()
        
        try:
            sql_lower = sql_query.lower()
            
            # Handle simple SELECT * queries
            if sql_lower == "select * from ticket_summary":
                logger.info("📋 Returning all data (SELECT * query)")
                return self.ticket_summary_df
            
            # Handle WHERE clauses with LIKE
            if 'where' in sql_lower and 'like' in sql_lower:
                logger.info("🔍 Processing LIKE query with pandas")
                # Extract the condition
                where_part = sql_lower.split('where')[1].strip()
                where_part = where_part.split(';')[0].strip()
                
                # Parse the LIKE condition
                if ' like ' in where_part:
                    column, pattern = where_part.split(' like ')
                    column = column.strip()
                    pattern = pattern.strip().replace("'", "").replace("%", "")
                    
                    logger.info(f"🔍 Applying LIKE filter: {column} contains '{pattern}'")
                    
                    # Apply the filter
                    if column in self.ticket_summary_df.columns:
                        result = self.ticket_summary_df[
                            self.ticket_summary_df[column].astype(str).str.contains(pattern, case=False, na=False)
                        ]
                        logger.info(f"✅ LIKE filter applied, returned {len(result)} rows")
                        return result
            
            # Handle other WHERE conditions
            if 'where' in sql_lower:
                logger.info("🔍 Processing WHERE clause with pandas")
                # Try to convert SQL WHERE to pandas query
                where_condition = sql_lower.split('where')[1].strip()
                where_condition = where_condition.split(';')[0].strip()
                
                # Replace SQL operators with pandas compatible ones
                where_condition = where_condition.replace(' like ', '.str.contains(')
                where_condition = where_condition.replace('%', '')
                where_condition = where_condition.replace("'", '"')
                where_condition = where_condition.replace(' = ', ' == ')
                where_condition = where_condition.replace(' <> ', ' != ')
                
                # Add closing parenthesis for contains
                if '.str.contains(' in where_condition and ')' not in where_condition:
                    where_condition += ')'
                
                logger.info(f"🔄 Converted SQL WHERE to pandas condition: {where_condition}")
                
                try:
                    result = self.ticket_summary_df.query(where_condition, engine='python')
                    logger.info(f"✅ Pandas query executed, returned {len(result)} rows")
                    return result
                except Exception as e:
                    logger.error(f"❌ Pandas query failed: {e}")
                    # If query fails, return all data
                    logger.warning("⚠️ Returning all data due to query failure")
                    return self.ticket_summary_df
            
            # Default return all data
            logger.info("📋 No specific conditions, returning all data")
            return self.ticket_summary_df
            
        except Exception as e:
            logger.error(f"❌ Pandas fallback failed: {e}")
            # Return all data as final fallback
            logger.warning("⚠️ Returning all data as final fallback")
            return self.ticket_summary_df

    def test_query_execution(self, sql_query: str):
        """Test method to debug query execution"""
        logger.info(f"🧪 Testing query execution: {sql_query}")
        
        # Check if we have data
        if self.ticket_summary_df is None:
            logger.error("❌ No data loaded for test!")
            return pd.DataFrame()
        
        logger.info(f"📊 Data shape: {self.ticket_summary_df.shape}")
        logger.info(f"📋 Columns: {list(self.ticket_summary_df.columns)}")
        
        # Try SQLite execution
        try:
            conn = self._get_thread_connection()
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ticket_summary'")
            table_exists = cursor.fetchone()
            logger.info(f"📊 Table exists in SQLite: {table_exists}")
            
            if table_exists:
                # Check row count
                cursor.execute("SELECT COUNT(*) FROM ticket_summary")
                count = cursor.fetchone()[0]
                logger.info(f"🔢 Row count in SQLite: {count}")
                
                # Try to execute the query
                result = pd.read_sql_query(sql_query, conn)
                logger.info(f"✅ SQLite execution successful, returned {len(result)} rows")
                return result
                
        except Exception as e:
            logger.error(f"❌ SQLite test failed: {e}")
        
        # Try pandas fallback
        try:
            result = self._fallback_to_pandas(sql_query)
            logger.info(f"✅ Pandas fallback successful, returned {len(result)} rows")
            return result
        except Exception as e:
            logger.error(f"❌ Pandas fallback failed: {e}")
        
        logger.error("❌ All execution methods failed")
        return pd.DataFrame()

    def _format_raw_tables_schema(self) -> str:
        """Format raw table schema for Groq"""
        logger.debug("📋 Formatting raw tables schema for Groq")
        schema_lines = []
        for table, columns in self.raw_table_columns.items():
            schema_lines.append(f"{table}: {', '.join(columns)}")
        return "\n".join(schema_lines)

    def _call_groq_api(self, prompt: str) -> str:
        logger.info("📡 Calling Groq API to generate SQL query")
        
        if not self.api_key:
            logger.warning("⚠️ No Groq API key found, returning default query")
            return "SELECT * FROM ticket_summary"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        body = {
            "model": Config.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "You are a SQL query generator. Return only the SQL query, no explanations."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 500
        }

        try:
            logger.debug("📤 Sending request to Groq API")
            response = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                                   json=body, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()['choices'][0]['message']['content'].strip()
            
            # Clean up the response
            result = result.replace('```sql', '').replace('```', '').strip()
            
            # Safety check: if result is None or empty, return a default query
            if not result or result == "None":
                logger.warning("Groq API returned empty result, using default query")
                return "SELECT * FROM ticket_summary"
                
            logger.info("Groq API call successful")
            return result
        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            # Fallback to basic query
            logger.info("Using fallback query due to API failure")
            return "SELECT * FROM ticket_summary"

    def _clean_prompt(self, prompt: str) -> str:
        """Clean and normalize the prompt"""
        logger.debug(f"Cleaning prompt: '{prompt}'")
        prompt = prompt.lower().strip()
        prompt = re.sub(r'\s+', ' ', prompt)
        filler_words = ['please', 'can you', 'could you', 'i need', 'i want', 'show me', 'display', 'give me']
        for word in filler_words:
            prompt = prompt.replace(word, '')
        cleaned = prompt.strip()
        logger.debug(f"Cleaned prompt: '{cleaned}'")
        return cleaned

# Initialize
logger.info("Creating HybridSQLGenerator instance")
hybrid_generator = HybridSQLGenerator()

def process_prompt(prompt, financial_year=None):
    logger.info(f"process_prompt called with prompt: '{prompt}', financial_year: {financial_year}")
    try:
        result = hybrid_generator.process_query(prompt, financial_year)
        logger.info(f"process_prompt completed successfully, returned {len(result['dataframe'])} rows")
        return result
    except Exception as e:
        logger.error(f"process_prompt failed: {e}")
        raise e
# import os
# import requests
# import re
# import pandas as pd
# import sqlite3
# import threading
# from app.config import Config
# from app.services.report_generator import complete_report_generator
# from app.services.schema_service import get_available_columns

# class HybridSQLGenerator:
#     def __init__(self, api_key: str = Config.GROQ_API_KEY):
#         self.api_key = api_key
#         # Generate the ticket summary and save to CSV
#         self.ticket_summary_df = complete_report_generator.generate_complete_ticket_report()
#         self.csv_path = complete_report_generator.get_csv_path()
        
#         # Store column mappings
#         self.available_columns = get_available_columns()
#         self.calculated_columns = self.available_columns["ticket_report_view"]
#         self.raw_table_columns = self.available_columns["raw_tables"]

#         # Thread-local storage for SQLite connections
#         self.local = threading.local()

#     def _get_thread_connection(self):
#         """Get or create a thread-local SQLite connection"""
#         if not hasattr(self.local, 'conn'):
#             self.local.conn = sqlite3.connect(':memory:', check_same_thread=False)
#             # Load CSV data into SQLite
#             self.ticket_summary_df.to_sql('ticket_summary', self.local.conn, index=False, if_exists='replace')
#         return self.local.conn

#     def process_query(self, prompt: str):
#         """Main method to process queries - returns SQL for execution"""
#         clean_prompt = self._clean_prompt(prompt)

#         # Generate the schema description for Groq
#         groq_prompt = f"""
# You are a SQL query generator with access to multiple data sources:

# SOURCE 1: RAW DATABASE TABLES (for basic data):
# {self._format_raw_tables_schema()}

# SOURCE 2: TICKET SUMMARY TABLE (pre-calculated report with derived columns):
# Available columns: {', '.join(self.calculated_columns)}

# The ticket_summary table is available as a CSV-based virtual table.

# User asked: "{clean_prompt}"

# RULES:
# 1. If the query involves CALCULATED FIELDS (resolution time, resolved by, customer names) → Use ticket_summary table
# 2. If the query involves BASIC DATA (users, products) → Use raw database tables  
# 3. Return ONLY the SQL query, no explanations
# 4. Use proper SQL syntax

# EXAMPLES:
# - "show all users" → "SELECT * FROM [user]"
# - "tickets with resolution time > 2 days" → "SELECT * FROM ticket_summary WHERE ResolutionDays > 2"
# - "tickets resolved by ravi" → "SELECT * FROM ticket_summary WHERE ResolvedBy LIKE '%ravi%'"
# - "list products" → "SELECT name FROM product"

# Return ONLY the SQL query for the most appropriate approach.
# """

#         response = self._call_groq_api(groq_prompt)
        
#         # Execute the query and return results
#         df = self.execute_query(response)
        
#         return {
#             "type": "sql", 
#             "query": response,
#             "dataframe": df
#         }

#     def execute_query(self, sql_query: str):
#         """
#         Execute SQL query - determines whether to use database or in-memory SQLite
#         Returns: DataFrame with results
#         """
#         sql_lower = sql_query.lower()
        
#         # Check if this is a ticket_summary query (should use in-memory SQLite)
#         if 'ticket_summary' in sql_lower:
#             try:
#                 conn = self._get_thread_connection()
#                 result = pd.read_sql_query(sql_query, conn)
#                 return result
#             except Exception as e:
#                 return self._fallback_to_pandas(sql_query)
#         else:
#             # This is a regular database query
#             try:
#                 from app.models.database import run_sql_query
#                 result = run_sql_query(sql_query)
#                 return result
#             except Exception as e:
#                 return pd.DataFrame()

#     def _fallback_to_pandas(self, sql_query: str):
#         """Fallback method to execute SQL-like queries using pandas"""
#         try:
#             # Simple WHERE clause parsing for fallback
#             if 'where' in sql_query.lower():
#                 base_query = sql_query.lower()
#                 where_part = base_query.split('where')[1].strip()
                
#                 # Remove any trailing semicolons or other clauses
#                 where_part = where_part.split(';')[0].strip()
#                 where_part = where_part.split('order by')[0].strip()
#                 where_part = where_part.split('group by')[0].strip()
#                 where_part = where_part.split('limit')[0].strip()
                
#                 # Convert SQL operators to pandas syntax
#                 where_condition = where_part.replace(' like ', '.str.contains(')
#                 where_condition = where_condition.replace('%', '')
#                 where_condition = where_condition.replace("'", '"')
                
#                 # Handle different operators
#                 where_condition = where_condition.replace(' = ', ' == ')
#                 where_condition = where_condition.replace(' <> ', ' != ')
#                 where_condition = where_condition.replace(' > ', ' > ')
#                 where_condition = where_condition.replace(' < ', ' < ')
#                 where_condition = where_condition.replace(' >= ', ' >= ')
#                 where_condition = where_condition.replace(' <= ', ' <= ')
                
#                 # Use pandas query method
#                 result = self.ticket_summary_df.query(where_condition, engine='python')
#                 return result
#             elif 'select * from ticket_summary' in sql_query.lower():
#                 # Return all data if no WHERE clause
#                 return self.ticket_summary_df
#             else:
#                 # For other queries, try to use the full SQL with pandas
#                 return self.ticket_summary_df
#         except Exception as e:
#             # Return all data as final fallback
#             return self.ticket_summary_df

#     def _format_raw_tables_schema(self) -> str:
#         """Format raw table schema for Groq"""
#         schema_lines = []
#         for table, columns in self.raw_table_columns.items():
#             schema_lines.append(f"{table}: {', '.join(columns)}")
#         return "\n".join(schema_lines)

#     def _call_groq_api(self, prompt: str) -> str:
#         if not self.api_key:
#             return "SELECT * FROM ticket_summary"

#         headers = {
#             "Authorization": f"Bearer {self.api_key}",
#             "Content-Type": "application/json"
#         }

#         body = {
#             "model": Config.GROQ_MODEL,
#             "messages": [
#                 {"role": "system", "content": "You are a SQL query generator. Return only the SQL query, no explanations."},
#                 {"role": "user", "content": prompt}
#             ],
#             "temperature": 0.1,
#             "max_tokens": 500
#         }

#         try:
#             response = requests.post("https://api.groq.com/openai/v1/chat/completions", 
#                                    json=body, headers=headers, timeout=30)
#             response.raise_for_status()
#             result = response.json()['choices'][0]['message']['content'].strip()
            
#             # Clean up the response
#             result = result.replace('```sql', '').replace('```', '').strip()
            
#             # Safety check: if result is None or empty, return a default query
#             if not result or result == "None":
#                 return "SELECT * FROM ticket_summary"
                
#             return result
#         except Exception as e:
#             # Fallback to basic query
#             return "SELECT * FROM ticket_summary"

#     def _clean_prompt(self, prompt: str) -> str:
#         """Clean and normalize the prompt"""
#         prompt = prompt.lower().strip()
#         prompt = re.sub(r'\s+', ' ', prompt)
#         filler_words = ['please', 'can you', 'could you', 'i need', 'i want', 'show me', 'display', 'give me']
#         for word in filler_words:
#             prompt = prompt.replace(word, '')
#         return prompt.strip()

# # Initialize
# hybrid_generator = HybridSQLGenerator()

# def process_prompt(prompt):
#     return hybrid_generator.process_query(prompt)