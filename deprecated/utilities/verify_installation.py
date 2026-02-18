#!/usr/bin/env python3
"""
Verification script for SCAD Forecast Tool v2.0
Checks that all components are properly installed and working.

Usage:
    python3 verify_installation.py
"""

import sys
import os
from pathlib import Path

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def check_python_version():
    """Check Python version."""
    print_header("Checking Python Version")
    version = sys.version_info
    print(f"Python {version.major}.{version.minor}.{version.micro}")

    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python 3.9+ required")
        return False
    else:
        print("✓ Python version OK")
        return True

def check_file_structure():
    """Check that all required files exist."""
    print_header("Checking File Structure")

    required_files = [
        "app_chat.py",
        "app.py",
        "Forecast_Tool_Launcher.command",
        "requirements.txt",
        "requirements_chat.txt",
        "QUICKSTART_CHAT.md",
        "README.md",
        "CLAUDE.md",
        "forecast_tool/__init__.py",
        "forecast_tool/chat/__init__.py",
        "forecast_tool/chat/command_parser.py",
        "forecast_tool/chat/conversation.py",
        "forecast_tool/chat/responses.py",
        "forecast_tool/ui/__init__.py",
        "forecast_tool/ui/chat_window.py",
        "forecast_tool/ui/output_window.py",
        "forecast_tool/forecasting/__init__.py",
        "forecast_tool/forecasting/prophet_forecast.py",
        "forecast_tool/forecasting/ets_forecast.py",
        "forecast_tool/forecasting/ensemble.py",
        "forecast_tool/data/__init__.py",
        "forecast_tool/data/loaders.py",
        "forecast_tool/data/transformers.py",
        "forecast_tool/config/__init__.py",
        "forecast_tool/config/settings.py",
    ]

    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            all_exist = False

    return all_exist

def check_imports():
    """Check that core modules can be imported."""
    print_header("Checking Module Imports")

    modules_to_test = [
        ("forecast_tool.chat.command_parser", "CommandParser"),
        ("forecast_tool.chat.conversation", "ConversationManager"),
        ("forecast_tool.chat.responses", "format_welcome_message"),
        ("forecast_tool.forecasting.prophet_forecast", "forecast_prophet"),
        ("forecast_tool.forecasting.ets_forecast", "forecast_ets"),
        ("forecast_tool.forecasting.ensemble", "calculate_sections"),
        ("forecast_tool.data.loaders", "load_course_mapping"),
        ("forecast_tool.data.transformers", "quarter_to_date"),
        ("forecast_tool.config.settings", "DEFAULT_SECTION_CAPACITY"),
    ]

    all_imported = True
    for module_name, item_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[item_name])
            getattr(module, item_name)
            print(f"✓ {module_name}.{item_name}")
        except ImportError as e:
            print(f"❌ {module_name}.{item_name} - Import Error: {e}")
            all_imported = False
        except AttributeError as e:
            print(f"❌ {module_name}.{item_name} - Not Found: {e}")
            all_imported = False

    return all_imported

def check_dependencies():
    """Check required Python packages."""
    print_header("Checking Dependencies")

    required_packages = [
        "streamlit",
        "prophet",
        "statsmodels",
        "pandas",
        "numpy",
        "openpyxl",
    ]

    all_installed = True
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"❌ {package} - NOT INSTALLED")
            all_installed = False

    return all_installed

def test_command_parser():
    """Test command parser functionality."""
    print_header("Testing Command Parser")

    try:
        from forecast_tool.chat.command_parser import CommandParser

        parser = CommandParser()

        # Test 1: Forecast intent
        result = parser.parse("Forecast Spring 2026")
        assert result['intent'] == 'forecast', f"Expected 'forecast', got '{result['intent']}'"
        assert result['parameters']['term'] == 'Spring 2026', "Term not parsed correctly"
        print("✓ Test 1: Forecast intent recognition")

        # Test 2: Configure intent
        result = parser.parse("Set capacity to 25")
        assert result['intent'] == 'configure', f"Expected 'configure', got '{result['intent']}'"
        print("✓ Test 2: Configure intent recognition")

        # Test 3: All courses
        result = parser.parse("Forecast all courses")
        assert result['parameters'].get('all_courses') == True, "All courses not detected"
        print("✓ Test 3: All courses parameter")

        return True

    except Exception as e:
        print(f"❌ Command parser test failed: {e}")
        return False

def test_utilities():
    """Test utility functions."""
    print_header("Testing Utility Functions")

    try:
        from forecast_tool.data.transformers import quarter_to_date, date_to_quarter_label
        from forecast_tool.forecasting.ensemble import calculate_sections
        from datetime import datetime

        # Test 1: Quarter to date
        date = quarter_to_date(2026, 'Spring')
        assert date.year == 2026, "Year incorrect"
        assert date.month == 4, "Month incorrect for Spring"
        print("✓ Test 1: quarter_to_date")

        # Test 2: Date to quarter label
        label = date_to_quarter_label(datetime(2026, 4, 1))
        assert label == "Spring 2026", f"Expected 'Spring 2026', got '{label}'"
        print("✓ Test 2: date_to_quarter_label")

        # Test 3: Section calculation
        sections = calculate_sections(85, 20, 10)
        assert sections == 5, f"Expected 5 sections, got {sections}"
        print("✓ Test 3: calculate_sections")

        return True

    except Exception as e:
        print(f"❌ Utility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_launcher_executable():
    """Check that launcher is executable."""
    print_header("Checking Launcher Script")

    launcher = Path("Forecast_Tool_Launcher.command")

    if not launcher.exists():
        print("❌ Launcher script not found")
        return False

    if os.access(launcher, os.X_OK):
        print("✓ Launcher is executable")
        return True
    else:
        print("❌ Launcher is not executable")
        print("  Run: chmod +x Forecast_Tool_Launcher.command")
        return False

def main():
    """Run all verification checks."""
    print("\n" + "=" * 60)
    print("  SCAD Forecast Tool v2.0 - Installation Verification")
    print("=" * 60)

    results = {
        "Python Version": check_python_version(),
        "File Structure": check_file_structure(),
        "Module Imports": check_imports(),
        "Dependencies": check_dependencies(),
        "Command Parser": test_command_parser(),
        "Utilities": test_utilities(),
        "Launcher": check_launcher_executable(),
    }

    print_header("Verification Summary")

    all_passed = True
    for check, passed in results.items():
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status} - {check}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)

    if all_passed:
        print("✅ All checks passed! Installation verified.")
        print("\nNext steps:")
        print("1. Test the chat interface:")
        print("   streamlit run app_chat.py")
        print("\n2. Or use the one-click launcher:")
        print("   ./Forecast_Tool_Launcher.command")
        return 0
    else:
        print("❌ Some checks failed. Please review errors above.")
        print("\nTo fix missing dependencies:")
        print("   pip install -r requirements.txt")
        print("\nTo fix permissions:")
        print("   chmod +x Forecast_Tool_Launcher.command")
        return 1

if __name__ == "__main__":
    sys.exit(main())
