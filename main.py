import sqlite3
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox, Text, VERTICAL, END, NO, W, CENTER, Toplevel, DISABLED, NORMAL, NW, E, LEFT, RIGHT, Y, BOTH, EW, WORD, filedialog
from datetime import datetime
import os
import shutil
import math
import re

# ReportLab Imports for PDF Generation
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib import colors

class ReportLabTemplate(SimpleDocTemplate):
    """Custom ReportLab document template to add hospital-style header and footer to every page."""
    
    def __init__(self, filename, **kw):
        # --- 1. Extract and store custom attributes for the header ---
        self.DOCTOR_NAME = kw.pop('DOCTOR_NAME', '')
        self.DOCTOR_DEGREE = kw.pop('DOCTOR_DEGREE', '')
        self.CLINIC_NAME = kw.pop('CLINIC_NAME', '')
        self.DOCTOR_REG_NO = kw.pop('DOCTOR_REG_NO', '')
        self.ADDRESS_LINE1 = kw.pop('ADDRESS_LINE1', '')
        self.CONTACT_INFO = kw.pop('CONTACT_INFO', '')

        # --- 2. Define/Retrieve Document Settings ---
        # Increased top margin for separation from clinic header.
        top_margin = kw.pop('topMargin', 1.5 * inch)  
        left_margin = kw.pop('leftMargin', 0.75 * inch)
        right_margin = kw.pop('rightMargin', 0.75 * inch)
        bottom_margin = kw.pop('bottomMargin', 0.4 * inch)
        
        # --- 3. Initialize Parent Class (SimpleDocTemplate) ---
        super().__init__(filename, 
                              topMargin=top_margin, 
                              leftMargin=left_margin, 
                              rightMargin=right_margin,
                              bottomMargin=bottom_margin,
                              **kw) 
                              
        self.doc_style = getSampleStyleSheet()

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        
        # --- Header Content (Attributes are retrieved from the 'doc' object) ---
        doc_name = doc.DOCTOR_NAME
        doc_degree = doc.DOCTOR_DEGREE
        clinic_name = doc.CLINIC_NAME
        reg_no = doc.DOCTOR_REG_NO
        address = doc.ADDRESS_LINE1
        contact = doc.CONTACT_INFO

        # Define styles for the header
        styles = getSampleStyleSheet()
        
        # Clinic Name (Size 20, Red)
        clinic_style = ParagraphStyle('ClinicNameStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=20, textColor=colors.red, alignment=TA_CENTER)

        # Doctor Name (Size 10, Navy, Centered)
        doc_name_style = ParagraphStyle('DocNameStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.navy, alignment=TA_CENTER)

        # Info (Size 8.5)
        info_style_left = ParagraphStyle('InfoStyleLeft', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.black, alignment=TA_LEFT)
        info_style_right = ParagraphStyle('InfoStyleRight', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.black, alignment=TA_RIGHT)
        
        # Create a table for the header layout 
        header_data = [
            # Row 0: Clinic Name (Spanned)
            [
                Paragraph(f"<font size='20'><b>{clinic_name.upper()}</b></font>", clinic_style), 
            ],
            # Row 1: Doctor Name (Spanned)
            [
                Paragraph(f"<b>{doc_name}</b>, {doc_degree}", doc_name_style),
            ],
            # Row 2: Address Left, Reg No Right
            [
                Paragraph(address, info_style_left),
                Paragraph(reg_no, info_style_right),
            ],
            # Row 3: Contact Left, Empty Right
            [
                Paragraph(contact, info_style_left),
                Paragraph("", info_style_right), # Empty cell for balance
            ]
        ]
        
        # Calculate available width 
        table_width = doc.width
        
        # Adjusted table to be 2 columns for address/contact split, 1 column for name/clinic
        header_table = Table(header_data, colWidths=[table_width/2, table_width/2])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('SPAN', (0, 0), (1, 0)), # Span Clinic Name
            ('SPAN', (0, 1), (1, 1)), # Span Doctor Name/Degree
            
            # Increased padding below Clinic Name (Row 0)
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12), 
            ('TOPPADDING', (0, 0), (-1, 0), 1),
            
            # Keep padding below Doctor Name (Row 1) the same
            ('BOTTOMPADDING', (0, 1), (-1, 1), 5), 
            ('TOPPADDING', (0, 1), (-1, 1), 1),
            
            # Keep padding for address/contact minimal
            ('BOTTOMPADDING', (0, 2), (-1, -1), 0),
            ('TOPPADDING', (0, 2), (-1, -1), 0),
        ]))
        
        # --- DYNAMIC POSITIONING ---
        
        # 1. Calculate the actual height of the table.
        w, h = header_table.wrapOn(canvas, doc.width, doc.topMargin)
        
        # 2. Define the target top clearance from the absolute top of the page.
        target_top_clearance = 25 
        
        # 3. Calculate the drawing position (Y) based on table height.
        y_draw = letter[1] - target_top_clearance - h
        
        # 4. Draw the table using the calculated position.
        header_table.drawOn(canvas, doc.leftMargin, y_draw) 

        # --- Divider Line (Teal Color) ---
        # The line must be positioned immediately below the table.
        line_y = y_draw - 5 
        
        canvas.setStrokeColor(colors.Color(0, 0.5, 0.5)) # Teal/Info color approximation
        canvas.setLineWidth(1.5)
        canvas.line(doc.leftMargin, line_y, doc.leftMargin + doc.width, line_y)


        # --- Footer Content (Page Number) ---
        footer_text = f"Page {canvas.getPageNumber()}"
        
        canvas.setFont('Helvetica-Oblique', 8)
        canvas.drawCentredString(letter[0] / 2, doc.bottomMargin / 2, footer_text)

        canvas.restoreState()

    def build(self, flowables, onFirstPage=_header_footer, onLaterPages=_header_footer):
        super().build(flowables, onFirstPage=self._header_footer, onLaterPages=self._header_footer)


