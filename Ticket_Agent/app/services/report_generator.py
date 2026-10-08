import pandas as pd
from datetime import datetime
from app.models.database import get_engine
from app.config import Config
import os
from typing import Optional, List, Dict
from dateutil.relativedelta import relativedelta
import logging

logger = logging.getLogger(__name__)

class CompleteReportGenerator:
    def __init__(self):
        self.engine = get_engine()
        self.ticket_type_map = {1: "Application", 2: "Device", 3: "Internal"}
        self.status_map = {2: "Open", 7: "Reopened", 8: "Resolved", 3: "Closed"}
        self.ticket_summary_df = None
        self.csv_path = "ticket_summary_report.csv"
        self.current_financial_year = self.get_current_financial_year()

    def get_financial_years(self) -> List[Dict[str, str]]:
        """Get list of available financial years + 'All' option"""
        current_year = datetime.now().year
        financial_years = []

        # Add "All" option at the top
        financial_years.append({
            'value': "All",
            'label': "All",
            'start_date': None,
            'end_date': None
        })

        # Generate financial years from 2022 to current year + 1
        for year in range(2022, current_year + 2):
            financial_years.append({
                'value': f"{year}-{year+1}",
                'label': f"{year} - {year+1}",
                'start_date': f"{year}-04-01",
                'end_date': f"{year+1}-03-31"
            })
        
        return financial_years


    def get_current_financial_year(self) -> str:
        """Get current financial year in format 'YYYY-YYYY'"""
        now = datetime.now()
        current_year = now.year
        # Financial year starts April 1st
        if now.month >= 4:
            return f"{current_year}-{current_year+1}"
        else:
            return f"{current_year-1}-{current_year}"

    def get_financial_year_dates(self, financial_year: str) -> tuple:
        """Get start and end dates for a financial year or return None for 'All'"""
        if not financial_year:
            financial_year = self.current_financial_year

        if financial_year == "All":
            return None, None  # no filtering applied

        try:
            start_year = int(financial_year.split('-')[0])
        except ValueError:
            # fallback: treat invalid input like "All"
            return None, None

        start_date = f"{start_year}-04-01"
        end_date = f"{start_year + 1}-03-31"
        return start_date, end_date


    def load_raw_data(self, financial_year: Optional[str] = None):
        """Load raw tables from database for specific financial year or all years"""
        print(f"Loading data for financial year: {financial_year}")
        logger.info(f"Loading data for financial year: {financial_year}")


        # Load raw data
        ticket_df = pd.read_sql("SELECT * FROM ticket", self.engine)
        user_df = pd.read_sql("SELECT * FROM [user]", self.engine)
        product_df = pd.read_sql("SELECT * FROM product", self.engine)
        ticket_activity_df = pd.read_sql("SELECT * FROM ticket_activity", self.engine)
        job_card_df = pd.read_sql("SELECT * FROM job_card", self.engine)
        invoice_df = pd.read_sql("SELECT * FROM invoice", self.engine)
        status_df = pd.read_sql("SELECT * FROM status", self.engine)

        # Convert datetime columns
        for df in [ticket_df, ticket_activity_df]:
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')

        # If not "All", filter by financial year range
        if financial_year and financial_year != "All":
            start_date, end_date = self.get_financial_year_dates(financial_year)
            print(f"Date range: {start_date} to {end_date}")

            start_dt = pd.to_datetime(start_date).tz_localize('UTC')
            end_dt = pd.to_datetime(end_date + " 23:59:59").tz_localize('UTC')

            ticket_df = ticket_df[
                (ticket_df["timestamp"] >= start_dt) & 
                (ticket_df["timestamp"] <= end_dt)
            ]

            ticket_activity_df = ticket_activity_df[
                (ticket_activity_df["timestamp"] >= start_dt) & 
                (ticket_activity_df["timestamp"] <= end_dt)
            ]

        print(f"Loaded {len(ticket_df)} tickets, {len(ticket_activity_df)} activities for {financial_year}")
        return ticket_df, ticket_activity_df, user_df, job_card_df, invoice_df, status_df, product_df


    def generate_complete_ticket_report(self, financial_year: Optional[str] = None) -> pd.DataFrame:
        """
        Generate the complete enriched ticket report for specific financial year.
        """
        if financial_year is None:
            financial_year = self.current_financial_year
        
        print(f"Generating complete report for financial year: {financial_year}...")
        
         # === Handle "All" case ===
        if financial_year == "All":
            ticket_df, ticket_activity_df, user_df, job_card_df, invoice_df, status_df, product_df = self.load_raw_data(None)
            csv_filename = "ticket_summary_report_all.csv"
        else:
            ticket_df, ticket_activity_df, user_df, job_card_df, invoice_df, status_df, product_df = self.load_raw_data(financial_year)
            csv_filename = f"ticket_summary_report_{financial_year.replace('-', '_')}.csv"
        # Load raw data for specific financial year

        # [Keep all your existing calculation code unchanged from here...]
        # Base ticket summary
        ticket_summary_df = ticket_df[['ticketNo','ticketType','issue','industryId','siteId']].copy()
        ticket_summary_df['ticketType'] = ticket_summary_df['ticketType'].map(self.ticket_type_map)

        # Merge activities
        merged_df = pd.merge(
            ticket_df[['id', 'ticketNo']],
            ticket_activity_df,
            left_on='id',
            right_on='ticketId',
            how='inner'
        )

        
        # === Derived Columns ===
        open_dates_df = merged_df[merged_df['ticketActivityTypeId'] == 2] \
            .groupby('ticketNo')['timestamp'].min().reset_index().rename(columns={'timestamp': 'openDate'})
        
        closed_dates_df = merged_df[merged_df['ticketActivityTypeId'] == 3] \
            .groupby('ticketNo')['timestamp'].min().reset_index().rename(columns={'timestamp': 'closedDate'})

        resolved_dates_df = merged_df[merged_df['ticketActivityTypeId'] == 8] \
            .groupby('ticketNo')['timestamp'].min().reset_index().rename(columns={'timestamp': 'ResolvedDate'})

        create_dates_df = merged_df[merged_df['ticketActivityTypeId'] == 1] \
            .groupby('ticketNo')['timestamp'].min().reset_index().rename(columns={'timestamp': 'createDate'})

        # Created By
        create_df = merged_df[merged_df['ticketActivityTypeId'] == 1]
        created_by_df = create_df.sort_values('timestamp').groupby('ticketNo').first().reset_index()[['ticketNo', 'userId']]
        created_by_df = pd.merge(created_by_df, user_df[['id', 'userName']], left_on='userId', right_on='id', how='left')
        created_by_df = created_by_df[['ticketNo', 'userName']].rename(columns={'userName': 'CreatedBy'})

        # Open By
        open_by_df = merged_df[merged_df['ticketActivityTypeId'] == 2]
        open_by_user_df = open_by_df.sort_values('timestamp').groupby('ticketNo').first().reset_index()[['ticketNo', 'userId']]
        open_by_user_df = pd.merge(open_by_user_df, user_df[['id', 'userName']], left_on='userId', right_on='id', how='left')
        open_by_user_df = open_by_user_df[['ticketNo', 'userName']].rename(columns={'userName': 'OpenBy'})

        # Resolved By
        resolved_by_df = merged_df[merged_df['ticketActivityTypeId'] == 8]
        resolved_by_user_df = resolved_by_df.sort_values('timestamp').groupby('ticketNo').first().reset_index()[['ticketNo', 'userId']]
        resolved_by_user_df = pd.merge(resolved_by_user_df, user_df[['id', 'userName', 'email']], left_on='userId', right_on='id', how='left')
        resolved_by_user_df['ResolvedBy'] = resolved_by_user_df['email'].fillna(resolved_by_user_df['userName'])
        resolved_by_user_df = resolved_by_user_df[['ticketNo', 'ResolvedBy']]

        # Closed By
        closed_by_df = merged_df[merged_df['ticketActivityTypeId'] == 3]
        closed_by_user_df = closed_by_df.sort_values('timestamp').groupby('ticketNo').first().reset_index()[['ticketNo', 'userId']]
        closed_by_user_df = pd.merge(closed_by_user_df, user_df[['id', 'userName']], left_on='userId', right_on='id', how='left')
        closed_by_user_df = closed_by_user_df[['ticketNo', 'userName']].rename(columns={'userName': 'closedBy'})

        # Job Number
        jobno_df = pd.merge(ticket_df[['id', 'ticketNo']], job_card_df[['ticketId', 'jobNo']],
                           left_on='id', right_on='ticketId', how='left')[['ticketNo', 'jobNo']]

        # Job Card Initiate / Approved / Closed
        jobcard_initiate_date_df = merged_df[
            (merged_df['ticketActivityTypeId'] == 11) &
            (merged_df['narration'].str.strip().str.rstrip('.').str.lower() == 'job card initiated')
        ].groupby('ticketNo')['timestamp'].min().reset_index().rename(columns={'timestamp': 'JobCardInitiateDate'})

        jobcard_approved_df = merged_df[
            (merged_df['ticketActivityTypeId'] == 11) &
            (merged_df['narration'].str.strip().str.rstrip('.').str.lower() == 'job varification approved')
        ]
        approved_by_df = jobcard_approved_df.sort_values('timestamp').groupby('ticketNo').first().reset_index()[['ticketNo', 'userId']]
        approved_by_df = pd.merge(approved_by_df, user_df[['id', 'userName']], left_on='userId', right_on='id', how='left')
        approved_by_df = approved_by_df[['ticketNo', 'userName']].rename(columns={'userName': 'jobCardApprovedBy'})

        jobcard_closed_date_df = merged_df[
            (merged_df['ticketActivityTypeId'] == 11) &
            (merged_df['narration'].str.strip().str.rstrip('.').str.lower() == 'job card has been closed')
        ].groupby('ticketNo')['timestamp'].min().reset_index().rename(columns={'timestamp': 'JobCard_ClosedDate'})

        # Job Card Verified/Tested
        job_card_merge = pd.merge(ticket_df[['id', 'ticketNo']], job_card_df[['ticketId', 'verifiedBy', 'testedBy']],
                                 left_on='id', right_on='ticketId', how='left')
        verified_by_map = {3: 'shashank.gupta@m2mlogger.com', 4: 'ravi.kumar@m2mlogger.com'}
        tested_by_map = {3: 'shashank.gupta@m2mlogger.com', 4: 'ravi.kumar@m2mlogger.com'}
        job_card_merge['jobCardVerifiedBy'] = job_card_merge['verifiedBy'].map(verified_by_map).fillna('')
        job_card_merge['jobCardTestedBy'] = job_card_merge['testedBy'].map(tested_by_map).fillna('')
        job_card_info_df = job_card_merge[['ticketNo', 'jobCardVerifiedBy', 'jobCardTestedBy']]

        # Invoices
        invoice_no_df = invoice_df[invoice_df['invoiceNo'].str.startswith(('T', 'S'), na=False) & 
                                 ~invoice_df['invoiceNo'].str.startswith('CH', na=False)]
        invoice_no_df = invoice_no_df.groupby('ticketId')['invoiceNo'].first().reset_index().rename(columns={'invoiceNo': 'InvoiceNo'})

        challan_no_df = invoice_df[invoice_df['invoiceNo'].str.startswith('CH', na=False)]
        challan_no_df = challan_no_df.groupby('ticketId')['invoiceNo'].first().reset_index().rename(columns={'invoiceNo': 'ChallanNo'})

        pi_no_df = invoice_df[invoice_df['invoiceNo'].str.startswith('PI', na=False)]
        pi_no_df = pi_no_df.groupby('ticketId')['invoiceNo'].first().reset_index().rename(columns={'invoiceNo': 'PINumber'})

        invoice_data_df = ticket_df[['id', 'ticketNo']] \
            .merge(invoice_no_df, left_on='id', right_on='ticketId', how='left') \
            .merge(challan_no_df, left_on='id', right_on='ticketId', how='left') \
            .merge(pi_no_df, left_on='id', right_on='ticketId', how='left')
        invoice_data_df = invoice_data_df[['ticketNo', 'InvoiceNo', 'ChallanNo', 'PINumber']]

        # Last Status
        last_status_df = ticket_activity_df.sort_values("timestamp").groupby("ticketId").last().reset_index()
        last_status_df["LastStatus"] = last_status_df["ticketActivityTypeId"].map(self.status_map)
        last_status_df = last_status_df.merge(ticket_df[["id", "ticketNo"]], left_on="ticketId", right_on="id", how="left")
        last_status_df = last_status_df[["ticketNo", "LastStatus"]]

        # Reopen Info
        reopened_dates_df = merged_df[merged_df['ticketActivityTypeId'] == 7].groupby('ticketNo')['timestamp'].min().reset_index().rename(columns={'timestamp': 'ReopenedDate'})
        reopen_by_df = merged_df[merged_df['ticketActivityTypeId'] == 7]
        reopen_by_user_df = reopen_by_df.sort_values('timestamp').groupby('ticketNo').first().reset_index()[['ticketNo', 'userId']]
        reopen_by_user_df = pd.merge(reopen_by_user_df, user_df[['id', 'userName']], left_on='userId', right_on='id', how='left')
        reopen_by_user_df = reopen_by_user_df[['ticketNo', 'userName']].rename(columns={'userName': 'ReopenBy'})

        # Product & Customer
        product_merge_df = pd.merge(ticket_df[['ticketNo', 'productId']], product_df[['id', 'name']],
                                   left_on='productId', right_on='id', how='left')[['ticketNo', 'name']].rename(columns={'name': 'Product'})
        customer_merge_df = pd.merge(ticket_df[['ticketNo', 'accountId']], job_card_df[['accountId', 'customerName']],
                                    on='accountId', how='left')[['ticketNo', 'customerName']].rename(columns={'customerName': 'CustomerName'})

        # Resolution Time
        resolution_time_df = pd.merge(open_dates_df[['ticketNo', 'openDate']], resolved_dates_df[['ticketNo', 'ResolvedDate']], on='ticketNo', how='left')
        resolution_time_df['ResolutionMinutes'] = (resolution_time_df['ResolvedDate'] - resolution_time_df['openDate']).dt.total_seconds() / 60
        resolution_time_df['ResolutionDays'] = resolution_time_df['ResolutionMinutes'] / (60 * 24)

        # Extra summary
        summary_df = ticket_df[['lastActivityTimestamp', 'expectedCloseDate', 'ticketNo']].copy()

        # Escalated By
        escalated_by_df = merged_df[merged_df['ticketActivityTypeId'] == 6]
        escalated_by_user_df = (
            escalated_by_df
            .sort_values('timestamp')
            .groupby('ticketNo')
            .first()
            .reset_index()[['ticketNo', 'userId']]
        )
        escalated_by_user_df = pd.merge(
            escalated_by_user_df,
            user_df[['id', 'userName']],
            left_on='userId',
            right_on='id',
            how='left'
        )
        escalated_by_user_df = escalated_by_user_df[['ticketNo', 'userName']].rename(columns={'userName': 'escalatedBy'})

        # === MERGE ALL ===
        merge_steps = [
            (customer_merge_df.drop_duplicates("ticketNo"), 'ticketNo'),
            (product_merge_df.drop_duplicates("ticketNo"), 'ticketNo'),
            (create_dates_df, 'ticketNo'),
            (open_dates_df, 'ticketNo'),
            (resolved_dates_df.drop_duplicates("ticketNo"), 'ticketNo'),
            (closed_dates_df, 'ticketNo'),
            (created_by_df, 'ticketNo'),
            (open_by_user_df.drop_duplicates("ticketNo"), 'ticketNo'),
            (resolved_by_user_df.drop_duplicates("ticketNo"), 'ticketNo'),
            (closed_by_user_df.drop_duplicates("ticketNo"), 'ticketNo'),
            (last_status_df.drop_duplicates("ticketNo"), 'ticketNo'),
            (invoice_data_df.drop_duplicates("ticketNo"), 'ticketNo'),
            (reopened_dates_df.drop_duplicates("ticketNo"), 'ticketNo'),
            (reopen_by_user_df.drop_duplicates("ticketNo"), 'ticketNo'),
            (summary_df.drop_duplicates("ticketNo"), 'ticketNo'),
            (resolution_time_df.drop_duplicates("ticketNo")[['ticketNo', 'ResolutionMinutes', 'ResolutionDays']], 'ticketNo'),
            (jobno_df.drop_duplicates("ticketNo"), 'ticketNo'),
            (jobcard_initiate_date_df.drop_duplicates("ticketNo"), 'ticketNo'),
            (approved_by_df.drop_duplicates("ticketNo"), 'ticketNo'),
            (job_card_info_df.drop_duplicates("ticketNo"), 'ticketNo'),
            (jobcard_closed_date_df.drop_duplicates("ticketNo"), 'ticketNo'),
            (escalated_by_user_df.drop_duplicates("ticketNo"), 'ticketNo'),
        ]

        for df_to_merge, on_column in merge_steps:
            ticket_summary_df = pd.merge(ticket_summary_df, df_to_merge, on=on_column, how='left')

        # Cleanup
        ticket_summary_df = ticket_summary_df.fillna('')
        for col in ticket_summary_df.select_dtypes(include=['datetimetz']).columns:
            ticket_summary_df[col] = ticket_summary_df[col].dt.tz_convert(None)

        print(f"Generated report with {len(ticket_summary_df)} rows and {len(ticket_summary_df.columns)} columns for {financial_year}")

        # Store in memory
        self.ticket_summary_df = ticket_summary_df

        # Save with proper filename
        self.csv_path = csv_filename
        self._save_to_csv(ticket_summary_df)

        return ticket_summary_df

    def _save_to_csv(self, df: pd.DataFrame):
        """Save the dataframe to CSV file"""
        try:
            df.to_csv(self.csv_path, index=False)
            print(f"✅ Saved ticket summary to {self.csv_path}")
            logger.info(f"✅ Saved ticket summary to {self.csv_path}")
        except Exception as e:
            print(f"❌ Error saving CSV: {e}")
            logger.error(f"❌ Error saving CSV: {e}")


    def get_ticket_summary(self, financial_year: Optional[str] = None):
        """Get the ticket summary dataframe for a specific financial year or all years"""
        if financial_year is None:
            financial_year = self.current_financial_year

        if financial_year == "All":
            csv_filename = "ticket_summary_report_all.csv"
        else:
            csv_filename = f"ticket_summary_report_{financial_year.replace('-', '_')}.csv"

        if (
            self.ticket_summary_df is None
            or not hasattr(self, 'current_financial_year_loaded')
            or self.current_financial_year_loaded != financial_year
        ):
            # Try to load from CSV if exists, otherwise generate
            if os.path.exists(csv_filename):
                try:
                    self.ticket_summary_df = pd.read_csv(csv_filename)
                    self.csv_path = csv_filename
                    self.current_financial_year_loaded = financial_year
                    print(f" Loaded ticket summary from {csv_filename}")
                    logger.info(f" Loaded ticket summary from {csv_filename}")

                except Exception as e:
                    print(f"❌ Error loading CSV: {e}")
                    logger.error(f"❌ Error loading CSV: {e}")

                    self.ticket_summary_df = self.generate_complete_ticket_report(financial_year)
            else:
                self.ticket_summary_df = self.generate_complete_ticket_report(financial_year)

        return self.ticket_summary_df


    def get_csv_path(self):
        """Get the path to the CSV file"""
        return self.csv_path

# Singleton instance
complete_report_generator = CompleteReportGenerator()