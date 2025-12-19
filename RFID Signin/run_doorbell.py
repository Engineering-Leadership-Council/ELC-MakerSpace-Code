import sys
import os

# Ensure the 'client' package can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from client.main import main

if __name__ == "__main__":
    main()
