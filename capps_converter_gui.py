#!/usr/bin/env python3
"""
CAPPS XML Converter GUI for AIMsi POS
Enhanced version with two-file support for AIMsi exports
WITH PERSISTENT SETTINGS - Auto-saves on every change
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import os
from pathlib import Path
from datetime import datetime
import webbrowser
import json
import queue
import sys
import threading

# Import the converter module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from csv_to_capps_xml import CAPPSConverter


class TextRedirector:
    """
    Thread-safe stdout/stderr redirector for tkinter Text widget
    Uses queue to safely update GUI from background threads
    """
    def __init__(self, text_widget, tag="stdout"):
        self.text_widget = text_widget
        self.tag = tag
        self.queue = queue.Queue()
        self.update_scheduled = False

    def write(self, message):
        """Called by print() or sys.stdout.write()"""
        if message:  # Only ignore completely empty strings, preserve newlines
            self.queue.put(message)
            self.schedule_update()

    def flush(self):
        """Required for file-like object compatibility"""
        pass

    def schedule_update(self):
        """Schedule GUI update on main thread"""
        if not self.update_scheduled:
            self.update_scheduled = True
            self.text_widget.after(100, self.process_queue)

    def process_queue(self):
        """Process all queued messages (runs on main thread)"""
        self.update_scheduled = False
        while not self.queue.empty():
            try:
                message = self.queue.get_nowait()
                self.text_widget.config(state="normal")
                self.text_widget.insert(tk.END, message, self.tag)
                self.text_widget.see(tk.END)  # Auto-scroll to bottom
                self.text_widget.config(state="disabled")
            except queue.Empty:
                break

        # Schedule next update if queue has more items
        if not self.queue.empty():
            self.schedule_update()


class CAPPSConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CAPPS XML Converter for AIMsi - Version 2")
        self.root.geometry("850x800")
        self.root.minsize(700, 700)
        
        # Store variables
        self.purchases_file_path = tk.StringVar()
        self.serials_file_path = tk.StringVar()
        self.license_number = tk.StringVar()
        self.employee_name = tk.StringVar(value="Store Employee")
        self.min_cost = tk.StringVar(value="100")
        self.days_lookback = tk.StringVar(value="5")
        self.include_isi_serials = tk.BooleanVar(value=False)
        self.capss_client_id = tk.StringVar()
        self.capss_client_secret = tk.StringVar()
        self.api_key = tk.StringVar()
        self.api_provider = tk.StringVar(value="groq")
        
        # Load saved settings
        self.load_settings()
        
        # Add traces to auto-save when values change
        self.setup_auto_save()
        
        # Create GUI
        self.create_widgets()

        # Setup logging redirection
        self.setup_logging()

        # Set window close protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_auto_save(self):
        """Setup automatic saving when settings change"""
        # Add trace to each variable to save when it changes
        self.license_number.trace_add('write', lambda *args: self.save_settings())
        self.employee_name.trace_add('write', lambda *args: self.save_settings())
        self.min_cost.trace_add('write', lambda *args: self.save_settings())
        self.days_lookback.trace_add('write', lambda *args: self.save_settings())
        self.include_isi_serials.trace_add('write', lambda *args: self.save_settings())
        self.capss_client_id.trace_add('write', lambda *args: self.save_settings())
        self.capss_client_secret.trace_add('write', lambda *args: self.save_settings())
        self.api_provider.trace_add('write', lambda *args: self.save_settings())
        self.api_key.trace_add('write', lambda *args: self.save_settings())
        self.purchases_file_path.trace_add('write', lambda *args: self.save_settings())
        self.serials_file_path.trace_add('write', lambda *args: self.save_settings())
        
    def create_widgets(self):
        """Create all GUI widgets"""

        # Title
        title_frame = ttk.Frame(self.root, padding="10")
        title_frame.grid(row=0, column=0, sticky="ew")

        title_label = ttk.Label(
            title_frame,
            text="CAPPS XML Converter for AIMsi",
            font=("Arial", 16, "bold")
        )
        title_label.pack()

        subtitle_label = ttk.Label(
            title_frame,
            text="Convert AIMsi purchases and serials exports to CAPPS XML",
            font=("Arial", 10)
        )
        subtitle_label.pack()
        
        # Main frame with scrollable canvas
        canvas_container = ttk.Frame(self.root)
        canvas_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        canvas_container.grid_rowconfigure(0, weight=1)
        canvas_container.grid_columnconfigure(0, weight=1)

        # Create canvas
        canvas = tk.Canvas(canvas_container, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")

        # Create vertical scrollbar
        scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Create the scrollable frame inside canvas
        scrollable_frame = ttk.Frame(canvas, padding="15")
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # Configure canvas scrolling
        def configure_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Ensure canvas_window matches canvas width
            canvas.itemconfig(canvas_window, width=canvas.winfo_width())

        scrollable_frame.bind("<Configure>", configure_scroll_region)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))

        # Mouse wheel binding (Windows + Linux)
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # Configure root grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # Use scrollable_frame as main_frame for all widgets
        main_frame = scrollable_frame
        
        # License Number
        ttk.Label(main_frame, text="License Number:*").grid(
            row=0, column=0, sticky="w", pady=5
        )
        license_entry = ttk.Entry(
            main_frame, 
            textvariable=self.license_number,
            width=30
        )
        license_entry.grid(row=0, column=1, sticky="ew", pady=5)
        
        ttk.Label(
            main_frame,
            text="(Your CA secondhand dealer license)",
            font=("Arial", 9),
            foreground="gray"
        ).grid(row=0, column=2, sticky="w", padx=5)
        
        # Employee Name
        ttk.Label(main_frame, text="Employee Name:*").grid(
            row=1, column=0, sticky="w", pady=5
        )
        employee_entry = ttk.Entry(
            main_frame,
            textvariable=self.employee_name,
            width=30
        )
        employee_entry.grid(row=1, column=1, sticky="ew", pady=5)

        # Minimum Cost
        ttk.Label(main_frame, text="Minimum Cost ($):*").grid(
            row=2, column=0, sticky="w", pady=5
        )
        min_cost_entry = ttk.Entry(
            main_frame,
            textvariable=self.min_cost,
            width=30
        )
        min_cost_entry.grid(row=2, column=1, sticky="ew", pady=5)

        ttk.Label(
            main_frame,
            text="(Only report items >= this amount)",
            font=("Arial", 9),
            foreground="gray"
        ).grid(row=2, column=2, sticky="w", padx=5)

        # Days Lookback
        ttk.Label(main_frame, text="Days Lookback:*").grid(
            row=3, column=0, sticky="w", pady=5
        )
        days_lookback_entry = ttk.Entry(
            main_frame,
            textvariable=self.days_lookback,
            width=30
        )
        days_lookback_entry.grid(row=3, column=1, sticky="ew", pady=5)

        ttk.Label(
            main_frame,
            text="(How many days back to include purchases)",
            font=("Arial", 9),
            foreground="gray"
        ).grid(row=3, column=2, sticky="w", padx=5)

        # Include ISI Serials Checkbox
        ttk.Label(main_frame, text="Include ISI Serials:").grid(
            row=4, column=0, sticky="w", pady=5
        )
        isi_checkbox = ttk.Checkbutton(
            main_frame,
            text="Include items with ISI serial numbers",
            variable=self.include_isi_serials
        )
        isi_checkbox.grid(row=4, column=1, sticky="w", pady=5)

        ttk.Label(
            main_frame,
            text="(ISI = in-store inventory)",
            font=("Arial", 9),
            foreground="gray"
        ).grid(row=4, column=2, sticky="w", padx=5)

        # CAPPS Client ID
        ttk.Label(main_frame, text="CAPPS Client ID:*").grid(
            row=5, column=0, sticky="w", pady=5
        )
        capss_client_id_entry = ttk.Entry(
            main_frame,
            textvariable=self.capss_client_id,
            width=30
        )
        capss_client_id_entry.grid(row=5, column=1, sticky="ew", pady=5)

        # CAPPS Client Secret
        ttk.Label(main_frame, text="CAPPS Client Secret:*").grid(
            row=6, column=0, sticky="w", pady=5
        )
        capss_client_secret_entry = ttk.Entry(
            main_frame,
            textvariable=self.capss_client_secret,
            width=30
        )
        capss_client_secret_entry.grid(row=6, column=1, sticky="ew", pady=5)

        # API Provider and Key
        ttk.Label(main_frame, text="API Provider:").grid(
            row=7, column=0, sticky="w", pady=5
        )

        provider_frame = ttk.Frame(main_frame)
        provider_frame.grid(row=7, column=1, sticky="ew", pady=5)
        
        provider_combo = ttk.Combobox(
            provider_frame,
            textvariable=self.api_provider,
            values=["groq", "gemini", "none"],
            state="readonly",
            width=15
        )
        provider_combo.pack(side="left", padx=(0, 10))
        provider_combo.bind("<<ComboboxSelected>>", self.on_provider_change)
        
        ttk.Label(
            provider_frame,
            text="(Groq and Gemini are FREE)",
            font=("Arial", 9),
            foreground="green"
        ).pack(side="left")
        
        # API Key
        ttk.Label(main_frame, text="API Key:").grid(
            row=8, column=0, sticky="w", pady=5
        )

        api_frame = ttk.Frame(main_frame)
        api_frame.grid(row=8, column=1, sticky="ew", pady=5)
        
        self.api_key_entry = ttk.Entry(
            api_frame,
            textvariable=self.api_key,
            show="*"
        )
        self.api_key_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.show_api_key_var = tk.BooleanVar(value=False)
        show_btn = ttk.Checkbutton(
            api_frame,
            text="Show",
            variable=self.show_api_key_var,
            command=self.toggle_api_key_visibility
        )
        show_btn.pack(side="right")
        
        self.api_help_label = ttk.Label(
            main_frame,
            text="Get free key at: console.groq.com",
            font=("Arial", 9),
            foreground="blue",
            cursor="hand2"
        )
        self.api_help_label.grid(row=8, column=2, sticky="w", padx=5)
        self.api_help_label.bind("<Button-1>", self.open_api_link)

        # Separator
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=9, column=0, columnspan=3, sticky="ew", pady=20
        )

        # File selection header
        file_header = ttk.Label(
            main_frame,
            text="AIMsi Export Files:",
            font=("Arial", 11, "bold")
        )
        file_header.grid(row=10, column=0, columnspan=3, sticky="w", pady=(0, 10))
        
        # Purchases File Selection
        ttk.Label(main_frame, text="Purchases CSV:*").grid(
            row=11, column=0, sticky="w", pady=5
        )

        purchases_frame = ttk.Frame(main_frame)
        purchases_frame.grid(row=11, column=1, columnspan=2, sticky="ew", pady=5)
        
        purchases_entry = ttk.Entry(
            purchases_frame,
            textvariable=self.purchases_file_path
        )
        purchases_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ttk.Button(
            purchases_frame,
            text="Browse...",
            command=self.select_purchases_file,
            width=10
        ).pack(side="right")
        
        # Serials File Selection
        ttk.Label(main_frame, text="Serials CSV:*").grid(
            row=12, column=0, sticky="w", pady=5
        )

        serials_frame = ttk.Frame(main_frame)
        serials_frame.grid(row=12, column=1, columnspan=2, sticky="ew", pady=5)
        
        serials_entry = ttk.Entry(
            serials_frame,
            textvariable=self.serials_file_path
        )
        serials_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ttk.Button(
            serials_frame,
            text="Browse...",
            command=self.select_serials_file,
            width=10
        ).pack(side="right")
        
        ttk.Label(
            main_frame,
            text="(e.g., LUCASSERIALS.CSV)",
            font=("Arial", 9),
            foreground="gray"
        ).grid(row=12, column=2, sticky="w", padx=5)

        # Configure column weights for resizing
        main_frame.columnconfigure(1, weight=1)

        # Convert Button
        convert_frame = ttk.Frame(main_frame)
        convert_frame.grid(row=13, column=0, columnspan=3, pady=20)

        self.convert_button = ttk.Button(
            convert_frame,
            text="Convert to XML",
            command=self.convert_files,
            style="Accent.TButton",
            width=20
        )
        self.convert_button.pack()
        
        # Status label
        self.status_label = ttk.Label(
            main_frame,
            text="Ready to convert",
            font=("Arial", 10)
        )
        self.status_label.grid(row=14, column=0, columnspan=3)

        # Info section
        info_frame = ttk.LabelFrame(
            main_frame,
            text="Quick Guide",
            padding="10"
        )
        info_frame.grid(row=15, column=0, columnspan=3, sticky="nsew", pady=10)
        
        info_text = tk.Text(
            info_frame,
            height=12,
            width=70,
            wrap="word",
            font=("Arial", 9),
            background="#f5f5f5",
            relief="flat"
        )
        info_text.pack(fill="both", expand=True)
        
        info_content = """How to use:

