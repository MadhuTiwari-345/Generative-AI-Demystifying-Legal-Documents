#!/usr/bin/env python3
"""
Stable server runner for Legal AI Flask application
"""

import os
import sys

# Set environment variables to prevent multiprocessing issues
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['TRANSFORMERS_OFFLINE'] = '0'

def main():
    print("=" * 60)
    print("Legal AI Flask Server - Stable Version")
    print("=" * 60)
    
    try:
        # Import and run the stable app
        from app_stable import app
        
        print("✓ Flask app imported successfully")
        print("✓ Starting server on http://127.0.0.1:5000")
        print("✓ Press CTRL+C to stop the server")
        print("=" * 60)
        
        app.run(
            debug=False,
            host='127.0.0.1', 
            port=5000,
            threaded=True,
            use_reloader=False  # Disable reloader to prevent multiprocessing issues
        )
        
    except KeyboardInterrupt:
        print("\n✓ Server stopped by user")
    except Exception as e:
        print(f"✗ Error starting server: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()