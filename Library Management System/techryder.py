"""

guide prpared by TechRyder Python Expert

Cinobaka  Library Management System (single-file)
- GUI: tkinter
- DB: sqlite3 (local file 'hwedza_library.db')
- Two roles: admin and student
- Features:
    Admin:
      - login
      - upload/add books
      - register student
      - give (issue) book to student and record transaction
      - clear (mark return)
      - view databases (books, students, transactions)
    Student:
      - login via unique ID
      - check if book collected
      - return a book
      - view available books
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from datetime import datetime
import os
import uuid
import functools

# -----------------------
# Configuration & colors
# -----------------------
DB_FILENAME = "hwedza_library.db"

# Modern color desigs 0774861688 TechRyder

COLORS = {
    "bg": "#0f1724",
    "panel": "#0b1220",
    "accent": "#06b6d4",
    "accent2": "#7c3aed",
    "muted": "#94a3b8",
    "success": "#10b981",
    "danger": "#ef4444",
    "card": "#0d1a26",
    "white": "#ffffff"
}

# Admin default passwords

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# -----------------------
# Database helpers
# -----------------------

def init_db():
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    # Students: unique student_id, name, class, email (optional)
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE,
            name TEXT,
            class TEXT,
            email TEXT,
            registered_at TEXT
        )
    ''')
    # Books: unique book_id, title, author, copies, category

    c.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT UNIQUE,
            title TEXT,
            author TEXT,
            copies INTEGER,
            category TEXT,
            uploaded_at TEXT
        )
    ''')
    # Transactions: issue/return records
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            txn_id TEXT UNIQUE,
            student_id TEXT,
            book_id TEXT,
            action TEXT, -- issued or returned
            timestamp TEXT,
            notes TEXT
        )
    ''')
    # Admins table
    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    # Insert default admin if not exists
    c.execute('SELECT * FROM admins WHERE username = ?', (ADMIN_USERNAME,))
    if not c.fetchone():
        c.execute('INSERT INTO admins (username, password) VALUES (?, ?)', (ADMIN_USERNAME, ADMIN_PASSWORD))
    conn.commit()
    conn.close()

def db_execute(query, params=(), fetch=False, many=False):
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    if many:
        c.executemany(query, params)
        conn.commit()
        conn.close()
        return None
    else:
        c.execute(query, params)
        if fetch:
            rows = c.fetchall()
            conn.close()
            return rows
        else:
            conn.commit()
            conn.close()
            return None

# -----------------------
# Utility helpers
# -----------------------
def gen_id(prefix="ID"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# -----------------------
# App GUI or  page design by carol m
# -----------------------
class HwedzaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Hwedza Library Management System By Makoni T")
        self.geometry("1000x650")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)

        # For "animation" we manage frames on a stacked container
        self.container = tk.Frame(self, bg=COLORS["bg"])
        self.container.place(relwidth=1, relheight=1)

        # Current user context
        self.current_user = None  # {'role': 'admin'/'student', 'id':..., 'name':...}

        # Initialize DB
        init_db()

        # Build frames
        self.frames = {}
        for F in (WelcomeFrame, AdminLoginFrame, StudentLoginFrame, AdminDashboard, StudentDashboard):
            frame = F(parent=self.container, controller=self)
            self.frames[F.__name__] = frame
            frame.place(relwidth=1, relheight=1)
        self.show_frame("WelcomeFrame")

        # small top bar with title + animated accent
        self.build_top_bar()

    def build_top_bar(self):
        # decorative top bar with small animated gradient block
        bar = tk.Frame(self, bg=COLORS["panel"], height=50)
        bar.place(relx=0, rely=0, relwidth=1)
        title = tk.Label(bar, text="Hwedza Library Management System By Makoni T", bg=COLORS["panel"], fg=COLORS["white"],
                         font=("Inter", 14, "bold"))
        title.pack(side="left", padx=12, pady=8)

        # animated accent - cycles colors
        self.accent = tk.Canvas(bar, width=100, height=10, bg=COLORS["panel"], highlightthickness=0)
        self.accent.pack(side="right", padx=12)
        self._accent_i = 0
        self._accent_colors = [COLORS["accent"], COLORS["accent2"], COLORS["success"], COLORS["muted"]]
        self._animate_accent()

    def _animate_accent(self):
        # simple moving rectangle that changes color
        c = self.accent
        c.delete("all")
        color = self._accent_colors[self._accent_i % len(self._accent_colors)]
        x = (self._accent_i % 20) * 5
        c.create_rectangle(x, 0, x+60, 10, fill=color, width=0)
        self._accent_i += 1
        self.after(120, self._animate_accent)

    def show_frame(self, name, animate=True):
        # Low-cost "slide" animation by shifting frames horizontally
        frame = self.frames[name]
        # bring to front
        for f in self.frames.values():
            f.lower()
        frame.lift()

        if animate:
            # start left outside then animate to 0
            frame.place_configure(relx=-1)
            self._slide_in(frame)
        else:
            frame.place_configure(relx=0)

    def _slide_in(self, frame, step=0):
        # animate frame to slide-in
        if step > 20:
            frame.place_configure(relx=0)
            return
        x = -1 + (step / 20) * 1  # from -1 to 0
        frame.place_configure(relx=x)
        self.after(12, lambda: self._slide_in(frame, step+1))

# -----------------------
# Base frame with styling helpers
# -----------------------
class BaseFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLORS["bg"])
        self.controller = controller

    def card(self, width=720, height=460):
        # return a centered frame that looks like a card
        c = tk.Frame(self, bg=COLORS["card"], bd=0, highlightthickness=0)
        c.place(relx=0.5, rely=0.55, anchor="center", width=width, height=height)
        return c

    def header_label(self, parent, text):
        return tk.Label(parent, text=text, bg=COLORS["card"], fg=COLORS["white"],
                        font=("Inter", 16, "bold"))

    def muted_label(self, parent, text):
        return tk.Label(parent, text=text, bg=COLORS["card"], fg=COLORS["muted"],
                        font=("Inter", 10))

    def accent_button(self, parent, text, command=None):
        btn = tk.Button(parent, text=text, bg=COLORS["accent"], fg=COLORS["bg"],
                        activebackground=COLORS["accent2"], activeforeground=COLORS["white"],
                        font=("Inter", 10, "bold"), bd=0, command=command)
        # hover
        btn.bind("<Enter>", lambda e: btn.config(bg=COLORS["accent2"]))
        btn.bind("<Leave>", lambda e: btn.config(bg=COLORS["accent"]))
        return btn

    def danger_button(self, parent, text, command=None):
        btn = tk.Button(parent, text=text, bg=COLORS["danger"], fg=COLORS["white"],
                        activebackground="#f87171", font=("Inter", 10, "bold"), bd=0, command=command)
        btn.bind("<Enter>", lambda e: btn.config(bg="#f97373"))
        btn.bind("<Leave>", lambda e: btn.config(bg=COLORS["danger"]))
        return btn

# -----------------------
# Welcome Frame by TechRyder
# -----------------------
class WelcomeFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        # Background large title
        t = tk.Label(self, text="Transforming Into Digital Systems", bg=COLORS["bg"], fg=COLORS["muted"],
                     font=("Inter", 34, "bold"))
        t.place(relx=0.12, rely=0.22)

        subtitle = tk.Label(self, text="Manage \ntextbooks, \nquestion \npapers \nand novels.\nAdmins and \nStudents access.",
                            bg=COLORS["bg"], fg=COLORS["muted"], font=("Inter", 12))
        subtitle.place(relx=0.12, rely=0.36)

        card = self.card(width=520, height=320)
        title = self.header_label(card, "Welcome")
        title.pack(pady=(18, 6))

        self.muted_label(card, "Choose your role to continue").pack()

        btn_admin = self.accent_button(card, "Admin Login", command=lambda: controller.show_frame("AdminLoginFrame"))
        btn_admin.pack(pady=(28, 8), ipadx=10, ipady=6)

        btn_student = self.accent_button(card, "Student Login", command=lambda: controller.show_frame("StudentLoginFrame"))
        btn_student.pack(ipadx=10, ipady=6)

        foot = tk.Label(card, text="Built with ❤️ — TechRyder", bg=COLORS["card"], fg=COLORS["muted"], font=("Inter", 9))
        foot.pack(side="bottom", pady=12)

# -----------------------
# Admin Login Frame
# -----------------------
class AdminLoginFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        card = self.card(500, 320)
        title = self.header_label(card, "Admin Login")
        title.pack(pady=(18, 6))

        self.muted_label(card, "Enter admin credentials").pack()

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        f = tk.Frame(card, bg=COLORS["card"])
        f.pack(pady=12)

        tk.Label(f, text="Username", bg=COLORS["card"], fg=COLORS["muted"]).grid(row=0, column=0, sticky="w")
        tk.Entry(f, textvariable=self.username_var, width=30).grid(row=1, column=0, pady=6)

        tk.Label(f, text="Password", bg=COLORS["card"], fg=COLORS["muted"]).grid(row=2, column=0, sticky="w")
        tk.Entry(f, textvariable=self.password_var, show="*", width=30).grid(row=3, column=0, pady=6)

        btn_login = self.accent_button(card, "Login", command=self.login)
        btn_login.pack(pady=(8, 6), ipadx=4, ipady=6)

        back = tk.Button(card, text="Back", bg=COLORS["card"], fg=COLORS["muted"], bd=0,
                         command=lambda: controller.show_frame("WelcomeFrame"))
        back.pack(side="left", padx=12, pady=10)

    def login(self):
        u = self.username_var.get().strip()
        p = self.password_var.get().strip()
        if not u or not p:
            messagebox.showwarning("Missing", "Please enter username and password")
            return
        res = db_execute("SELECT * FROM admins WHERE username=? AND password=?", (u, p), fetch=True)
        if res:
            self.controller.current_user = {"role": "admin", "username": u}
            messagebox.showinfo("Welcome", f"Welcome admin {u}")
            self.username_var.set("")
            self.password_var.set("")
            self.controller.show_frame("AdminDashboard")
        else:
            messagebox.showerror("Denied", "Incorrect credentials")

# -----------------------
# Student Login Frame
# -----------------------
class StudentLoginFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        card = self.card(500, 320)
        title = self.header_label(card, "Student Login")
        title.pack(pady=(18, 6))

        self.muted_label(card, "Login using your unique student ID").pack()

        self.student_id_var = tk.StringVar()
        f = tk.Frame(card, bg=COLORS["card"])
        f.pack(pady=12)
        tk.Label(f, text="Student ID", bg=COLORS["card"], fg=COLORS["muted"]).grid(row=0, column=0, sticky="w")
        tk.Entry(f, textvariable=self.student_id_var, width=30).grid(row=1, column=0, pady=6)

        btn_login = self.accent_button(card, "Login", command=self.login)
        btn_login.pack(pady=(8, 6), ipadx=4, ipady=6)

        back = tk.Button(card, text="Back", bg=COLORS["card"], fg=COLORS["muted"], bd=0,
                         command=lambda: controller.show_frame("WelcomeFrame"))
        back.pack(side="left", padx=12, pady=10)

    def login(self):
        sid = self.student_id_var.get().strip()
        if not sid:
            messagebox.showwarning("Missing", "Please enter your student ID")
            return
        res = db_execute("SELECT student_id, name FROM students WHERE student_id=?", (sid,), fetch=True)
        if res:
            name = res[0][1]
            self.controller.current_user = {"role": "student", "student_id": sid, "name": name}
            self.student_id_var.set("")
            messagebox.showinfo("Welcome", f"Welcome {name}")
            self.controller.show_frame("StudentDashboard")
        else:
            messagebox.showerror("Not found", "Student ID not found. Contact admin to register.")

# -----------------------
# Admin Dashboard or panel by F musanhu
# -----------------------
class AdminDashboard(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        # left column menu
        menu = tk.Frame(self, bg=COLORS["panel"], width=220)
        menu.place(relx=0, rely=0.08, relheight=0.92)
        tk.Label(menu, text="Admin", bg=COLORS["panel"], fg=COLORS["white"], font=("Inter", 12, "bold")).pack(pady=10)
        # menu buttons
        btns = [
            ("Register Student", self.register_student),
            ("Upload / Add Book", self.add_book),
            ("Issue Book to Student", self.issue_book),
            ("Clear Return (Record Return)", self.return_book),
            ("View Databases", self.view_databases),
            ("Sign out", self.sign_out)
        ]
        for t, cmd in btns:
            b = tk.Button(menu, text=t, bg=COLORS["card"], fg=COLORS["white"], bd=0, width=22, height=2, command=cmd)
            b.pack(pady=6, padx=6)

        # main area: dynamic content container
        self.main = tk.Frame(self, bg=COLORS["bg"])
        self.main.place(relx=0.22, rely=0.08, relwidth=0.78, relheight=0.92)

        welcome = self.header_label(self.main, "Admin Dashboard")
        welcome.pack(anchor="nw", pady=(10, 0), padx=12)
        self.info = tk.Label(self.main, text="Use the menu on the left to manage students and books.",
                             bg=COLORS["bg"], fg=COLORS["muted"], font=("Inter", 11))
        self.info.pack(anchor="nw", padx=12, pady=(6, 12))

        # quick stats area
        self.stats_frame = tk.Frame(self.main, bg=COLORS["card"])
        self.stats_frame.place(relx=0.02, rely=0.12, relwidth=0.96, relheight=0.78)
        self.update_stats()

    def update_stats(self):
        # clear
        for w in self.stats_frame.winfo_children():
            w.destroy()
        # fetch numbers
        students = db_execute("SELECT COUNT(*) FROM students", fetch=True)[0][0]
        books = db_execute("SELECT SUM(copies) FROM books", fetch=True)[0][0] or 0
        issued = db_execute("SELECT COUNT(*) FROM transactions WHERE action='issued'", fetch=True)[0][0]
        returned = db_execute("SELECT COUNT(*) FROM transactions WHERE action='returned'", fetch=True)[0][0]

        # display as cards
        info_items = [
            ("Students Registered", students),
            ("Library Copies (total)", books),
            ("Times Issued", issued),
            ("Times Returned", returned)
        ]
        for idx, (label, val) in enumerate(info_items):
            card = tk.Frame(self.stats_frame, bg=COLORS["panel"], bd=0)
            card.place(relx=0.01 + (idx*0.245), rely=0.05, relwidth=0.235, relheight=0.25)
            tk.Label(card, text=str(val), bg=COLORS["panel"], fg=COLORS["accent"], font=("Inter", 18, "bold")).pack(pady=8)
            tk.Label(card, text=label, bg=COLORS["panel"], fg=COLORS["muted"], font=("Inter", 9)).pack()

        # table listing recent transactions
        tk.Label(self.stats_frame, text="Recent Transactions", bg=COLORS["card"], fg=COLORS["white"], font=("Inter", 12, "bold")).place(relx=0.02, rely=0.34)
        cols = ("txn_id", "student", "book", "action", "time")
        tree = ttk.Treeview(self.stats_frame, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c.title())
            tree.column(c, width=140 if c!="time" else 220, anchor="w")
        tree.place(relx=0.02, rely=0.42, relwidth=0.96, relheight=0.52)
        rows = db_execute("SELECT txn_id, student_id, book_id, action, timestamp FROM transactions ORDER BY id DESC LIMIT 10", fetch=True)
        for r in rows:
            tree.insert("", "end", values=r)

    # --------------------
    # Admin actions
    # --------------------
    def register_student(self):
        # popup form
        form = tk.Toplevel(self)
        form.title("Register Student")
        form.geometry("420x320")
        form.configure(bg=COLORS["bg"])
        tk.Label(form, text="Register New Student", bg=COLORS["bg"], fg=COLORS["white"], font=("Inter", 12, "bold")).pack(pady=8)
        name_var = tk.StringVar()
        sid_var = tk.StringVar()
        class_var = tk.StringVar()
        email_var = tk.StringVar()
        tk.Label(form, text="Full Name", bg=COLORS["bg"], fg=COLORS["muted"]).pack(anchor="w", padx=12)
        tk.Entry(form, textvariable=name_var, width=40).pack(padx=12, pady=6)
        tk.Label(form, text="Student ID (unique)", bg=COLORS["bg"], fg=COLORS["muted"]).pack(anchor="w", padx=12)
        tk.Entry(form, textvariable=sid_var, width=40).pack(padx=12, pady=6)
        tk.Label(form, text="Class", bg=COLORS["bg"], fg=COLORS["muted"]).pack(anchor="w", padx=12)
        tk.Entry(form, textvariable=class_var, width=40).pack(padx=12, pady=6)
        tk.Label(form, text="Email (optional)", bg=COLORS["bg"], fg=COLORS["muted"]).pack(anchor="w", padx=12)
        tk.Entry(form, textvariable=email_var, width=40).pack(padx=12, pady=6)

        def save():
            name = name_var.get().strip()
            sid = sid_var.get().strip()
            cl = class_var.get().strip()
            email = email_var.get().strip()
            if not name or not sid:
                messagebox.showwarning("Missing", "Name and student ID are required")
                return
            try:
                db_execute("INSERT INTO students (student_id, name, class, email, registered_at) VALUES (?, ?, ?, ?, ?)",
                           (sid, name, cl, email, now()))
                messagebox.showinfo("Saved", f"Student {name} registered with ID {sid}")
                form.destroy()
                self.update_stats()
            except Exception as e:
                messagebox.showerror("Error", f"Could not register student: {e}")

        tk.Button(form, text="Save", bg=COLORS["accent"], fg=COLORS["white"], bd=0, command=save).pack(pady=12)

    def add_book(self):
        form = tk.Toplevel(self)
        form.title("Upload / Add Book")
        form.geometry("420x340")
        form.configure(bg=COLORS["bg"])
        tk.Label(form, text="Add Book to Library", bg=COLORS["bg"], fg=COLORS["white"], font=("Inter", 12, "bold")).pack(pady=8)
        title_var = tk.StringVar()
        author_var = tk.StringVar()
        copies_var = tk.IntVar(value=1)
        category_var = tk.StringVar()
        tk.Label(form, text="Title", bg=COLORS["bg"], fg=COLORS["muted"]).pack(anchor="w", padx=12)
        tk.Entry(form, textvariable=title_var, width=40).pack(padx=12, pady=6)
        tk.Label(form, text="Author", bg=COLORS["bg"], fg=COLORS["muted"]).pack(anchor="w", padx=12)
        tk.Entry(form, textvariable=author_var, width=40).pack(padx=12, pady=6)
        tk.Label(form, text="Copies", bg=COLORS["bg"], fg=COLORS["muted"]).pack(anchor="w", padx=12)
        tk.Entry(form, textvariable=copies_var, width=12).pack(padx=12, pady=6)
        tk.Label(form, text="Category (e.g. O-Level, A-Level, Novel)", bg=COLORS["bg"], fg=COLORS["muted"]).pack(anchor="w", padx=12)
        tk.Entry(form, textvariable=category_var, width=40).pack(padx=12, pady=6)

        def save_book():
            title = title_var.get().strip()
            author = author_var.get().strip()
            copies = copies_var.get()
            cat = category_var.get().strip()
            if not title:
                messagebox.showwarning("Missing", "Enter a book title")
                return
            if copies <= 0:
                messagebox.showwarning("Invalid", "Copies must be >= 1")
                return
            book_id = gen_id("BOOK")
            try:
                # if a book with same title exists, just increment copies (simple merge)
                existing = db_execute("SELECT id, copies FROM books WHERE title=? AND author=?", (title, author), fetch=True)
                if existing:
                    db_execute("UPDATE books SET copies = copies + ? WHERE id = ?", (copies, existing[0][0]))
                else:
                    db_execute("INSERT INTO books (book_id, title, author, copies, category, uploaded_at) VALUES (?, ?, ?, ?, ?, ?)",
                               (book_id, title, author, copies, cat, now()))
                messagebox.showinfo("Saved", f"Book '{title}' added/updated.")
                form.destroy()
                self.update_stats()
            except Exception as e:
                messagebox.showerror("Error", f"Could not add book: {e}")

        tk.Button(form, text="Save Book", bg=COLORS["accent"], fg=COLORS["white"], bd=0, command=save_book).pack(pady=12)

    def issue_book(self):
        # Issue a book to student (reduce copies and record transaction)
        form = tk.Toplevel(self)
        form.title("Issue Book")
        form.geometry("520x380")
        form.configure(bg=COLORS["bg"])
        tk.Label(form, text="Issue Book to Student", bg=COLORS["bg"], fg=COLORS["white"], font=("Inter", 12, "bold")).pack(pady=8)

        student_var = tk.StringVar()
        book_var = tk.StringVar()
        note_var = tk.StringVar()

        tk.Label(form, text="Student ID", bg=COLORS["bg"], fg=COLORS["muted"]).pack(anchor="w", padx=12)
        tk.Entry(form, textvariable=student_var, width=36).pack(padx=12, pady=6)
        tk.Label(form, text="Select Book (book_id)", bg=COLORS["bg"], fg=COLORS["muted"]).pack(anchor="w", padx=12)
        # list available books in dropdown as "book_id - title (copies)"
        books = db_execute("SELECT book_id, title, copies FROM books WHERE copies>0", fetch=True)
        options = [f"{b[0]} - {b[1]} ({b[2]} copies)" for b in books] or ["No books available"]
        book_cb = ttk.Combobox(form, values=options, textvariable=book_var, width=46)
        book_cb.pack(padx=12, pady=6)
        tk.Label(form, text="Note (optional)", bg=COLORS["bg"], fg=COLORS["muted"]).pack(anchor="w", padx=12)
        tk.Entry(form, textvariable=note_var, width=46).pack(padx=12, pady=6)

        def do_issue():
            sid = student_var.get().strip()
            book_sel = book_var.get().strip()
            note = note_var.get().strip()
            if not sid or not book_sel:
                messagebox.showwarning("Missing", "Enter student ID and select a book")
                return
            if " - " not in book_sel:
                messagebox.showerror("Invalid", "Please select a valid book")
                return
            book_id = book_sel.split(" - ")[0]
            # verify student exists
            s = db_execute("SELECT * FROM students WHERE student_id=?", (sid,), fetch=True)
            if not s:
                messagebox.showerror("Not found", "Student not found")
                return
            # verify copies
            b = db_execute("SELECT id, copies, title FROM books WHERE book_id=?", (book_id,), fetch=True)
            if not b or b[0][1] <= 0:
                messagebox.showerror("Unavailable", "Book not available")
                return
            # reduce copies and record transaction
            try:
                db_execute("UPDATE books SET copies = copies - 1 WHERE book_id=?", (book_id,))
                txn_id = gen_id("TXN")
                db_execute("INSERT INTO transactions (txn_id, student_id, book_id, action, timestamp, notes) VALUES (?, ?, ?, ?, ?, ?)",
                           (txn_id, sid, book_id, "issued", now(), note))
                messagebox.showinfo("Issued", f"Book '{b[0][2]}' issued to {sid}")
                form.destroy()
                self.update_stats()
            except Exception as e:
                messagebox.showerror("Error", f"Could not issue book: {e}")

        tk.Button(form, text="Issue Book", bg=COLORS["accent"], fg=COLORS["white"], bd=0, command=do_issue).pack(pady=12)

    def return_book(self):
        # admin records return (increase copies, record transaction)
        form = tk.Toplevel(self)
        form.title("Record Return")
        form.geometry("520x320")
        form.configure(bg=COLORS["bg"])
        tk.Label(form, text="Record Book Return", bg=COLORS["bg"], fg=COLORS["white"], font=("Inter", 12, "bold")).pack(pady=8)

        student_var = tk.StringVar()
        book_var = tk.StringVar()
        note_var = tk.StringVar()

        tk.Label(form, text="Student ID", bg=COLORS["bg"], fg=COLORS["muted"]).pack(anchor="w", padx=12)
        tk.Entry(form, textvariable=student_var, width=36).pack(padx=12, pady=6)

        tk.Label(form, text="Returned Book (book_id)", bg=COLORS["bg"], fg=COLORS["muted"]).pack(anchor="w", padx=12)
        # list all books with their id
        books = db_execute("SELECT book_id, title FROM books", fetch=True)
        options = [f"{b[0]} - {b[1]}" for b in books] or ["No books found"]
        book_cb = ttk.Combobox(form, values=options, textvariable=book_var, width=46)
        book_cb.pack(padx=12, pady=6)
        tk.Label(form, text="Note (optional)", bg=COLORS["bg"], fg=COLORS["muted"]).pack(anchor="w", padx=12)
        tk.Entry(form, textvariable=note_var, width=46).pack(padx=12, pady=6)

        def do_return():
            sid = student_var.get().strip()
            book_sel = book_var.get().strip()
            note = note_var.get().strip()
            if not sid or not book_sel:
                messagebox.showwarning("Missing", "Enter student ID and select a book")
                return
            book_id = book_sel.split(" - ")[0]
            # check student exists
            if not db_execute("SELECT * FROM students WHERE student_id=?", (sid,), fetch=True):
                messagebox.showerror("Not found", "Student not found")
                return
            # increment copies
            try:
                db_execute("UPDATE books SET copies = copies + 1 WHERE book_id=?", (book_id,))
                txn_id = gen_id("TXN")
                db_execute("INSERT INTO transactions (txn_id, student_id, book_id, action, timestamp, notes) VALUES (?, ?, ?, ?, ?, ?)",
                           (txn_id, sid, book_id, "returned", now(), note))
                messagebox.showinfo("Returned", f"Return recorded for student {sid}")
                form.destroy()
                self.update_stats()
            except Exception as e:
                messagebox.showerror("Error", f"Could not record return: {e}")

        tk.Button(form, text="Record Return", bg=COLORS["accent"], fg=COLORS["white"], bd=0, command=do_return).pack(pady=12)

    def view_databases(self):
        # open a window with tabs for Students, Books, Transactions
        form = tk.Toplevel(self)
        form.title("View Databases")
        form.geometry("920x520")
        form.configure(bg=COLORS["bg"])
        tab = ttk.Notebook(form)
        tab.pack(fill="both", expand=True, padx=8, pady=8)

        # Students tab
        sframe = tk.Frame(tab, bg=COLORS["card"])
        tab.add(sframe, text="Students")
        cols = ("student_id", "name", "class", "email", "registered_at")
        tree = ttk.Treeview(sframe, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c.title())
            tree.column(c, width=150 if c!="registered_at" else 200, anchor="w")
        tree.pack(fill="both", expand=True, padx=8, pady=8)
        rows = db_execute("SELECT student_id, name, class, email, registered_at FROM students ORDER BY id DESC", fetch=True)
        for r in rows:
            tree.insert("", "end", values=r)

        # Books tab
        bframe = tk.Frame(tab, bg=COLORS["card"])
        tab.add(bframe, text="Books")
        cols = ("book_id", "title", "author", "copies", "category", "uploaded_at")
        tree2 = ttk.Treeview(bframe, columns=cols, show="headings")
        for c in cols:
            tree2.heading(c, text=c.title())
            tree2.column(c, width=120 if c!="title" else 300, anchor="w")
        tree2.pack(fill="both", expand=True, padx=8, pady=8)
        rows = db_execute("SELECT book_id, title, author, copies, category, uploaded_at FROM books ORDER BY id DESC", fetch=True)
        for r in rows:
            tree2.insert("", "end", values=r)

        # Transactions tab
        tframe = tk.Frame(tab, bg=COLORS["card"])
        tab.add(tframe, text="Transactions")
        cols = ("txn_id", "student_id", "book_id", "action", "timestamp", "notes")
        tree3 = ttk.Treeview(tframe, columns=cols, show="headings")
        for c in cols:
            tree3.heading(c, text=c.title())
            tree3.column(c, width=140 if c!="notes" else 240, anchor="w")
        tree3.pack(fill="both", expand=True, padx=8, pady=8)
        rows = db_execute("SELECT txn_id, student_id, book_id, action, timestamp, notes FROM transactions ORDER BY id DESC", fetch=True)
        for r in rows:
            tree3.insert("", "end", values=r)

    def sign_out(self):
        self.controller.current_user = None
        self.controller.show_frame("WelcomeFrame")

# -----------------------
# Student Dashboard
# -----------------------
class StudentDashboard(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        # left menu
        menu = tk.Frame(self, bg=COLORS["panel"], width=220)
        menu.place(relx=0, rely=0.08, relheight=0.92)
        tk.Label(menu, text="Student", bg=COLORS["panel"], fg=COLORS["white"], font=("Inter", 12, "bold")).pack(pady=10)
        btns = [
            ("Check Collected Books", self.check_collected),
            ("Return a Book", self.return_book_student),
            ("View Available Books", self.view_books),
            ("Sign out", self.sign_out)
        ]
        for t, cmd in btns:
            b = tk.Button(menu, text=t, bg=COLORS["card"], fg=COLORS["white"], bd=0, width=22, height=2, command=cmd)
            b.pack(pady=6, padx=6)

        self.main = tk.Frame(self, bg=COLORS["bg"])
        self.main.place(relx=0.22, rely=0.08, relwidth=0.78, relheight=0.92)

        self.welcome_label = self.header_label(self.main, "Student Dashboard")
        self.welcome_label.pack(anchor="nw", padx=12, pady=(10, 0))
        self.info = tk.Label(self.main, text="Welcome. Use the menu to check collections, return books or view the catalogue.",
                             bg=COLORS["bg"], fg=COLORS["muted"], font=("Inter", 11))
        self.info.pack(anchor="nw", padx=12, pady=(6, 12))
        self.update_welcome()

    def update_welcome(self):
        cu = self.controller.current_user
        if cu and cu.get("role") == "student":
            name = cu.get("name")
            sid = cu.get("student_id")
            self.welcome_label.config(text=f"Welcome {name} ({sid})")
        else:
            self.welcome_label.config(text="Student Dashboard")

    # actions
    def check_collected(self):
        cu = self.controller.current_user
        if not cu or cu.get("role") != "student":
            messagebox.showerror("Error", "Student not logged in")
            return
        sid = cu.get("student_id")
        rows = db_execute("SELECT txn_id, book_id, action, timestamp FROM transactions WHERE student_id=? ORDER BY id DESC", (sid,), fetch=True)
        form = tk.Toplevel(self)
        form.title("My Transactions")
        form.geometry("720x420")
        form.configure(bg=COLORS["bg"])
        tk.Label(form, text=f"Transactions for {sid}", bg=COLORS["bg"], fg=COLORS["white"], font=("Inter", 12, "bold")).pack(pady=8)
        cols = ("txn_id", "book_id", "action", "timestamp")
        tree = ttk.Treeview(form, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c.title())
            tree.column(c, width=160, anchor="w")
        tree.pack(fill="both", expand=True, padx=8, pady=8)
        for r in rows:
            tree.insert("", "end", values=r)

        # show if currently has any book not returned: compute by tallying issued vs returned per book
        issued = db_execute("SELECT book_id, COUNT(*) FROM transactions WHERE student_id=? AND action='issued' GROUP BY book_id", (sid,), fetch=True)
        returned = db_execute("SELECT book_id, COUNT(*) FROM transactions WHERE student_id=? AND action='returned' GROUP BY book_id", (sid,), fetch=True)
        ret_map = {r[0]: r[1] for r in returned}
        current = []
        for book_id, cnt in issued:
            ret_cnt = ret_map.get(book_id, 0)
            if cnt > ret_cnt:
                # student still has (cnt - ret_cnt) copies of this book
                current.append((book_id, cnt - ret_cnt))
        if current:
            msg = "Books currently collected:\n" + "\n".join([f"{b[0]} (x{b[1]})" for b in current])
            tk.Label(form, text=msg, bg=COLORS["bg"], fg=COLORS["accent"], font=("Inter", 10, "bold")).pack(pady=6)
        else:
            tk.Label(form, text="No books currently collected.", bg=COLORS["bg"], fg=COLORS["muted"]).pack(pady=6)

    def return_book_student(self):
        cu = self.controller.current_user
        if not cu or cu.get("role") != "student":
            messagebox.showerror("Error", "Student not logged in")
            return
        sid = cu.get("student_id")
        # compute currently held books
        issued = db_execute("SELECT book_id, COUNT(*) FROM transactions WHERE student_id=? AND action='issued' GROUP BY book_id", (sid,), fetch=True)
        returned = db_execute("SELECT book_id, COUNT(*) FROM transactions WHERE student_id=? AND action='returned' GROUP BY book_id", (sid,), fetch=True)
        ret_map = {r[0]: r[1] for r in returned}
        current = []
        for book_id, cnt in issued:
            ret_cnt = ret_map.get(book_id, 0)
            if cnt > ret_cnt:
                current.append((book_id, cnt - ret_cnt))
        if not current:
            messagebox.showinfo("Nothing", "You have no books to return.")
            return
        form = tk.Toplevel(self)
        form.title("Return Book")
        form.geometry("520x300")
        form.configure(bg=COLORS["bg"])
        tk.Label(form, text="Return a Book", bg=COLORS["bg"], fg=COLORS["white"], font=("Inter", 12, "bold")).pack(pady=8)
        options = [f"{b[0]} (x{b[1]})" for b in current]
        book_var = tk.StringVar()
        book_cb = ttk.Combobox(form, values=options, textvariable=book_var, width=46)
        book_cb.pack(padx=12, pady=12)
        note_var = tk.StringVar()
        tk.Entry(form, textvariable=note_var, width=46).pack(pady=6, padx=12)
        def do_return():
            sel = book_var.get().strip()
            if not sel:
                messagebox.showwarning("Missing", "Select a book to return")
                return
            book_id = sel.split(" ")[0]
            try:
                # increment copies
                db_execute("UPDATE books SET copies = copies + 1 WHERE book_id=?", (book_id,))
                txn_id = gen_id("TXN")
                db_execute("INSERT INTO transactions (txn_id, student_id, book_id, action, timestamp, notes) VALUES (?, ?, ?, ?, ?, ?)",
                           (txn_id, sid, book_id, "returned", now(), note_var.get()))
                messagebox.showinfo("Returned", "Return recorded. Thank you.")
                form.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Could not return book: {e}")
        tk.Button(form, text="Return Book", bg=COLORS["accent"], fg=COLORS["white"], bd=0, command=do_return).pack(pady=12)

    def view_books(self):
        form = tk.Toplevel(self)
        form.title("Available Books")
        form.geometry("820x420")
        form.configure(bg=COLORS["bg"])
        tk.Label(form, text="Library Catalogue", bg=COLORS["bg"], fg=COLORS["white"], font=("Inter", 12, "bold")).pack(pady=8)
        cols = ("book_id", "title", "author", "copies", "category")
        tree = ttk.Treeview(form, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c.title())
            tree.column(c, width=140 if c!="title" else 300, anchor="w")
        tree.pack(fill="both", expand=True, padx=8, pady=8)
        rows = db_execute("SELECT book_id, title, author, copies, category FROM books ORDER BY title", fetch=True)
        for r in rows:
            tree.insert("", "end", values=r)

    def sign_out(self):
        self.controller.current_user = None
        self.controller.show_frame("WelcomeFrame")

# -----------------------
# Run App
# -----------------------
if __name__ == "__main__":
    # ensure DB in place
    init_db()
    app = HwedzaApp()
    app.mainloop()