1. Export PURCHASES report from AIMsi:
   • Must include: invoice#, date, description, serial, cost
   • Export as CSV file

2. Export SERIALS report:
   • Export serial numbers with descriptions
   • Must include serial number and description columns

3. Configure filters:
   • Set minimum cost threshold (default $100)
   • Set days lookback period (default 5 days)
   • Choose whether to include ISI serials (default: exclude)

4. Convert:
   • Select both CSV files above
   • Click "Convert to XML"
   • Choose to inspect file first or upload directly

Notes:
• Customer data will be "on file" per SB 1317
• Brands extracted automatically from descriptions
• FREE API keys improve brand detection accuracy
• All settings are saved automatically!"""
        
        info_text.insert("1.0", info_content)
        info_text.config(state="disabled")

        # Log display section
        log_frame = ttk.LabelFrame(
            main_frame,
            text="Conversion Log",
            padding="10"
        )
        log_frame.grid(row=16, column=0, columnspan=3, sticky="nsew", pady=10)

        # Make log frame expandable
        main_frame.rowconfigure(16, weight=1)

        # Create ScrolledText widget for logs
        self.log_text = ScrolledText(
            log_frame,
            height=12,
            width=80,
            wrap="word",
            font=("Consolas", 9),  # Monospace font for logs
            background="#1e1e1e",  # Dark background
            foreground="#d4d4d4",  # Light text
            relief="flat",
            state="disabled"  # Read-only initially
        )
        self.log_text.pack(fill="both", expand=True)

        # Configure tag for stderr (errors)
        self.log_text.tag_config("stderr", foreground="#f48771")

        # Create clear button
        clear_frame = ttk.Frame(log_frame)
        clear_frame.pack(fill="x", pady=(5, 0))

        ttk.Button(
            clear_frame,
            text="Clear Log",
            command=self.clear_log,
            width=12
        ).pack(side="right")

    def toggle_api_key_visibility(self):
        """Toggle visibility of API key field"""
        if self.show_api_key_var.get():
            self.api_key_entry.config(show="")
        else:
            self.api_key_entry.config(show="*")
    
    def on_provider_change(self, event=None):
        """Update help text when provider changes"""
        provider = self.api_provider.get()
        if provider == "groq":
            self.api_help_label.config(text="Get free key at: console.groq.com")
        elif provider == "gemini":
            self.api_help_label.config(text="Get free key at: makersuite.google.com/app/apikey")
        else:
            self.api_help_label.config(text="Pattern matching only (no API needed)")
    
    def open_api_link(self, event=None):
        """Open the API provider's website"""
        provider = self.api_provider.get()
        if provider == "groq":
            webbrowser.open("https://console.groq.com")
        elif provider == "gemini":
            webbrowser.open("https://makersuite.google.com/app/apikey")

    def setup_logging(self):
        """Redirect stdout and stderr to GUI log widget"""
        # Create redirectors
        self.stdout_redirector = TextRedirector(self.log_text, tag="stdout")
        self.stderr_redirector = TextRedirector(self.log_text, tag="stderr")

        # Save original stdout/stderr for restoration
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        # Redirect
        sys.stdout = self.stdout_redirector
        sys.stderr = self.stderr_redirector

        # Add initial message
        print("CAPPS Converter initialized. Ready to process files.")

    def clear_log(self):
        """Clear the log display"""
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

    def on_closing(self):
        """Clean up before closing"""
        # Restore original stdout/stderr
        if hasattr(self, 'original_stdout'):
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr

        # Unbind mousewheel
        try:
            self.root.unbind_all("<MouseWheel>")
        except:
            pass

        self.root.destroy()

    def select_purchases_file(self):
        """Open file dialog to select purchases CSV file"""
        filename = filedialog.askopenfilename(
            title="Select AIMsi Purchases Export",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.purchases_file_path.set(filename)
    
    def select_serials_file(self):
        """Open file dialog to select serials CSV file"""
        filename = filedialog.askopenfilename(
            title="Select AIMsi Serials Export (e.g., LUCASSERIALS.CSV)",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.serials_file_path.set(filename)

    def show_post_conversion_dialog(self, xml_path):
        """
        Show dialog asking user to inspect file or upload immediately

        Args:
            xml_path: Path to the generated XML file

        Returns:
            "inspect" or "upload" or None
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Conversion Complete")
        dialog.geometry("500x180")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        result = {"choice": None}

        # Content
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill="both", expand=True)

        # Success message
        ttk.Label(
            frame,
            text="XML file created successfully!",
            font=("Arial", 12, "bold"),
            foreground="green"
        ).pack(pady=(0, 10))

        # File path
        ttk.Label(
            frame,
            text=f"File: {os.path.basename(xml_path)}",
            font=("Arial", 9)
        ).pack(pady=(0, 20))

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)

        def on_inspect():
            result["choice"] = "inspect"
            dialog.destroy()

        def on_upload():
            result["choice"] = "upload"
            dialog.destroy()

        ttk.Button(
            button_frame,
            text="Inspect File",
            command=on_inspect,
            width=15
        ).pack(side="left", padx=5)

        ttk.Button(
            button_frame,
            text="Upload Now",
            command=on_upload,
            width=15,
            style="Accent.TButton"
        ).pack(side="left", padx=5)

        # Wait for dialog to close
        dialog.wait_window()

        return result["choice"]

    def inspect_and_upload(self, xml_path):
        """
        Open XML file for inspection, then offer upload option

        Args:
            xml_path: Path to the XML file
        """
        # Open the file in default application
        try:
            if sys.platform == "win32":
                os.startfile(xml_path)
            elif sys.platform == "darwin":
                os.system(f'open "{xml_path}"')
            else:
                os.system(f'xdg-open "{xml_path}"')
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Could not open file:\n{e}"
            )
            return

        # Ask if user wants to upload after inspection
        upload_now = messagebox.askyesno(
            "Upload to CAPSS?",
            "Would you like to upload the file to CAPSS now?"
        )

        if upload_now:
            self.upload_to_capss_gui(xml_path)

    def upload_to_capss_gui(self, xml_path):
        """
        Upload XML file to CAPSS with progress indication

        Args:
            xml_path: Path to the XML file to upload
        """
        # Validate credentials
        if not self.capss_client_id.get() or not self.capss_client_secret.get():
            messagebox.showerror(
                "Missing Credentials",
                "CAPPS Client ID and Secret are required for upload.\n\n"
                "Please fill in these fields and try again."
            )
            return

        # Disable convert button during upload
        self.convert_button.config(state="disabled", text="Uploading...")
        self.status_label.config(text="Uploading to CAPSS...", foreground="blue")

        # Run upload in background thread
        self.upload_thread = threading.Thread(
            target=self.run_upload_thread,
            args=(xml_path,),
            daemon=True
        )
        self.upload_thread.start()

        # Monitor thread
        self.check_upload_status()

    def run_upload_thread(self, xml_path):
        """Run upload in background thread"""
        try:
            converter = CAPPSConverter(self.license_number.get())
            success = converter.upload_to_capss(
                xml_path,
                self.capss_client_id.get(),
                self.capss_client_secret.get()
            )
            self.upload_result = {"success": success}
        except Exception as e:
            self.upload_result = {"success": False, "error": str(e)}

    def check_upload_status(self):
        """Check if upload thread is done"""
        if self.upload_thread and self.upload_thread.is_alive():
            self.root.after(100, self.check_upload_status)
        else:
            self.on_upload_complete()

    def on_upload_complete(self):
        """Handle upload completion"""
        # Re-enable button
        self.convert_button.config(state="normal", text="Convert to XML")

        result = getattr(self, 'upload_result', None)

        if result and result.get("success"):
            self.status_label.config(text="Upload successful!", foreground="green")
            messagebox.showinfo("Success", "File uploaded to CAPSS successfully!")
        else:
            error = result.get("error", "Upload failed") if result else "Upload failed"
            self.status_label.config(text="Upload failed", foreground="red")
            messagebox.showerror("Upload Failed", f"Failed to upload file to CAPSS.\n\n{error}")

        self.upload_result = None

    def convert_files(self):
        """Convert the CSV files to XML"""
        # Validate inputs
        if not self.license_number.get():
            messagebox.showerror("Error", "Please enter your license number")
            return
        
        if not self.employee_name.get():
            messagebox.showerror("Error", "Please enter the employee name")
            return
        
        if not self.purchases_file_path.get():
            messagebox.showerror("Error", "Please select the purchases CSV file")
            return
        
        if not self.serials_file_path.get():
            messagebox.showerror("Error", "Please select the serials CSV file")
            return

        # Check if files exist
        if not os.path.exists(self.purchases_file_path.get()):
            messagebox.showerror("Error", "Purchases file not found")
            return
        
        if not os.path.exists(self.serials_file_path.get()):
            messagebox.showerror("Error", "Serials file not found")
            return
        
        # Validate and parse minimum cost
        try:
            min_cost_value = float(self.min_cost.get())
            if min_cost_value < 0:
                messagebox.showerror("Error", "Minimum cost must be a positive number")
                return
        except ValueError:
            messagebox.showerror("Error", "Minimum cost must be a valid number")
            return

        # Validate and parse days lookback
        try:
            days_lookback_value = int(self.days_lookback.get())
            if days_lookback_value < 1:
                messagebox.showerror("Error", "Days lookback must be at least 1")
                return
        except ValueError:
            messagebox.showerror("Error", "Days lookback must be a valid whole number")
            return

        # Disable convert button to prevent double-clicks
        self.convert_button.config(state="disabled", text="Converting...")
        self.status_label.config(text="Converting...", foreground="blue")

        # Run conversion in background thread
        self.conversion_thread = threading.Thread(
            target=self.run_conversion_thread,
            args=(min_cost_value, days_lookback_value),
            daemon=True
        )
        self.conversion_thread.start()

        # Monitor thread completion
        self.check_conversion_status()

    def run_conversion_thread(self, min_cost_value, days_lookback_value):
        """Run conversion in background thread (called by threading.Thread)"""
        try:
            # Create converter and process
            api_key = self.api_key.get() if self.api_provider.get() != "none" else None
            converter = CAPPSConverter(
                self.license_number.get(),
                api_key,
                self.api_provider.get() if self.api_provider.get() != "none" else "groq",
                min_cost_value,
                days_lookback_value,
                self.include_isi_serials.get()
            )

            # Convert and get XML path (this is what takes time)
            xml_path = converter.convert_aimsi_to_xml(
                self.purchases_file_path.get(),
                self.serials_file_path.get(),
                self.employee_name.get()
            )

            # Store result for main thread to pick up
            self.conversion_result = {"success": True, "xml_path": xml_path}

        except Exception as e:
            # Store error for main thread
            self.conversion_result = {"success": False, "error": str(e)}

    def check_conversion_status(self):
        """Check if conversion thread is done (runs on main thread via after())"""
        if self.conversion_thread and self.conversion_thread.is_alive():
            # Still running, check again in 100ms
            self.root.after(100, self.check_conversion_status)
        else:
            # Thread finished, handle results
            self.on_conversion_complete()

    def on_conversion_complete(self):
        """Handle conversion completion (runs on main thread)"""
        # Re-enable button
        self.convert_button.config(state="normal", text="Convert to XML")

        # Check result
        result = getattr(self, 'conversion_result', None)

        if result and result.get("success"):
            xml_path = result["xml_path"]
            self.status_label.config(
                text="Conversion successful!",
                foreground="green"
            )

            # Show post-conversion dialog
            choice = self.show_post_conversion_dialog(xml_path)

            if choice == "inspect":
                self.inspect_and_upload(xml_path)
            elif choice == "upload":
                self.upload_to_capss_gui(xml_path)
        else:
            error = result.get("error", "Unknown error") if result else "Unknown error"
            self.status_label.config(
                text="Conversion failed",
                foreground="red"
            )
            messagebox.showerror(
                "Conversion Error",
                f"An error occurred during conversion:\n\n{error}"
            )

        # Clear result
        self.conversion_result = None

    def save_settings(self):
        """Save settings immediately (called automatically on changes)"""
        settings_file = Path.home() / ".capps_converter_settings.json"
        try:
            settings = {
                "license": self.license_number.get(),
                "employee": self.employee_name.get(),
                "min_cost": self.min_cost.get(),
                "days_lookback": self.days_lookback.get(),
                "include_isi_serials": self.include_isi_serials.get(),
                "capss_client_id": self.capss_client_id.get(),
                "capss_client_secret": self.capss_client_secret.get(),
                "provider": self.api_provider.get(),
                "api_key": self.api_key.get(),
                "purchases_file": self.purchases_file_path.get(),
                "serials_file": self.serials_file_path.get()
            }
            
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            # Silently ignore save errors to not interrupt user workflow
            pass
    
    def load_settings(self):
        """Load saved settings from file"""
        settings_file = Path.home() / ".capps_converter_settings.json"
        
        # Try to load from JSON file first (new format)
        try:
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    
                self.license_number.set(settings.get("license", ""))
                self.employee_name.set(settings.get("employee", "Store Employee"))
                self.min_cost.set(settings.get("min_cost", "100"))
                self.days_lookback.set(settings.get("days_lookback", "5"))
                self.include_isi_serials.set(settings.get("include_isi_serials", False))
                self.capss_client_id.set(settings.get("capss_client_id", ""))
                self.capss_client_secret.set(settings.get("capss_client_secret", ""))
                self.api_provider.set(settings.get("provider", "groq"))
                self.api_key.set(settings.get("api_key", ""))
                self.purchases_file_path.set(settings.get("purchases_file", ""))
                self.serials_file_path.set(settings.get("serials_file", ""))
                return
        except Exception as e:
            pass
        
        # Fallback: Try to load from old text file format
        old_settings_file = Path.home() / ".capps_converter_settings.txt"
        try:
            if old_settings_file.exists():
                with open(old_settings_file, 'r') as f:
                    for line in f:
                        if line.startswith("license="):
                            self.license_number.set(line.split("=", 1)[1].strip())
                        elif line.startswith("employee="):
                            self.employee_name.set(line.split("=", 1)[1].strip())
                        elif line.startswith("provider="):
                            self.api_provider.set(line.split("=", 1)[1].strip())
                        elif line.startswith("api_key="):
                            self.api_key.set(line.split("=", 1)[1].strip())
                
                # Migrate to new format
                self.save_settings()
                # Delete old file
                old_settings_file.unlink()
        except Exception as e:
            pass

def main():
    """Main entry point for GUI application"""
    root = tk.Tk()

    # Set style
    style = ttk.Style()
    style.theme_use('clam')

    # Create custom button style
    style.configure(
        "Accent.TButton",
        background="#0066cc",
        foreground="white",
        borderwidth=0,
        focuscolor="none",
        padding=10
    )
    style.map(
        "Accent.TButton",
        background=[("active", "#0052a3")]
    )

    # Create and run application
    app = CAPPSConverterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()