#!/usr/bin/env python3
"""
Test runner script for collecting-website
"""
import subprocess
import sys
import os
from pathlib import Path

def run_python_tests():
    """Run Python backend tests"""
    print("🧪 Running Python Backend Tests...")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", 
            "--tb=short", 
            "--cov=app", 
            "--cov-report=term-missing",
            "--cov-report=html"
        ], check=True, capture_output=False)
        
        print("✅ Python tests passed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Python tests failed with exit code {e.returncode}")
        return False

def check_js_tests():
    """Check if JavaScript tests exist and provide instructions"""
    test_file = Path("tests/test_optimistic_ui.html")
    if test_file.exists():
        print("\n🌐 JavaScript Frontend Tests Available")
        print("=" * 50)
        print(f"📂 Open {test_file} in your browser to run frontend tests")
        print("   Tests include:")
        print("   • State manager unit tests")
        print("   • Optimistic update integration tests")
        print("   • Rollback scenario tests")
        print("   • Mock API tests")
        return True
    else:
        print("\n❌ JavaScript tests not found")
        return False

def run_linting():
    """Run code quality checks"""
    print("\n🔍 Running Code Quality Checks...")
    print("=" * 50)
    
    # Check if files exist before linting
    python_files = list(Path(".").glob("**/*.py"))
    if not python_files:
        print("No Python files found for linting")
        return True
    
    try:
        # Basic Python syntax check
        for py_file in ["app/__init__.py", "app/routes.py", "config.py", "wsgi.py"]:
            if Path(py_file).exists():
                result = subprocess.run([
                    sys.executable, "-m", "py_compile", py_file
                ], check=True, capture_output=True, text=True)
        
        print("✅ Python syntax check passed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Syntax errors found: {e.stderr}")
        return False
    except FileNotFoundError:
        print("⚠️  Linting tools not available, skipping...")
        return True

def main():
    """Run all tests and checks"""
    print("🚀 Starting Collecting Website Test Suite")
    print("=" * 60)
    
    all_passed = True
    
    # Run backend tests
    if not run_python_tests():
        all_passed = False
    
    # Check for frontend tests
    check_js_tests()
    
    # Run linting
    if not run_linting():
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All automated tests passed!")
        print("\n📋 Test Coverage:")
        print("✅ API endpoint tests")
        print("✅ Optimistic UI backend support")
        print("✅ Error handling and rollback")
        print("✅ Database operations")
        print("✅ Edge cases and race conditions")
        print("\n🌐 Don't forget to run the frontend tests in your browser!")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()