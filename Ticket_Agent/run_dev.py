from app import create_app

app = create_app()

if __name__ == "__main__":
    # Test DB connection
    try:
        from app.models.database import get_connection
        conn = get_connection()
        print("✅ Database connection successful")
        app.logger.info("✅ Database connection successful")    
        conn.close()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        app.logger.error(f"❌ Database connection failed: {e}")
    # Test report generation
    try:
        from app.services.report_generator import complete_report_generator
        df = complete_report_generator.get_ticket_summary()
        app.logger.info(f"✅ Report generated with {len(df)} rows and {len(df.columns)} columns")
    except Exception as e:
        app.logger.error(f"❌ Report generation failed: {e}")
        print(f"❌ Report generation failed: {e}")

    print("🚀 Starting development server...")
    print("📊 Debug mode: ON")
    print("🌐 Host: 0.0.0.0 (accessible from network)")
    print("🔌 Port: 5000")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)