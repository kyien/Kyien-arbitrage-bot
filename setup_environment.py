#!/usr/bin/env python3
"""
Environment Setup Script for Arbitrage Bot
Creates virtual environment and installs dependencies safely
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a shell command with error handling"""
    print(f"📦 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def main():
    """Main setup function"""
    print("🔧 Setting up Arbitrage Bot Environment")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version}")
    
    # Create virtual environment if it doesn't exist
    if not Path("venv").exists():
        if not run_command(f"{sys.executable} -m venv venv", "Creating virtual environment"):
            sys.exit(1)
    
    # Determine pip path based on OS
    pip_path = "venv/bin/pip" if os.name != "nt" else "venv\\Scripts\\pip"
    python_path = "venv/bin/python" if os.name != "nt" else "venv\\Scripts\\python"
    
    # Upgrade pip
    run_command(f"{pip_path} install --upgrade pip", "Upgrading pip")
    
    # Install requirements
    if Path("requirements.txt").exists():
        print("📋 Installing dependencies from requirements.txt...")
        if not run_command(f"{pip_path} install -r requirements.txt", "Installing requirements"):
            print("⚠️  Some packages may have failed, continuing...")
    
    # Install additional security packages
    security_packages = [
        "pytest",
        "pytest-asyncio", 
        "black",
        "flake8",
        "safety"
    ]
    
    print("🔒 Installing security and testing packages...")
    for package in security_packages:
        run_command(f"{pip_path} install {package}", f"Installing {package}")
    
    print("\n" + "=" * 50)
    print("✅ Environment setup complete!")
    print("\n🔑 Next steps:")
    print("1. Activate virtual environment:")
    print(f"   source venv/bin/activate  # Linux/Mac")
    print(f"   venv\\Scripts\\activate     # Windows")
    print("2. Copy .env.example to .env and configure:")
    print("   cp .env.example .env")
    print("3. Run security checks:")
    print(f"   {python_path} -m safety check")
    print("4. Test the setup:")
    print(f"   {python_path} scripts/whitelist_setup.py --help")

if __name__ == "__main__":
    main()
