import sys
import os

# Ensure the parent directory is in path so 'client' can be imported as a package
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)


def start():
    # 1. Check Dependencies
    try:
        from client.dependency_checker import check_and_install_dependencies
        check_and_install_dependencies()

    except Exception as e:
        print(f"Dependency Check Warning: {e}")

    # 2. Launch App
    from client.main import main
    main()

if __name__ == "__main__":
    start()
