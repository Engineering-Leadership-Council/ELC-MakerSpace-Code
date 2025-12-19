from .gui import RFIDClientApp
import tkinter as tk

def main():
    root = tk.Tk()
    app = RFIDClientApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
