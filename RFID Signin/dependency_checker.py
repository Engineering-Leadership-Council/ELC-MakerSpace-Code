import sys
import subprocess
import importlib.util
import time
import os

REQUIRED_PACKAGES = [
    "requests",
    "pyttsx3",
    "python-dotenv",
    "pandas",
    "openpyxl"
]

def install(package):
    """ Installs a package using pip """
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█', printEnd="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()

def check_and_install_dependencies():
    """ Checks for required packages and installs them if missing """
    print("\n--- Checking Dependencies ---")
    
    missing_packages = []
    
    # 1. Check what is missing
    total_checks = len(REQUIRED_PACKAGES)
    for i, package in enumerate(REQUIRED_PACKAGES):
        progress_bar(i + 1, total_checks, prefix='Scanning:', suffix=f'Checking {package}', length=30)
        time.sleep(0.1) # simulated delay for visual effect
        
        # Mapping for import name vs package name
        import_name = package
        if package == "python-dotenv": import_name = "dotenv"
        
        if importlib.util.find_spec(import_name) is None:
            missing_packages.append(package)

    print("\n")
    
    if not missing_packages:
        print("All dependencies satisfy requirements.")
        return

    print(f"Missing {len(missing_packages)} package(s): {', '.join(missing_packages)}")
    print("Installing packages... This may take a moment.")
    print("-" * 50)

    # 2. Install missing
    for i, package in enumerate(missing_packages):
        print(f"\n[{i+1}/{len(missing_packages)}] Installing {package}...")
        success = install(package)
        if success:
            print(f"Successfully installed {package}")
        else:
            print(f"FAILED to install {package}. Please install manually.")
            input("Press Enter to continue anyway (app may crash)...")

    print("-" * 50)
    print("Dependency check complete.\n")
    time.sleep(1) # Pause before clearing/starting app
