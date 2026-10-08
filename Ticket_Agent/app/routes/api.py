from app.services.schema_service import get_column_descriptions, get_enhanced_schema
from flask import Blueprint, render_template, request, send_file, session, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.services.hybrid_agent import process_prompt, hybrid_generator
from app.services.report_generator import complete_report_generator
from app.models import database
from app.models.database import get_connection
import os
import traceback
import pandas as pd
import datetime
api_bp = Blueprint('api', __name__)
import logging

@api_bp.route("/report", methods=["POST"])
# @login_required
def generate_report():
    try:
        data = request.get_json() or {}
        filters = data.get('filters', {})

        df = complete_report_generator.generate_complete_ticket_report(
            from_date=filters.get('from_date'),
            to_date=filters.get('to_date')
        )

        return jsonify({
            "success": True,
            "columns": list(df.columns),
            "row_count": len(df),
            "data": df.head(1000).to_dict(orient='records')
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route("/columns", methods=["GET"])
# @login_required
def get_columns():
    return jsonify({"calculated_columns": get_column_descriptions()})

@api_bp.route("/schema", methods=["GET"])
# @login_required
def get_schema():
    return jsonify({"schema": get_enhanced_schema()})

@api_bp.route("/", methods=["GET", "POST"])
# @login_required
def index():
    error = None
    sql_query = None
    result_html = None
    row_count = 0
    prompt = ""
    show_results = False
    df = None
    result_type = None
    
    # Get financial years and current selection
    financial_years = complete_report_generator.get_financial_years()
    current_financial_year = session.get('financial_year', complete_report_generator.current_financial_year)
    start_date, end_date = complete_report_generator.get_financial_year_dates(current_financial_year)
    financial_year_dates = {'start': start_date, 'end': end_date}

    if request.method == "POST":
        # Check if this is a financial year selection
        if 'financial_year' in request.form and 'prompt' not in request.form:
            financial_year = request.form.get("financial_year")
            session['financial_year'] = financial_year
            # Regenerate report for the selected financial year
            complete_report_generator.get_ticket_summary(financial_year)
            # Get updated dates
            start_date, end_date = complete_report_generator.get_financial_year_dates(financial_year)
            financial_year_dates = {'start': start_date, 'end': end_date}
            current_financial_year = financial_year
        else:
            # Process query
            prompt = request.form.get("prompt", "").strip()
            financial_year = request.form.get("financial_year", current_financial_year)
            
            # Update session if financial year changed
            if financial_year != session.get('financial_year'):
                session['financial_year'] = financial_year
                complete_report_generator.get_ticket_summary(financial_year)
            
            if not prompt:
                error = "Please enter a query prompt"
            else:
                try:
                    # Debug test functionality
                    if prompt.lower() == "debug test":
                        test_result = hybrid_generator.test_query_execution("SELECT * FROM ticket_summary WHERE ResolvedBy LIKE '%ravi%'")
                        result_html = test_result.to_html(
                            classes='table table-striped table-bordered',
                            index=False,
                            escape=False
                        )
                        row_count = len(test_result)
                        show_results = True
                        sql_query = "SELECT * FROM ticket_summary WHERE ResolvedBy LIKE '%ravi%'"
                    else:
                        # Try to call process_prompt with financial_year parameter
                        # If it fails, fall back to calling without it
                        try:
                            result = process_prompt(prompt, financial_year)
                        except TypeError as e:
                            if "takes 1 positional argument but 2 were given" in str(e):
                                # Fall back to original function signature
                                result = process_prompt(prompt)
                            else:
                                raise e
                        
                        result_type = result["type"]
                        sql_query = result["query"]
                        df = result["dataframe"]

                        if df.empty:
                            error = "Query executed successfully but returned no results."
                        else:
                            df = df.drop_duplicates()
                            result_html = df.to_html(
                                classes='table table-striped table-bordered',
                                index=False,
                                escape=False
                            )
                            row_count = len(df)
                            show_results = True

                        # Save results only if df exists
                        if show_results and df is not None:
                            os.makedirs("storage/output", exist_ok=True)
                            output_path = os.path.join("storage/output", f"query_result_{financial_year.replace('-', '_')}.xlsx")
                            df.to_excel(output_path, index=False)

                except Exception as e:
                    error = f"Error: {str(e)}"

    return render_template(
        "result.html",
        error=error,
        sql_query=sql_query,
        result_html=result_html,
        row_count=row_count,
        prompt=prompt,
        show_results=show_results,
        result_type=result_type,
        complete_report_generator=complete_report_generator,
        # username=current_user.username,
        financial_years=financial_years,
        current_financial_year=current_financial_year,
        financial_year_dates=financial_year_dates
    )


@api_bp.route("/select-financial-year", methods=["POST"])
# @login_required
def select_financial_year():
    financial_year = request.form.get("financial_year")
    session['financial_year'] = financial_year

    if financial_year == "All":
        # regenerate report with no date filtering
        complete_report_generator.get_ticket_summary(None)
    else:
        # regenerate report for the specific year
        complete_report_generator.get_ticket_summary(financial_year)

    return redirect(url_for('api.index'))



from flask import request, render_template

@api_bp.route("/process-query", methods=["POST"])
def process_query():
    financial_year = request.form.get("financial_year")
    prompt = request.form.get("prompt", "").strip()

    # Sync session financial year
    if financial_year != session.get('financial_year'):
        session['financial_year'] = financial_year
        complete_report_generator.get_ticket_summary(financial_year)

    error = None
    sql_query = None
    result_html = None
    row_count = 0
    show_results = False
    df = None
    result_type = None

    if not prompt:
        error = "Please enter a query prompt"
    else:
        try:
            result = process_prompt(prompt, financial_year)
            result_type = result["type"]
            sql_query = result["query"]
            df = result["dataframe"]

            if df.empty:
                error = "Query executed successfully but returned no results."
            else:
                df = df.drop_duplicates()
                result_html = df.to_html(
                    classes='table table-striped table-bordered',
                    index=False,
                    escape=False
                )
                row_count = len(df)
                show_results = True

            if show_results and df is not None:
                output_dir = os.path.join(os.path.dirname(__file__), "..", "storage", "output")
                os.makedirs(output_dir, exist_ok=True)

                output_path = os.path.join(output_dir, f"query_result_{financial_year.replace('-', '_')}.xlsx")

                df.to_excel(output_path, index=False)

        except Exception as e:
            error = f"Error: {str(e)}"

    # Prepare context
    financial_years = complete_report_generator.get_financial_years()
    start_date, end_date = complete_report_generator.get_financial_year_dates(financial_year)
    financial_year_dates = {'start': start_date, 'end': end_date}

    context = dict(
        error=error,
        sql_query=sql_query,
        result_html=result_html,
        row_count=row_count,
        prompt=prompt,
        show_results=show_results,
        result_type=result_type,
        complete_report_generator=complete_report_generator,
        financial_years=financial_years,
        current_financial_year=financial_year,
        financial_year_dates=financial_year_dates
    )

    # ⚡️Return partial template if AJAX
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("partials/query_results.html", **context)

    # Otherwise, return full page
    return render_template("result.html", **context)

@api_bp.route("/download")
def download():
    try:
        financial_year = session.get("financial_year", complete_report_generator.current_financial_year)
        filename = f"query_result_{financial_year.replace('-', '_')}.xlsx"

        output_path = os.path.join(os.path.dirname(__file__), "..", "storage", "output", filename)
        output_path = os.path.abspath(output_path)

        if os.path.exists(output_path):
            return send_file(output_path, as_attachment=True, download_name="report.xlsx")
        return "No report file found. Please generate a report first."
    except Exception as e:
        return f"Download error: {str(e)}"

@api_bp.route("/test-db")
# @login_required
def test_db():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION as version")
        result = cursor.fetchone()
        conn.close()
        return f"Database connection successful: {result[0]}"
    except Exception as e:
        return f"Database connection failed: {str(e)}"

@api_bp.route("/test-report")
# @login_required
def test_report():
    try:
        df = complete_report_generator.get_ticket_summary()
        
        # Convert NaT values to None for JSON serialization
        df = df.where(df.notnull(), None)
        
        return jsonify({
            "success": True,
            "rows": len(df),
            "columns": len(df.columns),
            "sample_data": df.head(5).to_dict(orient='records')
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Report test failed: {str(e)}"
        }), 500
@api_bp.route("health/", methods=["GET"])
def health():
        logging.info("Health check endpoint accessed")
        try:
            # Example: log database connection status
            db_status = "connected" if database.is_connected() else "disconnected"
            logging.info(f"Database status: {db_status}")
            
            return jsonify({"status": "ok", "model": "ready", "database": db_status}), 200
        except Exception as e:
            logging.error(f"Error in health endpoint: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500