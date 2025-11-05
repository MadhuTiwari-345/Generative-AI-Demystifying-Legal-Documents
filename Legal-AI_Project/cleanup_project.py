#!/usr/bin/env python3
"""
Project cleanup script to remove redundant files and optimize structure
"""

import os
import shutil
import json

def cleanup_project():
    """Remove redundant and unnecessary files"""
    
    # Files to remove from flask_server
    flask_redundant_files = [
        'app_simple.py',
        'minimal_test.py', 
        'test_complete.py',
        'test_curl.py',
        'test_model.py',
        'test_server.py',
        'test_text_cleaning.py',
        'predict_optimized.py',
        'index.html',
        'nbest.json'
    ]
    
    # Remove redundant flask files
    flask_dir = 'flask_server'
    for file in flask_redundant_files:
        file_path = os.path.join(flask_dir, file)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Removed: {file_path}")
    
    # Clean up .next build cache (can be regenerated)
    next_cache_dir = 'web_app/.next'
    if os.path.exists(next_cache_dir):
        shutil.rmtree(next_cache_dir)
        print(f"Removed build cache: {next_cache_dir}")
    
    # Remove unnecessary component files
    web_redundant_files = [
        'web_app/components/foooter.tsx',  # Typo in filename
        'web_app/pages/admin.tsx',
        'web_app/pages/api-example.tsx', 
        'web_app/pages/client.tsx',
        'web_app/pages/me.tsx',
        'web_app/pages/protected.tsx',
        'web_app/pages/server.tsx'
    ]
    
    for file in web_redundant_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"Removed: {file}")
    
    # Create optimized project structure info
    structure_info = {
        "project_structure": {
            "flask_server": {
                "core_files": [
                    "app_optimized.py - Main optimized Flask application",
                    "predict.py - ML prediction logic", 
                    "paraphrase.py - Text paraphrasing",
                    "requirements_optimized.txt - Updated dependencies"
                ],
                "data": [
                    "questions_short.txt - Predefined questions",
                    "contract samples - Test documents"
                ]
            },
            "web_app": {
                "core_files": [
                    "pages/dashboard_optimized.tsx - Enhanced dashboard",
                    "pages/_app.tsx - App configuration",
                    "pages/index.tsx - Landing page"
                ],
                "components": [
                    "navbar.tsx - Navigation",
                    "footer.tsx - Footer component", 
                    "access-denied.tsx - Auth component"
                ]
            }
        },
        "optimizations": [
            "PyMuPDF for robust PDF text extraction",
            "Efficient model loading with caching",
            "User-defined questions with validation",
            "Search functionality for predefined questions",
            "Better error handling and logging",
            "Sentiment analysis for answers",
            "Paraphrasing for better understanding",
            "Responsive UI with loading states"
        ]
    }
    
    with open('PROJECT_STRUCTURE.json', 'w') as f:
        json.dump(structure_info, f, indent=2)
    
    print("\nProject cleanup completed!")
    print("Key improvements:")
    print("- Removed redundant test and duplicate files")
    print("- Optimized Flask server with PyMuPDF")
    print("- Enhanced dashboard with custom questions")
    print("- Better text extraction and processing")
    print("- Improved error handling and validation")

if __name__ == "__main__":
    cleanup_project()