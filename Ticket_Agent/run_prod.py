from app import create_app
import os

app = create_app()

if __name__ == "__main__":
    # Production checks
    print("🔍 Running production pre-flight checks...")
    
    # Test DB connection
    try:
        from app.models.database import get_connection
        conn = get_connection()
        print("✅ Database connection successful")
        conn.close()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        exit(1)

    # Test report generation
    try:
        from app.services.report_generator import complete_report_generator
        df = complete_report_generator.get_ticket_summary()
        print(f"✅ Report generated with {len(df)} rows and {len(df.columns)} columns")
    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        exit(1)

    # Environment check
    if os.environ.get('FLASK_ENV') == 'development':
        print("⚠️  Warning: Running in production mode with FLASK_ENV=development")
    
    # Security check - ensure debug is off
    if app.debug:
        print("❌ SECURITY WARNING: Debug mode is enabled in production!")
        exit(1)

    print("🚀 Starting production server...")
    print("📊 Debug mode: OFF")
    print("🌐 Host: 0.0.0.0")
    print("🔌 Port: 5000")
    print("=" * 50)
    
    # Production server (consider using a proper WSGI server like Gunicorn)
    app.run(debug=False, host='0.0.0.0', port=5000)