class PatientManagerApp:
    def __init__(self, master):
        self.master = master
        
        master.title("Shradha Homoeo Clinic")
        master.geometry("1200x850") 

        # ⭐️ CONSTANT FOR PADDING SIZE (5 digits covers 00001 to 99999) ⭐️
        self.CASE_NO_PADDING_SIZE = 5 
        
        # ⭐️ CLINIC AND DOCTOR DETAILS FOR PDF HEADER ⭐️
        self.CLINIC_NAME = "Shradha Homoeo Clinic"
        self.DOCTOR_NAME = "Dr. Ramesh Ramrao Mustare" 
        self.DOCTOR_DEGREE = "D.H.M.S., C.C.M.P.(C.C.H.)" 
        self.DOCTOR_REG_NO = "Reg. No: 20702" 
        self.ADDRESS_LINE1 = "Kamtha(BK), Tq Ardhapur, Dist Nanded, 431704"
        self.CONTACT_INFO = "Contact: +91 9420911808 "
        
        # Database and Backup constants
        self.DB_NAME = "patients.db"
        self.BACKUP_FOLDER = "db_backups" 
        self.RECORDS_PER_PAGE = 30 

        # Pagination variables
        self.current_page = 1
        self.total_records = 0
        self.total_pages = 1
        
        # --- Style Configuration ---
        self.DEFAULT_FONT = ("Helvetica", 12)
        self.BOLD_FONT = ("Helvetica", 12, "bold")
        self.TITLE_FONT = ("Helvetica", 18, "bold")
        self.LARGE_TITLE_FONT = ("Helvetica", 48, "bold")
        
        # ⭐ HIGHLIGHT STYLES - Conceptually uses Primary/Navy Blue ⭐
        master.style.configure("Highlight.TLabel", 
                               foreground=master.style.colors.get("primary"), 
                               font=("Helvetica", 12, "bold", "underline"))
        
        self.default_label_fg = master.style.lookup("TLabel", "foreground")
        
        master.style.configure("Disabled.TNotebook.Tab", 
                               foreground=master.style.colors.get("success"), 
                               font=("Helvetica", 14, "bold"))
        
        master.style.map("Disabled.TNotebook.Tab", 
                         background=[('selected', master.style.colors.get("light")), ('!selected', master.style.colors.get("light"))], 
                         foreground=[('selected', master.style.colors.get("success")), ('!selected', master.style.colors.get("success"))])
        
        master.style.configure("TButton", font=("Helvetica", 14)) 
        self.master.style.configure("TLabel", font=self.DEFAULT_FONT)
        master.style.configure("TNotebook.Tab", font=("Helvetica", 14, "bold")) 
        master.style.configure("Treeview.Heading", font=self.BOLD_FONT)
        master.style.configure("Treeview", font=self.DEFAULT_FONT, rowheight=28) 
        master.style.configure("HomeTitle.TLabel", font=self.LARGE_TITLE_FONT)

        # --- Database Initialization ---
        self.init_db()
        self.backup_database(silent=True)
        
        # --- Frames/Widgets ---
        self.home_frame = tb.Frame(master)
        self.add_frame = tb.Frame(master)
        self.search_frame = tb.Frame(master)
        self.view_all_frame = tb.Frame(master) 
        
        self.intake_canvas = None
        self.followup_canvas = None

        self.current_patient_id = None
        self.entries = {}
        self.followup_entries = {}
        
        self.widget_label_map = {}
        
        # ⭐ MANUAL FOCUS LISTS ⭐
        self.intake_widgets = []
        self.followup_widgets = []
        
        # --- Setup Pages ---
        self.home_page()
        self.add_page()
        self.search_page()
        self.view_all_page() 
        
        # ⭐ NEW: Bind the Esc key to the navigation function ⭐
        master.bind('<Escape>', self.handle_escape)

        self.show_frame(self.home_frame)

    # ==================== Highlighting Utility ====================
    
    def apply_highlight(self, event):
        """Highlights the active widget and its associated label."""
        widget = event.widget
        
        # 1. Highlight the Widget itself (Input box)
        if isinstance(widget, Text):
            widget.config(bg=self.master.style.colors.get("light")) 
        elif isinstance(widget, tb.Entry) or isinstance(widget, tb.Combobox):
            try:
                widget.config(background=self.master.style.colors.get("light"))
            except Exception:
                pass
            
        # 2. Highlight the Label (Heading)
        if widget in self.widget_label_map:
            label = self.widget_label_map[widget]
            label.config(style="Highlight.TLabel")

    def remove_highlight(self, event):
        """Removes highlight from the widget and its associated label."""
        widget = event.widget
        
        # 1. Remove highlight from the Widget itself
        if isinstance(widget, Text):
            widget.config(bg="white")
        elif isinstance(widget, tb.Entry) or isinstance(widget, tb.Combobox):
            try:
                widget.config(background="white")
            except Exception:
                pass

        # 2. Remove highlight from the Label (Heading)
        if widget in self.widget_label_map:
            label = self.widget_label_map[widget]
            label.config(style="TLabel", font=self.BOLD_FONT)
            
    # ==================== UI Navigation & Scroll Fix ====================
    
    # ⭐ NEW: Handle Escape Key for Navigation ⭐
    def handle_escape(self, event):
        """Navigates back to the home frame when the Esc key is pressed."""
        
        # Determine the currently visible frame and switch back to home.
        if self.add_frame.winfo_ismapped() or self.search_frame.winfo_ismapped() or self.view_all_frame.winfo_ismapped():
            self.show_frame(self.home_frame)
            return "break"
            
    # ⭐ NEW: Handle Arrow Keys for Home Page Buttons ⭐
    def navigate_home_buttons(self, event):
        """Allows arrow key navigation between the main buttons on the home page."""
        buttons = [
            self.home_frame.winfo_children()[1],  # Add New Patient
            self.home_frame.winfo_children()[2],  # Search Patient
            self.home_frame.winfo_children()[3]   # View All Records
        ]
        current_widget = self.master.focus_get()

        try:
            current_index = buttons.index(current_widget)
        except ValueError:
            # If focus is lost or on the title, move to the first button
            buttons[0].focus_set()
            return "break"

        next_index = current_index
        # Only check for Up/Down keys
        if event.keysym in ('Down'):
            next_index = (current_index + 1) % len(buttons)
        elif event.keysym in ('Up'):
            next_index = (current_index - 1 + len(buttons)) % len(buttons)
        else:
            return # Allow default Tab behavior

        buttons[next_index].focus_set()
        return "break"
        
    def scroll_to_widget(self, widget, canvas):
        """Scrolls the canvas to ensure the given widget is visible, prioritizing an upper-half view."""
        if canvas != self.intake_canvas:
            return
            
        canvas.update_idletasks()
        
        if isinstance(widget, tb.Entry) or isinstance(widget, tb.Combobox) or isinstance(widget, tb.Button):
            scrollable_frame = widget.master
            total_widget_y = widget.winfo_y()
            widget_height = widget.winfo_height()
        else:
            scrollable_frame = widget.master.master 
            container_y = widget.master.winfo_y()
            total_widget_y = container_y
            widget_height = widget.master.winfo_height() 

        content_height = scrollable_frame.winfo_reqheight()
        current_scroll = canvas.canvasy(0)
        canvas_height = canvas.winfo_height()
        
        padding = 20
        target_y_offset = canvas_height * 0.20 
        
        widget_top = total_widget_y
        widget_bottom = total_widget_y + widget_height
        
        visible_top = current_scroll
        
        target_scroll = max(0, widget_top - target_y_offset)

        if widget_top < visible_top + target_y_offset:
            canvas.yview_moveto(target_scroll / content_height)
        
        elif widget_bottom > current_scroll + canvas_height - padding:
            bottom_aligned_scroll = widget_bottom - canvas_height + padding
            final_scroll = max(target_scroll, bottom_aligned_scroll)
            canvas.yview_moveto(min(1.0, max(0, final_scroll / content_height)))

    def bind_mouse_scroll(self, canvas, scrollable_frame):
        """Binds mouse wheel events to the canvas for scrolling."""
        
        def _on_mousewheel(event):
            if event.delta: 
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            elif event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        scrollable_frame.bind('<Enter>', lambda e: self._bind_all_scroll(canvas, _on_mousewheel))
        scrollable_frame.bind('<Leave>', lambda e: self._unbind_all_scroll(canvas))
        
        scrollable_frame.bind('<Button-1>', lambda e: scrollable_frame.focus_set())

    def _bind_all_scroll(self, canvas, handler):
        canvas.bind_all('<MouseWheel>', handler)
        canvas.bind_all('<Button-4>', handler)
        canvas.bind_all('<Button-5>', handler)

    def _unbind_all_scroll(self, canvas):
        canvas.unbind_all('<MouseWheel>')
        canvas.unbind_all('<Button-4>')
        canvas.unbind_all('<Button-5>')

    def navigate_treeview(self, event):
        """Allows Tab/Shift-Tab and Arrow Keys to cycle through Treeview rows."""
        tree = event.widget
        current_item = tree.focus()
        
        # If no item is focused but there are children, focus the first one
        if not current_item and tree.get_children():
            first_child = tree.get_children()[0]
            tree.focus(first_child)
            tree.selection_set(first_child)
            return "break"

        children = tree.get_children()
        if not children:
            return "break"

        try:
            current_index = children.index(current_item)
        except ValueError:
            # Should not happen if current_item is valid
            tree.focus(children[0])
            tree.selection_set(children[0])
            return "break"

        # Determine the direction based on key press
        next_index = current_index
        if event.keysym in ('Tab', 'Down'):
            next_index = (current_index + 1) % len(children)
        elif event.keysym in ('ISO_Left_Tab', 'Up') or (event.state & 0x1 and event.keysym == 'Tab'):
            next_index = (current_index - 1 + len(children)) % len(children)
        else:
            return # Let other keys (like Enter) proceed naturally

        next_item = children[next_index]
        tree.focus(next_item)
        tree.selection_set(next_item)
        
        tree.see(next_item)
        
        return "break" 

    def force_tab_focus(self, event):
        """
        Forces focus to move using the predetermined widget list and scrolls the view.
        """
        widget = event.widget
        
        if widget in self.intake_widgets:
            focus_list = self.intake_widgets
            canvas = self.intake_canvas
        elif widget in self.followup_widgets:
            focus_list = self.followup_widgets
            canvas = self.followup_canvas
        else:
            if event.state & 0x1:
                event.widget.tk_focusPrev()
            else:
                event.widget.tk_focusNext()
            return "break"

        try:
            current_index = focus_list.index(widget)
        except ValueError:
            return "break"

        if event.state & 0x1: # Shift-Tab (Previous)
            next_index = (current_index - 1 + len(focus_list)) % len(focus_list)
        else: # Tab (Next)
            next_index = (current_index + 1) % len(focus_list)

        next_widget = focus_list[next_index]
        next_widget.focus_set()
        
        if canvas == self.intake_canvas:
            self.scroll_to_widget(next_widget, canvas)
        
        return "break" 
    
    def bind_tab_to_widget(self, widget, focus_list):
        """Helper to bind Tab/Shift-Tab and add the widget to the tracking list."""
        widget.bind('<Key-Tab>', self.force_tab_focus)
        widget.bind('<Shift-Key-Tab>', self.force_tab_focus)
        # BIND HIGHLIGHTING
        widget.bind('<FocusIn>', self.apply_highlight)
        widget.bind('<FocusOut>', self.remove_highlight)
        
        focus_list.append(widget)


    # ==================== Database Functions ====================
    def init_db(self):
        if not os.path.exists(self.BACKUP_FOLDER):
            os.makedirs(self.BACKUP_FOLDER)
            
        conn = sqlite3.connect(self.DB_NAME)
        c = conn.cursor()
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT, case_no TEXT, name TEXT, age TEXT, address TEXT, gender TEXT,
                co TEXT, onset_duration TEXT,
                habit TEXT, diet TEXT, appetite TEXT, bowel TEXT,
                family_history TEXT, past_history TEXT,
                mind TEXT, sleep TEXT, desire TEXT, aversion TEXT,
                wt TEXT, bp TEXT, pulse TEXT, temp TEXT,
                systemic_exam TEXT, modalities_pe TEXT, diagnosis TEXT,
                treatment TEXT  
            )
        """)
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS visits (
                visit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                visit_date TEXT,
                complaints TEXT,
                new_modalities TEXT,
                treatment TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        """)
        
        try:
            # Check for old column name and rename if found
            c.execute("PRAGMA table_info(patients)")
            columns = [col[1] for col in c.fetchall()]
            if 'final_diagnosis' in columns:
                 c.execute("ALTER TABLE patients RENAME COLUMN final_diagnosis TO treatment")
        except sqlite3.OperationalError:
            pass # Ignore if rename fails (e.g., if column doesn't exist or already renamed)
            
        conn.commit()
        conn.close()

    def backup_database(self, silent=False):
        """Copies the main database file to a time-stamped backup file."""
        source_db = self.DB_NAME
        
        if not os.path.exists(source_db):
            if not silent:
                 messagebox.showerror("Backup Error", f"Database file '{source_db}' not found.")
            return

        if not os.path.exists(self.BACKUP_FOLDER):
            os.makedirs(self.BACKUP_FOLDER)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{self.BACKUP_FOLDER}/patients_backup_{timestamp}.db"
        
        try:
            shutil.copyfile(source_db, backup_file)
            
            backup_files = sorted([f for f in os.listdir(self.BACKUP_FOLDER) if f.startswith('patients_backup_') and f.endswith('.db')])
            if len(backup_files) > 10:
                for old_file in backup_files[:-10]: 
                     os.remove(os.path.join(self.BACKUP_FOLDER, old_file))

            if not silent:
                messagebox.showinfo("Backup Success", f"Database backed up to:\n{backup_file}")
            
        except Exception as e:
            messagebox.showerror("Backup Error", f"Failed to create database backup: {e}")
            
    def _get_text_widget_content(self, widget):
        content = widget.get("1.0", END).strip()
        return content
    
    # ⭐️ MODIFIED: Handles Zero-Padding of Case No for DB ⭐️
    def get_patient_data(self):
        data = []
        intake_keys = [
            'entry_date', 'entry_case_no', 'entry_name', 'entry_age', 'entry_address', 'combo_sex',
            'entry_co', 'entry_onset_duration',
            'entry_habit', 'entry_diet', 'entry_appetite', 'entry_bowel',
            'entry_family_history', 'entry_past_history',
            'entry_mind', 'entry_sleep', 'entry_desire', 'entry_aversion',
            'entry_wt', 'entry_bp', 'entry_pulse', 'entry_temp', 'entry_systemic_exam', 'entry_modalities_pe', 'entry_diagnosis',
            'entry_treatment'
        ]
        
        for key in intake_keys:
            widget = self.entries.get(key)
            if isinstance(widget, Text):
                content = self._get_text_widget_content(widget)
            elif widget:
                content = widget.get().strip()
            else:
                content = '' 

            # Apply Zero-Padding only to the case number
            if key == 'entry_case_no' and content:
                try:
                    # Strip any non-digit characters and convert to an integer, then zero-pad to 5 digits
                    numeric_part = re.sub(r'[^0-9]', '', content)
                    if numeric_part:
                        # Ensures '1' becomes '00001', '100' becomes '00100'
                        content = numeric_part.zfill(self.CASE_NO_PADDING_SIZE) 
                    else:
                         # If input was alphanumeric with no digits (e.g., 'TEST'), keep it as is.
                         pass 
                except Exception:
                    pass # Keep the content as is if processing fails

            data.append(content)
            
        return tuple(data)

    def get_followup_data(self):
        data = []
        followup_keys = [
            'fu_entry_date', 'fu_text_complaints', 'fu_text_new_modalities', 'fu_text_treatment'
        ]
        for key in followup_keys:
            widget = self.followup_entries.get(key)
            if isinstance(widget, Text):
                data.append(self._get_text_widget_content(widget))
            else:
                data.append(widget.get())
        return tuple(data)

    def validate_required_fields(self):
        # Validation checks the unpadded input from the UI
        if not self.entries.get('entry_name', tb.Entry()).get().strip() or \
           not self.entries.get('entry_case_no', tb.Entry()).get().strip():
            messagebox.showerror("Error", "Name and Case No are required fields for a new record!")
            return False
        return True

    def save_patient(self):
        if not self.validate_required_fields():
            return
        
        # Data is retrieved and padded inside get_patient_data
        data = self.get_patient_data() 
        
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute("""INSERT INTO patients (
                date, case_no, name, age, address, gender, co, onset_duration,
                habit, diet, appetite, bowel, family_history, past_history,
                mind, sleep, desire, aversion,
                wt, bp, pulse, temp, systemic_exam, modalities_pe, diagnosis,
                treatment
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", data)
            conn.commit()
            
            new_patient_id = c.lastrowid
            
            messagebox.showinfo("Success", f"New Patient record saved successfully! (ID: {new_patient_id})")
            
            self.edit_record(new_patient_id)
            self.notebook.select(self.tab_followup)
            
            self.backup_database(silent=True) 
            
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")
        finally:
            conn.close()

    def update_patient_intake(self):
        if not self.validate_required_fields():
            return
        
        if self.current_patient_id is None:
            messagebox.showerror("Error", "No patient selected for update.")
            return

        # Data is retrieved and padded inside get_patient_data
        data = self.get_patient_data()
        data_with_id = data + (self.current_patient_id,)

        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            
            columns = [
                'date', 'case_no', 'name', 'age', 'address', 'gender', 'co', 'onset_duration',
                'habit', 'diet', 'appetite', 'bowel', 'family_history', 'past_history',
                'mind', 'sleep', 'desire', 'aversion',
                'wt', 'bp', 'pulse', 'temp', 'systemic_exam', 'modalities_pe', 'diagnosis',
                'treatment'
            ]
            set_clause = ", ".join([f"{col} = ?" for col in columns])
            
            sql = f"UPDATE patients SET {set_clause} WHERE id = ?"
            
            c.execute(sql, data_with_id)
            conn.commit()
            messagebox.showinfo("Success", f"Patient Intake data (ID: {self.current_patient_id}) updated successfully!")
            
            self.backup_database(silent=True)
            
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")
        finally:
            conn.close()

    def save_followup(self):
        if self.current_patient_id is None:
            messagebox.showerror("Error", "Please save the patient's initial intake first.")
            return

        data = self.get_followup_data()
        
        if not data[0].strip() or not data[-1].strip():
            messagebox.showerror("Error", "Visit Date and Treatment are required for a follow-up record.")
            return

        data_with_id = (self.current_patient_id,) + data

        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute("""INSERT INTO visits (
                patient_id, visit_date, complaints, new_modalities, treatment
            ) VALUES (?, ?, ?, ?, ?)""", data_with_id)
            conn.commit()
            messagebox.showinfo("Success", "New Follow-up record saved successfully!")
            
            self.clear_followup_entries(clear_date=False)
            self.populate_visit_history()
            
            self.backup_database(silent=True)
            
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")
        finally:
            conn.close()
            
    def clear_entries(self):
        for name, widget in self.entries.items():
            if isinstance(widget, Text):
                widget.delete("1.0", END)
            else:
                widget.delete(0, END)
                if name == 'entry_date': 
                    widget.insert(0, datetime.today().strftime("%d-%m-%Y"))
                elif isinstance(widget, tb.Combobox):
                    widget.set('')
                    
        self.clear_followup_entries()
        self.reset_to_new_patient_mode()
        self.notebook.select(self.tab_intake)

    def clear_followup_entries(self, clear_date=True):
        followup_keys = [
            'fu_entry_date', 'fu_text_complaints', 'fu_text_new_modalities', 'fu_text_treatment'
        ]
        
        for name in followup_keys:
            widget = self.followup_entries.get(name)
            if widget:
                if isinstance(widget, Text):
                    widget.delete("1.0", END)
                else:
                    widget.delete(0, END)
                    if name == 'fu_entry_date' and not clear_date:
                        widget.insert(0, datetime.today().strftime("%d-%m-%Y"))
                    elif name == 'fu_entry_date' and clear_date:
                        widget.insert(0, datetime.today().strftime("%d-%m-%Y"))
                    
        if self.current_patient_id is None:
            for row in self.tree_history.get_children():
                 self.tree_history.delete(row)
        
    def reset_to_new_patient_mode(self):
        self.current_patient_id = None
        self.btn_save_new.grid() 
        self.btn_update_intake.grid_remove() 
        self.btn_save_followup.configure(state=DISABLED)

    def switch_to_edit_mode(self):
        self.btn_save_new.grid_remove()
        self.btn_update_intake.grid()
        self.btn_save_followup.configure(state=NORMAL)

    def _unpad_case_no(self, case_no_value):
        """Removes leading zeros for display in the UI."""
        if case_no_value is None:
            return ""
        
        s = str(case_no_value)
        
        # Only unpad if it looks like a padded number
        if re.match(r'0+\d+$', s):
            unpadded = s.lstrip('0')
            # If lstrip('0') results in an empty string (meaning the input was '0', '00', '000'), return '0'.
            return unpadded if unpadded else '0' 
        
        return s

    def search_patient(self):
        query = self.entry_search.get()
        conn = sqlite3.connect(self.DB_NAME)
        c = conn.cursor()
        
        # Simple search using the stored (padded) value for fast retrieval, ordered by case_no ASC
        c.execute("""
            SELECT id, case_no, name, date, age, gender FROM patients
            WHERE case_no LIKE ? OR name LIKE ?
            ORDER BY case_no ASC 
        """, (f"%{query}%", f"%{query}%"))
        rows = c.fetchall()
        conn.close()

        for row in self.tree_search.get_children():
            self.tree_search.delete(row)
        
        for row in rows:
            patient_id = row[0]
            
            # ⭐️ UNPADDING CASE_NO for Treeview DISPLAY ⭐️
            display_row = list(row[1:])
            display_row[0] = self._unpad_case_no(display_row[0])
            
            self.tree_search.insert("", "end", iid=patient_id, values=display_row)
            
    def on_tree_double_click(self, event):
        # Handles double click on search results AND view all records
        selected_item = event.widget.focus()
        
        if selected_item:
            try:
                # The iid is set to the patient_id
                patient_id = int(selected_item)
                self.edit_record(patient_id)
            except ValueError:
                pass
            
    # ⭐️ MODIFIED: Unpads Case No for Entry Box ⭐️
    def edit_record(self, patient_id):
        conn = sqlite3.connect(self.DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
        record = c.fetchone()
        conn.close()

        if not record:
            messagebox.showerror("Error", "Patient record not found.")
            return

        self.clear_entries() 
        self.current_patient_id = patient_id
        self.switch_to_edit_mode() 
        
        # Mapping remains the same
        column_map = [
            'entry_date', 'entry_case_no', 'entry_name', 'entry_age', 'entry_address', 'combo_sex',
            'entry_co', 'entry_onset_duration',
            'entry_habit', 'entry_diet', 'entry_appetite', 'entry_bowel',
            'entry_family_history', 'entry_past_history',
            'entry_mind', 'entry_sleep', 'entry_desire', 'entry_aversion', 
            'entry_wt', 'entry_bp', 'entry_pulse', 'entry_temp',
            'entry_systemic_exam', 'entry_modalities_pe', 'entry_diagnosis',
            'entry_treatment'
        ]
        db_column_indices = [
            1, 2, 3, 4, 5, 6, 
            7, 8, 
            9, 10, 11, 12, 
            13, 14, 
            15, 16, 17, 18, 
            19, 20, 21, 22, 
            23, 24, 25, 26 
        ]

        for i, key in enumerate(column_map):
            widget = self.entries.get(key)
            db_index = db_column_indices[i]
            value = record[db_index] 
            
            # Apply unpadding ONLY to the case_no field
            if key == 'entry_case_no':
                value = self._unpad_case_no(value)

            if widget and value is not None:
                if isinstance(widget, Text):
                    widget.delete("1.0", END)
                    widget.insert("1.0", str(value))
                else:
                    widget.delete(0, END)
                    widget.insert(0, str(value))

        self.populate_visit_history()
        self.show_frame(self.add_frame)
        
    def populate_visit_history(self):
        if self.current_patient_id is None:
            return

        for row in self.tree_history.get_children():
            self.tree_history.delete(row)

        conn = sqlite3.connect(self.DB_NAME)
        c = conn.cursor()
        c.execute("SELECT visit_id, visit_date, complaints, treatment FROM visits WHERE patient_id = ? ORDER BY visit_date DESC", 
                      (self.current_patient_id,))
        visits = c.fetchall()
        conn.close()

        for visit in visits:
            visit_id, date, complaints, treatment = visit
            display_complaints = complaints[:50] + '...' if len(complaints) > 50 else complaints
            display_treatment = treatment[:50] + '...' if len(treatment) > 50 else treatment
            
            self.tree_history.insert("", "end", iid=visit_id, 
                                             values=(date, display_complaints, display_treatment))
    
    def on_history_double_click(self, event):
        selected_item = self.tree_history.focus()
        
        if selected_item:
            try:
                visit_id = int(selected_item)
                self.view_visit_details(visit_id)
            except ValueError:
                pass
            
    def view_visit_details(self, visit_id):
        conn = sqlite3.connect(self.DB_NAME)
        c = conn.cursor()
        c.execute("""
            SELECT 
                v.visit_date, v.complaints, v.new_modalities, v.treatment,
                p.name, p.case_no
            FROM visits v
            JOIN patients p ON v.patient_id = p.id
            WHERE v.visit_id = ?
        """, (visit_id,))
        record = c.fetchone()
        conn.close()

        if not record:
            messagebox.showerror("Error", "Visit record not found.")
            return

        visit_date, complaints, new_modalities, treatment, patient_name, case_no = record
        
        # ⭐️ UNPADDING CASE_NO for Visit Details Display ⭐️
        case_no = self._unpad_case_no(case_no)
        
        details_window = Toplevel(self.master)
        details_window.title(f"Visit Details: {patient_name} ({case_no}) - {visit_date}")
        details_window.geometry("1000x550") 
        details_window.transient(self.master)

        canvas = tb.Canvas(details_window)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar = tb.Scrollbar(details_window, orient="vertical", command=canvas.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        detail_frame = tb.Frame(canvas, padding=15)
        canvas.create_window((0, 0), window=detail_frame, anchor="nw", width=950) 
        
        detail_frame.columnconfigure(1, weight=1)

        self.bind_mouse_scroll(canvas, detail_frame) 
        detail_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def display_text_field(parent, label_text, content, row_idx, height=4): 
            style_obj = self.master.style 
            
            tb.Label(parent, text=label_text, font=self.BOLD_FONT).grid(row=row_idx, column=0, sticky=NW, pady=(10, 2))
            
            text_widget = Text(parent, height=height, font=self.DEFAULT_FONT, wrap=WORD, borderwidth=1, relief="flat", state=NORMAL)
            text_widget.insert("1.0", content if content else "N/A")
            
            text_widget.bind('<Key-Tab>', lambda e: text_widget.tk_focusNext() or "break")
            text_widget.bind('<Shift-Key-Tab>', lambda e: text_widget.tk_focusPrev() or "break")
            
            text_widget.config(state=DISABLED, background=style_obj.lookup('TFrame', 'background'))
            
            text_widget.grid(row=row_idx, column=1, sticky=EW, pady=(10, 2), padx=5)
            
            return row_idx + 1

        r = 0
        
        tb.Label(detail_frame, text=f"Patient: {patient_name} (Case No: {case_no})", 
                                     font=("Helvetica", 16, "bold"), bootstyle="primary").grid(row=r, column=0, columnspan=2, pady=10)
        r += 1
        
        tb.Label(detail_frame, text=f"Visit Date: {visit_date}", 
                                     font=("Helvetica", 14, "italic")).grid(row=r, column=0, columnspan=2, pady=(0, 15))
        r += 1
        
        r = display_text_field(detail_frame, "Complaints:", complaints, r, height=4) 
        r = display_text_field(detail_frame, "New Modalities:", new_modalities, r, height=3) 
        r = display_text_field(detail_frame, "Treatment (Remedy/Dose):", treatment, r, height=4) 
        
        detail_frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    # ==================== PDF Export Functions (Updated for Hospital Style) ====================
    
    def get_full_patient_data(self, patient_id):
        """Fetches all intake and visit data for a single patient."""
        conn = sqlite3.connect(self.DB_NAME)
        c = conn.cursor()
        
        # Exclude 'id' and 'constitution' (if it exists, though not in schema)
        c.execute("PRAGMA table_info(patients)")
        patient_cols = [col[1] for col in c.fetchall() if col[1] != 'id' and col[1] != 'constitution']
        
        c.execute(f"SELECT {', '.join(patient_cols)} FROM patients WHERE id = ?", (patient_id,))
        intake_record = c.fetchone()
        
        c.execute("SELECT visit_date, complaints, new_modalities, treatment FROM visits WHERE patient_id = ? ORDER BY visit_date ASC", (patient_id,))
        visit_records = c.fetchall()
        
        conn.close()
        
        if not intake_record:
            return None, None
            
        intake_data = dict(zip(patient_cols, intake_record))
        
        # ⭐️ UNPAD CASE_NO for PDF Display ⭐️
        intake_data['case_no'] = self._unpad_case_no(intake_data['case_no'])
        
        return intake_data, visit_records
    
    # ⭐️ NEW: Manual Hex conversion to fix 'Color object has no attribute 'hexa' error ⭐️
    def _to_hex(self, color_obj):
        """Converts ReportLab Color object (0-1 floats) to an #RRGGBB hex string."""
        r = int(color_obj.red * 255)
        g = int(color_obj.green * 255)
        b = int(color_obj.blue * 255)
        return f"#{r:02x}{g:02x}{b:02x}"


    def generate_patient_pdf(self, intake_data, visit_records, filename):
        """Generates a PDF report for a single patient using the hospital template, ensuring intake fits one page
        and follow-ups are continuous (no page break between visits)."""
        
        # Define custom colors
        NAVY_BLUE = colors.Color(0.04, 0.16, 0.35) # Primary Blue
        TEAL = colors.Color(0, 0.5, 0.5)           # Info/Success Teal
        
        # Use safe hex conversion
        TEAL_HEX = self._to_hex(TEAL)
        NAVY_HEX = self._to_hex(NAVY_BLUE)

        # Pass clinic/doctor details to the document for the header template
        doc = ReportLabTemplate(filename, pagesize=letter,
                                leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                                bottomMargin=0.4 * inch,
                                DOCTOR_NAME=self.DOCTOR_NAME, DOCTOR_DEGREE=self.DOCTOR_DEGREE,
                                CLINIC_NAME=self.CLINIC_NAME, DOCTOR_REG_NO=self.DOCTOR_REG_NO,
                                ADDRESS_LINE1=self.ADDRESS_LINE1, CONTACT_INFO=self.CONTACT_INFO)
        
        styles = getSampleStyleSheet()
        story = []

        # ⭐️ MODIFIED Styles for Coloring and Bullet Points ⭐️
        H_TITLE = ParagraphStyle('H_TITLE', parent=styles['h1'], fontSize=11, alignment=TA_CENTER,  
                                 spaceBefore=5, spaceAfter=4, fontName='Helvetica-Bold', textColor=NAVY_BLUE)
        
        # textColor is set via the Color object itself, which is fine for the style sheet.
        H_SECTION = ParagraphStyle('H_SECTION', parent=styles['h2'], fontSize=9, alignment=TA_LEFT,  
                                    spaceBefore=6, spaceAfter=2, fontName='Helvetica-Bold', textColor=TEAL)
                                    
        H_VISIT = ParagraphStyle('H_VISIT', parent=styles['h3'], fontSize=9, alignment=TA_LEFT,  
                                 spaceBefore=8, spaceAfter=2, fontName='Helvetica-BoldOblique', textColor=NAVY_BLUE)
        BODY = ParagraphStyle('BODY', parent=styles['Normal'], fontSize=7.5, alignment=TA_JUSTIFY,  
                              leading=9, spaceAfter=1, fontName='Helvetica')
        BODY_BOLD = ParagraphStyle('BODY_BOLD', parent=BODY, fontName='Helvetica-Bold')
        TEXT_BLOCK = ParagraphStyle('TEXT_BLOCK', parent=styles['Normal'], fontSize=7.5, alignment=TA_JUSTIFY,  
                                    leading=9, spaceAfter=4, fontName='Helvetica')
        
        # --- Patient Header Block ---
        patient_name_str = intake_data.get('name', 'N/A')
        case_no_str = intake_data.get('case_no', 'N/A')
        
        # Intake page padding (15 points)
        story.append(Spacer(1, 15)) 

        # ⭐️ Title uses Navy Blue (using HEX string) ⭐️
        patient_header = f"<b>PATIENT INTAKE RECORD:</b> <font color='{NAVY_HEX}'>{patient_name_str}</font> (Case No: {case_no_str})"
        story.append(Paragraph(patient_header, H_TITLE))
        story.append(Spacer(1, 2))


        # --- Helper to add a section with bullet and variable height text ---
        def add_bulleted_text_section(title, key, height_lines=1):
            # Using the pre-calculated TEAL_HEX string for inline color
            story.append(Paragraph(f"<font color='{TEAL_HEX}'>&#8226;</font> <b><u>{title}:</u></b>", H_SECTION))
            content = str(intake_data.get(key) or 'N/A').replace('\n', '<br/>')
            story.append(Paragraph(content, TEXT_BLOCK))

        # 1) Preliminary Data (Compact Table) 
        story.append(Paragraph(f"<font color='{TEAL_HEX}'>&#8226;</font> <b><u>Preliminary Data:</u></b>", H_SECTION))
        
        prelim_data = [
            [Paragraph("<b>Date:</b>", BODY_BOLD), Paragraph(intake_data.get('date', 'N/A'), BODY),  
             Paragraph("<b>Age:</b>", BODY_BOLD), Paragraph(intake_data.get('age', 'N/A'), BODY)],
            [Paragraph("<b>Name:</b>", BODY_BOLD), Paragraph(patient_name_str, BODY),  
             Paragraph("<b>Gender:</b>", BODY_BOLD), Paragraph(intake_data.get('gender', 'N/A'), BODY)],
            [Paragraph("<b>Address:</b>", BODY_BOLD), Paragraph(intake_data.get('address', 'N/A'), BODY),
             '', ''],
        ]
        
        prelim_table = Table(prelim_data, colWidths=[doc.width * 0.1, doc.width * 0.4, doc.width * 0.1, doc.width * 0.4])
        prelim_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('SPAN', (1, 2), (-1, 2)), 
            ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1), ('TOPPADDING', (0, 0), (-1, -1), 1)
        ]))
        story.append(prelim_table)
        story.append(Spacer(1, 5))

        # 2) Chief Complaints Group
        add_bulleted_text_section("Chief Complaints (C/O)", 'co')
        add_bulleted_text_section("Onset and Duration", 'onset_duration')
        
        # 3) Personal History Group
        story.append(Paragraph(f"<font color='{TEAL_HEX}'>&#8226;</font> <b><u>Personal History:</u></b>", H_SECTION))
        personal_history_data = [
            [
                Paragraph("<b>Habit:</b>", BODY_BOLD), Paragraph(str(intake_data.get('habit', 'N/A') or 'N/A').replace('\n', '<br/>'), BODY),  
                Paragraph("<b>Diet:</b>", BODY_BOLD), Paragraph(str(intake_data.get('diet', 'N/A') or 'N/A').replace('\n', '<br/>'), BODY),
            ],
            [
                Paragraph("<b>Appetite:</b>", BODY_BOLD), Paragraph(str(intake_data.get('appetite', 'N/A') or 'N/A').replace('\n', '<br/>'), BODY),  
                Paragraph("<b>Bowel:</b>", BODY_BOLD), Paragraph(str(intake_data.get('bowel', 'N/A') or 'N/A').replace('\n', '<br/>'), BODY),
            ]
        ]
        ph_table = Table(personal_history_data, colWidths=[doc.width * 0.1, doc.width * 0.4, doc.width * 0.1, doc.width * 0.4])
        ph_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1), ('TOPPADDING', (0, 0), (-1, -1), 1)
        ]))
        story.append(ph_table)
        story.append(Spacer(1, 5))
        
        # 4 & 5) History (Text Block)
        add_bulleted_text_section("Family History", 'family_history')
        add_bulleted_text_section("Past History", 'past_history')
        
        # 6) Generalities (Text Block)
        story.append(Paragraph(f"<font color='{TEAL_HEX}'>&#8226;</font> <b><u>Homoeopathic Generalities:</u></b>", H_SECTION))
        generalities_data = [
            [
                Paragraph("<b>Mind:</b>", BODY_BOLD), Paragraph(str(intake_data.get('mind', 'N/A') or 'N/A').replace('\n', '<br/>'), BODY),  
                Paragraph("<b>Sleep:</b>", BODY_BOLD), Paragraph(str(intake_data.get('sleep', 'N/A') or 'N/A').replace('\n', '<br/>'), BODY),
            ],
            [
                Paragraph("<b>Desire:</b>", BODY_BOLD), Paragraph(str(intake_data.get('desire', 'N/A') or 'N/A').replace('\n', '<br/>'), BODY),  
                Paragraph("<b>Aversion:</b>", BODY_BOLD), Paragraph(str(intake_data.get('aversion', 'N/A') or 'N/A').replace('\n', '<br/>'), BODY),
            ]
        ]
        gen_table = Table(generalities_data, colWidths=[doc.width * 0.1, doc.width * 0.4, doc.width * 0.1, doc.width * 0.4])
        gen_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1), ('TOPPADDING', (0, 0), (-1, -1), 1)
        ]))
        story.append(gen_table)
        story.append(Spacer(1, 5))

        # 7) Physical Examination & Initial Treatment (Combined)
        story.append(Paragraph(f"<font color='{TEAL_HEX}'>&#8226;</font> <b><u>Physical Examination & Initial Treatment:</u></b>", H_SECTION))

        vitals_data = [
            [Paragraph("<b>Wt:</b>", BODY_BOLD), Paragraph(intake_data.get('wt', 'N/A'), BODY),  
             Paragraph("<b>B.P.:</b>", BODY_BOLD), Paragraph(intake_data.get('bp', 'N/A'), BODY)],
            [Paragraph("<b>Pulse:</b>", BODY_BOLD), Paragraph(intake_data.get('pulse', 'N/A'), BODY),  
             Paragraph("<b>Temp:</b>", BODY_BOLD), Paragraph(intake_data.get('temp', 'N/A'), BODY)]
        ]
        
        vitals_table = Table(vitals_data, colWidths=[doc.width * 0.1, doc.width * 0.4, doc.width * 0.1, doc.width * 0.4])
        vitals_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1), ('TOPPADDING', (0, 0), (-1, -1), 1)
        ]))
        story.append(vitals_table)
        story.append(Spacer(1, 5))
        
        # Examination Details & Treatment (Text Blocks)
        add_bulleted_text_section("Systemic Examination", 'systemic_exam')
        add_bulleted_text_section("Modalities (P.E.)", 'modalities_pe')
        add_bulleted_text_section("Diagnosis", 'diagnosis')
        add_bulleted_text_section("Initial Treatment", 'treatment')

        # --- Visit History (CONDITIONAL SECTION) ---
        if visit_records:
            story.append(PageBreak()) 
            # ⭐️ Title uses Navy Blue ⭐️
            story.append(Paragraph("<u>VISIT HISTORY / FOLLOW-UPS</u>", H_TITLE))
            
            # ⭐️ Increased initial spacer for Follow-up page. ⭐️
            story.append(Spacer(1, 25)) 

            for i, visit in enumerate(visit_records):
                
                date, complaints, new_modalities, treatment = visit 
                
                # H_VISIT uses Navy Blue (color set in style, not inline)
                story.append(Paragraph(f"Visit {i+1}: <font color='black'>{date}</font>", H_VISIT))
                
                visit_data = [
                    [Paragraph("<b>Complaints/Changes:</b>", BODY_BOLD), Paragraph(str(complaints or 'N/A').replace('\n', '<br/>'), BODY)],
                    [Paragraph("<b>New Modalities:</b>", BODY_BOLD), Paragraph(str(new_modalities or 'N/A').replace('\n', '<br/>'), BODY)],
                    [Paragraph("<b>Treatment (Remedy/Dose):</b>", BODY_BOLD), Paragraph(str(treatment or 'N/A').replace('\n', '<br/>'), BODY)]
                ]
                
                visit_table = Table(visit_data, colWidths=[doc.width * 0.2, doc.width * 0.8])
                visit_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('LINEBELOW', (0, 2), (-1, 2), 0.5, colors.lightgrey), 
                ]))
                story.append(visit_table)
                story.append(Spacer(1, 8))

        try:
            # Build the document
            doc.build(story)
            return True
        except Exception as e:
            messagebox.showerror("PDF Build Error", f"Failed to build PDF content. Error: {e}")
            return False

    def export_selected_patient_to_pdf(self):
        """Exports the currently selected patient record to a PDF file."""
        selected_item = self.tree_search.focus()
        
        if not selected_item:
            messagebox.showerror("Export Error", "Please select a patient record from the list to export.")
            return

        try:
            patient_id = int(selected_item)
            item_values = self.tree_search.item(selected_item, 'values')
            patient_name = item_values[1]
            case_no = item_values[0] # This is already unpadded from search_patient()
            
            intake_data, visit_records = self.get_full_patient_data(patient_id)

            if not intake_data:
                messagebox.showerror("Error", "Could not retrieve patient data for export.")
                return

            safe_name = "".join(c for c in patient_name if c.isalnum() or c in (' ', '_')).rstrip()
            default_filename = f"{safe_name}_{case_no}_Full_Record.pdf"
            
            filepath = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                initialfile=default_filename,
                title="Save Patient Record as PDF",
                filetypes=(("PDF files", "*.pdf"), ("All files", "*.*"))
            )

            if not filepath:
                return 

            if self.generate_patient_pdf(intake_data, visit_records, filepath):
                messagebox.showinfo("Export Complete", 
                                       f"Patient record successfully saved to:\n{filepath}")

        except ValueError:
            messagebox.showerror("Error", "Invalid patient selection.")
        except Exception as e:
            messagebox.showerror("Export Error", f"An unexpected error occurred during file operation: {e}")

    # ⭐ NEW: Function to export the patient currently loaded in the Add/Edit form ⭐
    def export_current_patient_to_pdf(self):
        """Exports the patient currently loaded in the Add/Edit frame to a PDF file."""
        patient_id = self.current_patient_id

        if patient_id is None:
            messagebox.showerror("Export Error", "No patient record is currently loaded for export. Please load an existing patient or save a new one first.")
            return

        try:
            # Fetch patient details for file naming
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute("SELECT name, case_no FROM patients WHERE id = ?", (patient_id,))
            record = c.fetchone()
            conn.close()

            if not record:
                messagebox.showerror("Error", "Could not retrieve patient data for export.")
                return

            patient_name, case_no_padded = record
            case_no = self._unpad_case_no(case_no_padded)
            
            intake_data, visit_records = self.get_full_patient_data(patient_id)
            
            safe_name = "".join(c for c in patient_name if c.isalnum() or c in (' ', '_')).rstrip()
            default_filename = f"{safe_name}_{case_no}_Full_Record.pdf"
            
            filepath = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                initialfile=default_filename,
                title="Save Patient Record as PDF",
                filetypes=(("PDF files", "*.pdf"), ("All files", "*.*"))
            )

            if not filepath:
                return 

            if self.generate_patient_pdf(intake_data, visit_records, filepath):
                messagebox.showinfo("Export Complete", 
                                       f"Patient record successfully saved to:\n{filepath}")

        except Exception as e:
            messagebox.showerror("Export Error", f"An unexpected error occurred during file operation: {e}")
            

    # ==================== UI/Page Management ====================
    def show_frame(self, frame):
        for f in (self.home_frame, self.add_frame, self.search_frame, self.view_all_frame): 
            f.pack_forget()
        frame.pack(fill=BOTH, expand=True)

    # ⭐ MODIFIED: Includes Arrow Key Bindings for Buttons ⭐
    def home_page(self):
        # Title uses primary (Dark Navy)
        title = tb.Label(self.home_frame, text=" Shradha Homoeo Clinic",
                                         bootstyle="primary", style="HomeTitle.TLabel") 
        title.pack(pady=70) 

        # Primary Action: Add New Patient (Bright Teal - Success style)
        btn_add = tb.Button(self.home_frame, text=" Add New Patient", 
                     width=50, padding=30, bootstyle="success", # <--- Primary Action Color
                     command=lambda: [self.clear_entries(), self.show_frame(self.add_frame)])
        btn_add.pack(pady=20)

        # Secondary Action: Search Patient (Dark Navy - Primary style)
        btn_search = tb.Button(self.home_frame, text=" Search Patient", 
                     width=50, padding=30, bootstyle="primary", # <--- Secondary Action Color
                     command=lambda: self.show_frame(self.search_frame))
        btn_search.pack(pady=20)
                     
        # Tertiary Action: View All Records (Slate Teal - Info style)
        btn_view_all = tb.Button(self.home_frame, text=" View All Records ", 
                     width=50, padding=30, bootstyle="info", # <--- Tertiary Action Color
                     command=lambda: [self.load_all_records(1), self.show_frame(self.view_all_frame)])
        btn_view_all.pack(pady=20)
        
        # ⭐ MODIFIED: Bind only Up/Down Arrow Keys for Home Page Navigation ⭐
        for btn in [btn_add, btn_search, btn_view_all]:
            btn.bind('<Up>', self.navigate_home_buttons)
            btn.bind('<Down>', self.navigate_home_buttons)

    def on_notebook_select(self, event):
        """Prevents selection change when tabs are styled as 'disabled'."""
        pass

    # ⭐️ MODIFIED: Added Print Button to the bottom of the Add/Edit page ⭐️
    def add_page(self):
        self.add_frame.columnconfigure(0, weight=1)
        self.add_frame.rowconfigure(1, weight=1) 

        tb.Label(self.add_frame, text=" Shradha Homoeo Clinic",
                                         font=self.TITLE_FONT, bootstyle="primary").grid(row=0, column=0, pady=10) # Title uses primary

        self.notebook = tb.Notebook(self.add_frame)
        self.notebook.grid(row=1, column=0, pady=10, padx=10, sticky=EW+NS)
        
        # Tabs foreground uses success (Bright Teal)
        self.notebook.configure(style="Disabled.TNotebook") 

        self.tab_intake = tb.Frame(self.notebook, padding=5)
        self.notebook.add(self.tab_intake, text=" Initial Intake Form")
        self.build_intake_form(self.tab_intake)

        self.tab_followup = tb.Frame(self.notebook, padding=5)
        self.notebook.add(self.tab_followup, text=" Follow-up / Visits")
        self.build_followup_page(self.tab_followup)
        
        self.notebook.bind('<<NotebookTabChanged>>', self.on_notebook_select)
        
        # --- Container for buttons at the bottom ---
        button_container = tb.Frame(self.add_frame)
        button_container.grid(row=2, column=0, pady=5, sticky=EW)
        button_container.columnconfigure(0, weight=1)
        button_container.columnconfigure(1, weight=1)

        # 1. Back to Home Button
        tb.Button(button_container, text="⬅ Back to Home", bootstyle="danger", 
                     command=lambda: self.show_frame(self.home_frame), padding=10).grid(row=0, column=0, padx=(20, 10), sticky=W)

        # 2. Print Current Patient Button (uses Primary/Navy style for professional print look)
        tb.Button(button_container, text="📄 Print Current Record (PDF)", bootstyle="primary", 
                     command=self.export_current_patient_to_pdf, padding=10).grid(row=0, column=1, padx=(10, 20), sticky=E)

    def build_intake_form(self, parent_frame):
        # Implementation for build_intake_form (uses min heights and highlight bindings)
        self.intake_widgets.clear()
        self.widget_label_map.clear() 

        canvas = tb.Canvas(parent_frame)
        self.intake_canvas = canvas
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar = tb.Scrollbar(parent_frame, orient="vertical", command=canvas.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.configure(yscrollcommand=scrollbar.set)

        form_frame = tb.Frame(canvas, padding=15)
        canvas.create_window((0, 0), window=form_frame, anchor="nw", width=1150) 
        
        self.bind_mouse_scroll(canvas, form_frame)
        form_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        form_frame.columnconfigure(1, weight=1) 
        form_frame.columnconfigure(3, weight=1) 
        form_frame.columnconfigure(0, weight=0)
        form_frame.columnconfigure(2, weight=0)
        
        row_idx = 0
        
        def create_text_widget(parent, entries_dict, key, label_text, height=2): 
            nonlocal row_idx
            
            label = tb.Label(parent, text=label_text, font=self.BOLD_FONT)
            label.grid(row=row_idx, column=0, sticky=NW, pady=(7, 2))
            
            text_frame = tb.Frame(parent)
            text_frame.grid(row=row_idx, column=1, columnspan=3, sticky=EW, pady=2, padx=5)
            text_widget = Text(text_frame, height=height, font=self.DEFAULT_FONT, wrap=WORD, borderwidth=1, relief="solid", bg="white")
            text_widget.pack(side=LEFT, fill=BOTH, expand=True)
            
            self.bind_tab_to_widget(text_widget, self.intake_widgets)
            self.widget_label_map[text_widget] = label 

            scrollbar = tb.Scrollbar(text_frame, orient=VERTICAL, command=text_widget.yview)
            scrollbar.pack(side=RIGHT, fill=Y)
            text_widget.config(yscrollcommand=scrollbar.set)
            entries_dict[key] = text_widget
            row_idx += 1
            return text_widget
            
        def create_entry_widget(parent, entries_dict, key, label=None, width=20, col=1, sticky=EW, padx=5, pady=5):
            entry = tb.Entry(parent, width=width, font=self.DEFAULT_FONT) 
            entry.grid(row=row_idx, column=col, sticky=sticky, padx=padx, pady=pady)
            self.bind_tab_to_widget(entry, self.intake_widgets)
            if label:
                self.widget_label_map[entry] = label 
            entries_dict[key] = entry
            return entry

        def create_combobox_widget(parent, entries_dict, key, label=None, values=None, width=20, col=1, sticky=EW, padx=5, pady=5):
            combo = tb.Combobox(parent, values=values, width=width, font=self.DEFAULT_FONT)
            combo.grid(row=row_idx, column=col, sticky=sticky, padx=padx, pady=pady)
            self.bind_tab_to_widget(combo, self.intake_widgets)
            if label:
                self.widget_label_map[combo] = label 
            entries_dict[key] = combo
            return combo
        
        # 1. Date + Case No
        label_date = tb.Label(form_frame, text="Date:", font=self.BOLD_FONT)
        label_date.grid(row=row_idx, column=0, sticky=W, pady=5)
        self.entries['entry_date'] = create_entry_widget(form_frame, self.entries, 'entry_date', label=label_date, col=1, sticky=W)
        self.entries['entry_date'].insert(0, datetime.today().strftime("%d-%m-%Y"))

        label_case_no = tb.Label(form_frame, text="Case No:", font=self.BOLD_FONT)
        label_case_no.grid(row=row_idx, column=2, sticky=W, padx=(10, 0))
        self.entries['entry_case_no'] = create_entry_widget(form_frame, self.entries, 'entry_case_no', label=label_case_no, col=3)
        row_idx += 1

        tb.Label(form_frame, text="1) Preliminary Data", font=self.TITLE_FONT).grid(row=row_idx, column=0, columnspan=4, sticky=W, pady=(15, 5))
        row_idx += 1
        
        # 2. Name, Age, Address, Sex
        label_name = tb.Label(form_frame, text="Name:", font=self.BOLD_FONT)
        label_name.grid(row=row_idx, column=0, sticky=W)
        self.entries['entry_name'] = create_entry_widget(form_frame, self.entries, 'entry_name', label=label_name, width=40, col=1, pady=2)
        
        label_age = tb.Label(form_frame, text="Age:", font=self.BOLD_FONT)
        label_age.grid(row=row_idx, column=2, sticky=W, padx=(10, 0))
        self.entries['entry_age'] = create_entry_widget(form_frame, self.entries, 'entry_age', label=label_age, width=10, col=3, pady=2)
        row_idx += 1

        label_address = tb.Label(form_frame, text="Address:", font=self.BOLD_FONT)
        label_address.grid(row=row_idx, column=0, sticky=W)
        self.entries['entry_address'] = create_entry_widget(form_frame, self.entries, 'entry_address', label=label_address, width=40, col=1, pady=2)
        
        label_sex = tb.Label(form_frame, text="Sex:", font=self.BOLD_FONT)
        label_sex.grid(row=row_idx, column=2, sticky=W, padx=(10, 0))
        self.entries['combo_sex'] = create_combobox_widget(form_frame, self.entries, 'combo_sex', label=label_sex, values=["M", "F"], width=8, col=3)
        
        row_idx += 1

        # 3. Chief Complaints Group (HEIGHT=2)
        tb.Label(form_frame, text="2) Chief Complaints", font=self.TITLE_FONT).grid(row=row_idx, column=0, columnspan=4, sticky=W, pady=(15, 5))
        row_idx += 1
        
        self.entries['entry_co'] = create_text_widget(form_frame, self.entries, 'entry_co', "C/O:", height=3) 
        self.entries['entry_onset_duration'] = create_text_widget(form_frame, self.entries, 'entry_onset_duration', "Onset and Duration:", height=2) 

        # 4. Personal History Group (HEIGHT=1)
        tb.Label(form_frame, text="3) Personal History", font=self.TITLE_FONT).grid(row=row_idx, column=0, columnspan=4, sticky=W, pady=(15, 5))
        row_idx += 1
        self.entries['entry_habit'] = create_text_widget(form_frame, self.entries, 'entry_habit', "Habit:", height=1) 
        self.entries['entry_diet'] = create_text_widget(form_frame, self.entries, 'entry_diet', "Diet:", height=1) 
        self.entries['entry_appetite'] = create_text_widget(form_frame, self.entries, 'entry_appetite', "Appetite:", height=1) 
        self.entries['entry_bowel'] = create_text_widget(form_frame, self.entries, 'entry_bowel', "Bowel:", height=1) 

        # 5. History Groups (HEIGHT=2)
        tb.Label(form_frame, text="4) Family History", font=self.TITLE_FONT).grid(row=row_idx, column=0, columnspan=4, sticky=W, pady=(15, 5))
        row_idx += 1
        self.entries['entry_family_history'] = create_text_widget(form_frame, self.entries, 'entry_family_history', "Family History:", height=2) 

        tb.Label(form_frame, text="5) Past History", font=self.TITLE_FONT).grid(row=row_idx, column=0, columnspan=4, sticky=W, pady=(15, 5))
        row_idx += 1
        self.entries['entry_past_history'] = create_text_widget(form_frame, self.entries, 'entry_past_history', "Past History:", height=2) 

        # 6. Homoeopathic Generalities Group (HEIGHT=2 and 1)
        tb.Label(form_frame, text="6) Homoeopathic Generalities", font=self.TITLE_FONT).grid(row=row_idx, column=0, columnspan=4, sticky=W, pady=(15, 5))
        row_idx += 1
        self.entries['entry_mind'] = create_text_widget(form_frame, self.entries, 'entry_mind', "Mind:", height=2) 
        self.entries['entry_sleep'] = create_text_widget(form_frame, self.entries, 'entry_sleep', "Sleep:", height=1) 
        self.entries['entry_desire'] = create_text_widget(form_frame, self.entries, 'entry_desire', "Desire:", height=1) 
        self.entries['entry_aversion'] = create_text_widget(form_frame, self.entries, 'entry_aversion', "Aversion:", height=1) 

        # 7. Physical Examination
        tb.Label(form_frame, text="7) Physical Examination", font=self.TITLE_FONT).grid(row=row_idx, column=0, columnspan=4, sticky=W, pady=(15, 5))
        row_idx += 1
        
        # Physical Vitals (Entry boxes) 
        label_wt = tb.Label(form_frame, text="Wt:", font=self.BOLD_FONT)
        label_wt.grid(row=row_idx, column=0, sticky=W)
        self.entries['entry_wt'] = create_entry_widget(form_frame, self.entries, 'entry_wt', label=label_wt, col=1, sticky=W)
        
        label_bp = tb.Label(form_frame, text="B.P.:", font=self.BOLD_FONT)
        label_bp.grid(row=row_idx, column=2, sticky=W, padx=(10, 0))
        self.entries['entry_bp'] = create_entry_widget(form_frame, self.entries, 'entry_bp', label=label_bp, col=3)
        row_idx += 1
        
        label_pulse = tb.Label(form_frame, text="Pulse:", font=self.BOLD_FONT)
        label_pulse.grid(row=row_idx, column=0, sticky=W)
        self.entries['entry_pulse'] = create_entry_widget(form_frame, self.entries, 'entry_pulse', label=label_pulse, col=1, sticky=W)
        
        label_temp = tb.Label(form_frame, text="Temp:", font=self.BOLD_FONT)
        label_temp.grid(row=row_idx, column=2, sticky=W, padx=(10, 0))
        self.entries['entry_temp'] = create_entry_widget(form_frame, self.entries, 'entry_temp', label=label_temp, col=3)
        row_idx += 1
        
        # 8. Examination and Diagnosis (HEIGHT=2)
        self.entries['entry_systemic_exam'] = create_text_widget(form_frame, self.entries, 'entry_systemic_exam', "Systemic Examination:", height=2) 
        self.entries['entry_modalities_pe'] = create_text_widget(form_frame, self.entries, 'entry_modalities_pe', "Modalities (P.E.):", height=2) 
        self.entries['entry_diagnosis'] = create_text_widget(form_frame, self.entries, 'entry_diagnosis', "Diagnosis:", height=2) 
        self.entries['entry_treatment'] = create_text_widget(form_frame, self.entries, 'entry_treatment', "Treatment (Initial):", height=3) 

        # Save / Update Buttons for the INTAKE FORM
        btn_row_idx = row_idx 

        self.btn_save_new = tb.Button(form_frame, text=" Save New Patient", bootstyle="success", command=self.save_patient, padding=10) # Success (Bright Teal)
        self.btn_update_intake = tb.Button(form_frame, text=" Update Intake Data", bootstyle="primary", command=self.update_patient_intake, padding=10) # Primary (Dark Navy)
        
        self.bind_tab_to_widget(self.btn_save_new, self.intake_widgets)
        self.bind_tab_to_widget(self.btn_update_intake, self.intake_widgets)

        self.btn_save_new.grid(row=btn_row_idx, column=1, columnspan=2, pady=15, sticky=EW, padx=10)
        self.btn_update_intake.grid(row=btn_row_idx, column=1, columnspan=2, pady=15, sticky=EW, padx=10)
        self.btn_update_intake.grid_remove()
        
        form_frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    def build_followup_page(self, parent_frame):
        # Clear the follow-up widget list and map
        self.followup_widgets.clear()
        self.widget_label_map.clear()

        parent_frame.columnconfigure(0, weight=1)
        parent_frame.rowconfigure(0, weight=1)
        parent_frame.rowconfigure(1, weight=1)
        
        history_frame = tb.LabelFrame(parent_frame, text=" Visit History (Double-click for details)", 
                                             padding=10) 
        history_frame.grid(row=0, column=0, sticky=EW+NS, pady=(5, 10), padx=5)
        
        cols = ("Date", "Complaints Summary", "Treatment Summary")
        self.tree_history = tb.Treeview(history_frame, columns=cols, show="headings", height=8)
        self.tree_history.pack(fill=BOTH, expand=True)
        
        self.tree_history.bind("<Double-1>", self.on_history_double_click) 
        
        self.tree_history.column("#0", width=0, stretch=NO) 
        self.tree_history.column("Date", width=140, anchor=CENTER) 
        self.tree_history.column("Complaints Summary", width=480, anchor=W) 
        self.tree_history.column("Treatment Summary", width=480, anchor=W) 
        
        self.tree_history.heading("Date", text="Date", anchor=CENTER)
        self.tree_history.heading("Complaints Summary", text="Complaints Summary", anchor=W)
        self.tree_history.heading("Treatment Summary", text="Treatment Summary", anchor=W)
        
        # --- NEW FOLLOW UP FRAME ---
        new_fu_frame = tb.LabelFrame(parent_frame, text=" New Follow-up Visit", padding=10)
        new_fu_frame.grid(row=1, column=0, sticky=EW+NS, pady=(0, 5), padx=5)
        self.followup_canvas = None 
        
        new_fu_frame.columnconfigure(0, weight=0) 
        new_fu_frame.columnconfigure(1, weight=1) 
        
        def create_fu_text_widget(parent, key, label_text, height=2, row_idx=0):
            label = tb.Label(parent, text=label_text, font=self.BOLD_FONT)
            label.grid(row=row_idx, column=0, sticky=W, pady=(7, 2), padx=(0, 10))
            
            text_frame = tb.Frame(parent)
            text_frame.grid(row=row_idx + 1, column=0, columnspan=2, sticky=EW, pady=2) 
            text_widget = Text(text_frame, height=height, font=self.DEFAULT_FONT, wrap=WORD, borderwidth=1, relief="solid", bg="white")
            text_widget.pack(side=LEFT, fill=BOTH, expand=True)
            
            self.bind_tab_to_widget(text_widget, self.followup_widgets)
            self.widget_label_map[text_widget] = label
            
            scrollbar = tb.Scrollbar(text_frame, orient=VERTICAL, command=text_widget.yview)
            scrollbar.pack(side=RIGHT, fill=Y)
            text_widget.config(yscrollcommand=scrollbar.set)
            
            self.followup_entries[key] = text_widget
            return row_idx + 2 

        row_idx = 0
        
        label_date = tb.Label(new_fu_frame, text="Visit Date:", font=self.BOLD_FONT)
        label_date.grid(row=row_idx, column=0, sticky=W, pady=5)
        entry = tb.Entry(new_fu_frame, width=20, font=self.DEFAULT_FONT)
        entry.insert(0, datetime.today().strftime("%d-%m-%Y"))
        entry.grid(row=row_idx, column=1, sticky=W, padx=5, pady=5)
        
        self.bind_tab_to_widget(entry, self.followup_widgets)
        self.widget_label_map[entry] = label_date
        self.followup_entries['fu_entry_date'] = entry
        
        row_idx += 1 

        row_idx = create_fu_text_widget(new_fu_frame, 'fu_text_complaints', "New Complaints:", 2, row_idx) 
        
        row_idx = create_fu_text_widget(new_fu_frame, 'fu_text_new_modalities', "New Modalities:", 1, row_idx) 
        
        row_idx = create_fu_text_widget(new_fu_frame, 'fu_text_treatment', "Treatment (Remedy/Dose):", 2, row_idx) 
        
        # Save Follow-up Button uses Success (Bright Teal)
        self.btn_save_followup = tb.Button(new_fu_frame, text=" Save Follow-up Record", 
                                                 bootstyle="success", # <--- Primary Action Color
                                                 command=self.save_followup, 
                                                 state=DISABLED,
                                                 padding=10)
        
        self.bind_tab_to_widget(self.btn_save_followup, self.followup_widgets)
        
        self.btn_save_followup.grid(row=row_idx, column=1, pady=10, sticky=E)


    def search_page(self):
        self.search_frame.columnconfigure(0, weight=1)
        self.search_frame.rowconfigure(2, weight=1) 

        # Title uses Primary (Dark Navy)
        tb.Label(self.search_frame, text=" Search Patient (Double-click to View/Edit)",
                                         font=self.TITLE_FONT, bootstyle="primary").grid(row=0, column=0, pady=10, sticky=N) # <--- Secondary Action Color

        search_container = tb.Frame(self.search_frame)
        search_container.grid(row=1, column=0, pady=5, padx=20, sticky=EW)
        
        self.entry_search = tb.Entry(search_container, width=30, font=self.DEFAULT_FONT) 
        self.entry_search.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))

        # Search button uses Primary (Dark Navy)
        tb.Button(search_container, text="Search", bootstyle="primary", command=self.search_patient).pack(side=LEFT, padx=5) # <--- Secondary Action Color
        
        tb.Button(search_container, text="Delete Record", bootstyle="danger", command=self.delete_patient_record).pack(side=LEFT, padx=5)
        
        # Print button uses Info (Slate Teal)
        tb.Button(search_container, text="Print Selected Record (PDF)", bootstyle="info", command=self.export_selected_patient_to_pdf).pack(side=LEFT, padx=5) # <--- Tertiary Action Color


        cols = ("Case No", "Name", "Date", "Age", "Gender")
        self.tree_search = tb.Treeview(self.search_frame, columns=cols, show="headings", height=15)
        
        self.tree_search.column("#0", width=0, stretch=NO)
        self.tree_search.column("Case No", width=120, anchor=CENTER)
        self.tree_search.column("Date", width=120, anchor=CENTER)
        self.tree_search.column("Age", width=80, anchor=CENTER) 
        self.tree_search.column("Gender", width=100, anchor=CENTER) 
        self.tree_search.column("Name", width=600, anchor=W) 
        
        self.tree_search.heading("Case No", text="Case No", anchor=CENTER)
        self.tree_search.heading("Name", text="Name", anchor=W)
        self.tree_search.heading("Date", text="Date", anchor=CENTER)
        self.tree_search.heading("Age", text="Age", anchor=CENTER)
        self.tree_search.heading("Gender", text="Gender", anchor=CENTER)
                
        self.tree_search.grid(row=2, column=0, pady=10, padx=20, sticky=EW+NS)

        self.tree_search.bind("<Double-1>", self.on_tree_double_click)
        
        self.tree_search.bind("<Tab>", self.navigate_treeview)
        self.tree_search.bind("<Shift-Tab>", self.navigate_treeview)

        tb.Button(self.search_frame, text="⬅ Back", bootstyle="danger",
                     command=lambda: self.show_frame(self.home_frame), padding=10).grid(row=3, column=0, pady=20)
            
    def delete_patient_record(self):
        selected_item = self.tree_search.focus()
        
        if not selected_item:
            messagebox.showerror("Error", "Please select a patient record to delete.")
            return

        try:
            patient_id = int(selected_item)
            item_values = self.tree_search.item(selected_item, 'values')
            patient_name = item_values[1]
            
            confirm = messagebox.askyesno(
                "Confirm Deletion",
                f"Are you absolutely sure you want to delete the record for {patient_name} (Case No: {item_values[0]}) and ALL associated visit records? This action cannot be undone."
            )

            if confirm:
                conn = sqlite3.connect(self.DB_NAME)
                c = conn.cursor()
                
                c.execute("DELETE FROM visits WHERE patient_id = ?", (patient_id,))
                c.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
                conn.commit()
                conn.close()
                
                self.tree_search.delete(selected_item)
                messagebox.showinfo("Success", f"Patient record for {patient_name} has been successfully deleted.")
                
                self.backup_database(silent=True)
                
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"An error occurred during deletion: {e}")
        except ValueError:
            messagebox.showerror("Error", "Invalid patient selection.")
    
    # ==================== View All Records with Pagination ====================

    def count_all_patients(self):
        conn = sqlite3.connect(self.DB_NAME)
        c = conn.cursor()
        c.execute("SELECT COUNT(id) FROM patients")
        count = c.fetchone()[0]
        conn.close()
        return count

    # ⭐️ MODIFIED: Uses simple SQL sort (fast) and unpads in Python (display) ⭐️
    def load_all_records(self, page_number):
        self.total_records = self.count_all_patients()
        self.total_pages = math.ceil(self.total_records / self.RECORDS_PER_PAGE)
        
        if self.total_records == 0:
            self.current_page = 1
            self.tree_all.delete(*self.tree_all.get_children())
            self.lbl_pagination.config(text="No Records Found.")
            self.btn_prev.config(state=DISABLED)
            self.btn_next.config(state=DISABLED)
            return

        if page_number < 1:
            page_number = 1
        elif page_number > self.total_pages:
            page_number = self.total_pages

        self.current_page = page_number
        offset = (self.current_page - 1) * self.RECORDS_PER_PAGE

        conn = sqlite3.connect(self.DB_NAME)
        c = conn.cursor()
        
        # Use simple string sort, relying on the fact that case_no is now zero-padded
        c.execute("""
            SELECT id, case_no, name, date, age, gender FROM patients
            ORDER BY case_no ASC 
            LIMIT ? OFFSET ?
        """, (self.RECORDS_PER_PAGE, offset))
        rows = c.fetchall()
        conn.close()

        for row in self.tree_all.get_children():
            self.tree_all.delete(row)
        
        for row in rows:
            patient_id = row[0]
            
            # Create a mutable list for display values
            display_row = list(row[1:])
            
            # Unpad the case_no (which is at index 0 of display_row, index 1 of row)
            display_row[0] = self._unpad_case_no(display_row[0])
            
            self.tree_all.insert("", "end", iid=patient_id, values=display_row)
            
        # Update navigation buttons and label
        self.lbl_pagination.config(text=f"Page {self.current_page} of {self.total_pages} (Total: {self.total_records} Records)")
        
        self.btn_prev.config(state=NORMAL if self.current_page > 1 else DISABLED)
        self.btn_next.config(state=NORMAL if self.current_page < self.total_pages else DISABLED)

    def view_all_page(self):
        self.view_all_frame.columnconfigure(0, weight=1)
        self.view_all_frame.rowconfigure(1, weight=1) 

        # Title uses Primary (Dark Navy)
        tb.Label(self.view_all_frame, text=" All Patient Records (Sorted by Case No)",
                                         font=self.TITLE_FONT, bootstyle="primary").grid(row=0, column=0, pady=10, sticky=N) # <--- Secondary Action Color

        # 1. Treeview Setup (List of Records)
        cols = ("Case No", "Name", "Date", "Age", "Gender")
        self.tree_all = tb.Treeview(self.view_all_frame, columns=cols, show="headings", height=self.RECORDS_PER_PAGE)
        
        self.tree_all.column("#0", width=0, stretch=NO)
        self.tree_all.column("Case No", width=120, anchor=CENTER)
        self.tree_all.column("Date", width=120, anchor=CENTER)
        self.tree_all.column("Age", width=80, anchor=CENTER) 
        self.tree_all.column("Gender", width=100, anchor=CENTER) 
        self.tree_all.column("Name", width=600, anchor=W) 
        
        self.tree_all.heading("Case No", text="Case No", anchor=CENTER)
        self.tree_all.heading("Name", text="Name", anchor=W)
        self.tree_all.heading("Date", text="Date", anchor=CENTER)
        self.tree_all.heading("Age", text="Age", anchor=CENTER)
        self.tree_all.heading("Gender", text="Gender", anchor=CENTER)
                
        self.tree_all.grid(row=1, column=0, pady=10, padx=20, sticky=EW+NS)

        self.tree_all.bind("<Double-1>", self.on_tree_double_click)
        self.tree_all.bind("<Tab>", self.navigate_treeview)
        self.tree_all.bind("<Shift-Tab>", self.navigate_treeview)
        
        # 2. Pagination Controls
        pagination_frame = tb.Frame(self.view_all_frame)
        pagination_frame.grid(row=2, column=0, pady=10, sticky=EW)
        
        pagination_frame.columnconfigure(0, weight=1)
        pagination_frame.columnconfigure(1, weight=0)
        pagination_frame.columnconfigure(2, weight=0)
        pagination_frame.columnconfigure(3, weight=0)
        pagination_frame.columnconfigure(4, weight=1)

        # Previous Button uses Secondary (Neutral Teal)
        self.btn_prev = tb.Button(pagination_frame, text="< Previous Page", bootstyle="info", 
                                          command=lambda: self.load_all_records(self.current_page - 1), state=DISABLED) # <--- Tertiary Action Color
        self.btn_prev.grid(row=0, column=1, padx=10, sticky=E)

        # Page Label uses Primary (Dark Navy)
        self.lbl_pagination = tb.Label(pagination_frame, text="Loading...", font=self.BOLD_FONT, bootstyle="primary") # <--- Secondary Action Color
        self.lbl_pagination.grid(row=0, column=2, padx=20)
        
        # Next Button uses Secondary (Neutral Teal)
        self.btn_next = tb.Button(pagination_frame, text="Next Page >", bootstyle="info", 
                                          command=lambda: self.load_all_records(self.current_page + 1), state=DISABLED) # <--- Tertiary Action Color
        self.btn_next.grid(row=0, column=3, padx=10, sticky=W)


        # 3. Back Button
        tb.Button(self.view_all_frame, text="⬅ Back to Home", bootstyle="danger",
                     command=lambda: self.show_frame(self.home_frame), padding=10).grid(row=3, column=0, pady=20)


# ==================== Main Execution ====================
# ==================== Main Execution ====================
if __name__ == '__main__':
    # Use 'flatly' theme as it provides good contrast and is professional.
    app_root = tb.Window(themename="flatly") 
    
    # 1. Maximize the window immediately
    app_root.state('zoomed') # Maximizes the window on Windows/Linux
    # For macOS, 'zoomed' often doesn't work; 'fullscreen' can be used, but 'zoomed' is standard for maximization.
    
    app = PatientManagerApp(app_root)
    
    # 2. Set initial focus after the GUI is fully rendered (using after)
    # The "Add New Patient" button is the first child of the home_frame, located at index 1 of the home_frame's children.
    def set_initial_focus():
        # home_frame.winfo_children() -> [Title Label, Add Button, Search Button, View All Button]
        add_new_patient_button = app.home_frame.winfo_children()[1]
        add_new_patient_button.focus_set()

    # Schedule the focus change shortly after the mainloop starts drawing (100ms delay)
    app_root.after(100, set_initial_focus)
    
    app_root.mainloop()