#!/usr/bin/env python3
"""
Chrome and ChromeDriver Installation Script for UPS Server
Must be run as root: sudo python3 install_chrome.py
"""

import os
import sys
import subprocess
import shutil
import re
from pathlib import Path

def run_command(cmd, shell=False, check=True, capture_output=False):
    """Execute a shell command and handle errors."""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=shell, check=check, 
                                  capture_output=True, text=True)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=shell, check=check)
            return None
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        if capture_output and e.stderr:
            print(f"Error output: {e.stderr}")
        raise

def check_root():
    """Check if script is running as root."""
    if os.geteuid() != 0:
        print("ERROR: This script must be run as root")
        print("Usage: sudo python3 install_chrome.py")
        sys.exit(1)

def remove_snap_chromium():
    """Remove snap version of Chromium if installed."""
    print("\n[1/6] Checking for snap Chromium installation...")
    try:
        result = subprocess.run(['snap', 'list'], capture_output=True, text=True)
        if 'chromium' in result.stdout:
            print("Found snap Chromium. Removing...")
            run_command(['snap', 'remove', 'chromium'])
            print("✓ Snap Chromium removed")
        else:
            print("✓ No snap Chromium found")
    except FileNotFoundError:
        print("✓ Snap not installed")

def install_chrome():
    """Download and install Google Chrome."""
    print("\n[2/6] Installing Google Chrome...")
    
    # Check if Chrome is already installed
    try:
        version = run_command(['google-chrome', '--version'], capture_output=True)
        print(f"✓ Google Chrome already installed: {version}")
        return
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Download Chrome
    chrome_deb = "/tmp/google-chrome-stable_current_amd64.deb"
    print("Downloading Google Chrome...")
    run_command([
        'wget', '-q', '--show-progress',
        'https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb',
        '-O', chrome_deb
    ])
    
    # Install Chrome
    print("Installing Google Chrome...")
    run_command(['apt', 'install', '-y', chrome_deb])
    
    # Cleanup
    if os.path.exists(chrome_deb):
        os.remove(chrome_deb)
    
    # Verify installation
    version = run_command(['google-chrome', '--version'], capture_output=True)
    print(f"✓ Google Chrome installed: {version}")

def get_chrome_version():
    """Get the major version of installed Chrome."""
    print("\n[3/6] Detecting Chrome version...")
    version_output = run_command(['google-chrome', '--version'], capture_output=True)
    match = re.search(r'(\d+)', version_output)
    if match:
        major_version = match.group(1)
        print(f"✓ Chrome major version: {major_version}")
        return major_version
    else:
        raise Exception("Could not determine Chrome version")

def install_chromedriver(chrome_major_version):
    """Download and install ChromeDriver matching Chrome version."""
    print("\n[4/6] Installing ChromeDriver...")
    
    # Check if ChromeDriver is already installed and matches version
    try:
        driver_version = run_command(['chromedriver', '--version'], capture_output=True)
        if chrome_major_version in driver_version:
            print(f"✓ ChromeDriver already installed and matches Chrome version: {driver_version}")
            return
        else:
            print(f"ChromeDriver version mismatch. Reinstalling...")
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Get ChromeDriver version for this Chrome version
    print(f"Fetching ChromeDriver version for Chrome {chrome_major_version}...")
    api_url = f"https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_{chrome_major_version}"
    
    try:
        chromedriver_version = run_command(['curl', '-s', api_url], capture_output=True)
    except subprocess.CalledProcessError:
        chromedriver_version = ""
    
    if not chromedriver_version:
        print(f"ERROR: Could not fetch ChromeDriver version for Chrome {chrome_major_version}")
        print("Visit https://googlechromelabs.github.io/chrome-for-testing/ for available versions")
        sys.exit(1)
    
    print(f"ChromeDriver version: {chromedriver_version}")
    
    # Download ChromeDriver
    download_url = f"https://storage.googleapis.com/chrome-for-testing-public/{chromedriver_version}/linux64/chromedriver-linux64.zip"
    temp_zip = "/tmp/chromedriver-linux64.zip"
    temp_dir = "/tmp/chromedriver-linux64"
    
    print("Downloading ChromeDriver...")
    run_command(['wget', '-q', '--show-progress', download_url, '-O', temp_zip])
    
    # Extract ChromeDriver
    print("Extracting ChromeDriver...")
    run_command(['unzip', '-o', '-q', temp_zip, '-d', '/tmp'])
    
    # Install ChromeDriver
    print("Installing ChromeDriver to /usr/bin/chromedriver...")
    chromedriver_binary = os.path.join(temp_dir, 'chromedriver')
    shutil.move(chromedriver_binary, '/usr/bin/chromedriver')
    run_command(['chmod', '+x', '/usr/bin/chromedriver'])
    
    # Cleanup
    if os.path.exists(temp_zip):
        os.remove(temp_zip)
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    # Verify installation
    version = run_command(['chromedriver', '--version'], capture_output=True)
    print(f"✓ ChromeDriver installed: {version}")

def test_chrome_headless():
    """Test Chrome works in headless mode."""
    print("\n[5/6] Testing Chrome in headless mode...")
    try:
        output = run_command([
            'google-chrome',
            '--headless',
            '--no-sandbox',
            '--disable-gpu',
            '--dump-dom',
            'https://www.google.com'
        ], capture_output=True)
        
        if 'google' in output.lower():
            print("✓ Chrome headless mode works correctly")
        else:
            print("⚠ Chrome ran but output unexpected")
    except subprocess.CalledProcessError as e:
        print(f"✗ Chrome headless test failed: {e}")
        sys.exit(1)

def test_selenium():
    """Test Selenium with Chrome."""
    print("\n[6/6] Testing Selenium with Chrome...")
    
    # Check if selenium is installed
    try:
        import selenium
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
    except ImportError:
        print("⚠ Selenium not installed. Skipping Selenium test.")
        print("Install with: pip3 install selenium --break-system-packages")
        return
    
    try:
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        
        # Explicitly specify ChromeDriver location
        service = Service(executable_path='/usr/bin/chromedriver')
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get('https://www.google.com')
        title = driver.title
        driver.quit()
        
        print(f"✓ Selenium test successful. Page title: {title}")
    except Exception as e:
        print(f"✗ Selenium test failed: {e}")
        print("This may indicate a configuration issue with Chrome/ChromeDriver")
        sys.exit(1)

def main():
    """Main installation process."""
    print("=" * 60)
    print("Chrome and ChromeDriver Installation for UPS Server")
    print("=" * 60)
    
    check_root()
    
    try:
        remove_snap_chromium()
        install_chrome()
        chrome_version = get_chrome_version()
        install_chromedriver(chrome_version)
        test_chrome_headless()
        test_selenium()
        
        print("\n" + "=" * 60)
        print("✓ Installation completed successfully!")
        print("=" * 60)
        print("\nChrome and ChromeDriver are ready for use with Selenium.")
        print("You can now start the UPS server service.")
        
    except Exception as e:
        print(f"\n✗ Installation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
