from tkinter import ttk
from .config import MCC_BLACK, MCC_GOLD, TEXT_WHITE, HEADER_BLACK, SUCCESS_GREEN

def apply_styles():
    style = ttk.Style()
    style.theme_use('clam')  # 'clam' allows for better color customization
    
    # General Frame
    style.configure('TFrame', background=MCC_BLACK)
    
    # Labels
    style.configure('TLabel', background=MCC_BLACK, foreground=TEXT_WHITE, font=('Segoe UI', 11))
    style.configure('Header.TLabel', background=HEADER_BLACK, foreground=MCC_GOLD, font=('Segoe UI', 20, 'bold'))
    style.configure('SubHeader.TLabel', background=MCC_BLACK, foreground=MCC_GOLD, font=('Segoe UI', 14, 'bold'))
    style.configure('Status.TLabel', background=HEADER_BLACK, foreground="gray", font=('Segoe UI', 10))
    
    # Buttons
    style.configure('TButton', 
                    font=('Segoe UI', 11, 'bold'), 
                    background=MCC_GOLD, 
                    foreground="black", 
                    borderwidth=0, 
                    focuscolor=MCC_GOLD)
    style.map('TButton', background=[('active', '#FFCA28'), ('disabled', '#555')]) # Lighter gold on hover
    
    # Toggle Button Style (Sign In / Sign Out)
    style.configure('Toggle.TButton', 
                    font=('Segoe UI', 12, 'bold'),
                    background=SUCCESS_GREEN,
                    foreground="white")
    
    # Radiobuttons
    style.configure('TRadiobutton', background=MCC_BLACK, foreground=TEXT_WHITE, font=('Segoe UI', 11))
    style.map('TRadiobutton', indicatorcolor=[('selected', MCC_GOLD)])
    
    # Checkbuttons
    style.configure('TCheckbutton', background=MCC_BLACK, foreground=TEXT_WHITE, font=('Segoe UI', 11))
    style.map('TCheckbutton', indicatorcolor=[('selected', MCC_GOLD)])
    
    # Labelframe
    style.configure('TLabelframe', background=MCC_BLACK, foreground=MCC_GOLD)
    style.configure('TLabelframe.Label', background=MCC_BLACK, foreground=MCC_GOLD, font=('Segoe UI', 10, 'bold'))

    # Combobox
    style.configure('TCombobox', 
                    fieldbackground=MCC_BLACK, 
                    background=MCC_GOLD, 
                    foreground=TEXT_WHITE,
                    arrowcolor="black",
                    darkcolor=MCC_BLACK,
                    lightcolor=MCC_BLACK,
                    selectbackground=MCC_GOLD,
                    selectforeground="black",
                    bordercolor=MCC_GOLD)
    
    style.map('TCombobox', 
              fieldbackground=[('readonly', MCC_BLACK)],
              selectbackground=[('readonly', MCC_GOLD)],
              selectforeground=[('readonly', "black")],
              foreground=[('readonly', TEXT_WHITE)])
