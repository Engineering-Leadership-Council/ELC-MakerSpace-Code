import sys
import os

# Ensure the 'client' package can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def start():
    # 1. Check Dependencies
    try:
        from dependency_checker import check_and_install_dependencies
        check_and_install_dependencies()
    except Exception as e:
        print(f"Dependency Check Warning: {e}")

    # 2. Launch App
    from client.main import main
    main()

if __name__ == "__main__":
    start()
