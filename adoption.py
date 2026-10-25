import json
import os
import hashlib
import secrets
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, "petlink_data.json")
UPLOAD_DIR = os.path.join(APP_DIR, "pet_photos")
os.makedirs(UPLOAD_DIR, exist_ok=True)

BG = "#eef7f7"
TEAL = "#155b59"
TEAL_DARK = "#104a49"
MINT = "#dff2ef"
WHITE = "#ffffff"
TEXT = "#244b4b"
MUTED = "#6f8d95"
GREEN = "#25a77a"
GOLD = "#e3b64b"
RED = "#d86b70"


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 salt.encode("utf-8"), 180_000).hex()
    return salt, digest


class Database:
    def __init__(self, path=DATA_FILE):
        self.path = path
        if not os.path.exists(path):
            self.data = {
                "users": [], "pets": [], "applications": [], "strays": [],
                "next_pet_id": 1, "next_application_id": 1, "next_stray_id": 1
            }
            self.create_admin()
            self.save()
        else:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, OSError):
                messagebox.showerror("Database error",
                                     "petlink_data.json could not be read. A backup named petlink_data_corrupt.json will be created.")
                try:
                    shutil.copy2(path, path + ".corrupt_backup")
                except OSError:
                    pass
                self.data = {"users": [], "pets": [], "applications": [], "strays": [],
                             "next_pet_id": 1, "next_application_id": 1, "next_stray_id": 1}
                self.create_admin()
                self.save()
            for key, default in (("users", []), ("pets", []), ("applications", []),
                                 ("strays", []), ("next_pet_id", 1),
                                 ("next_application_id", 1), ("next_stray_id", 1)):
                self.data.setdefault(key, default)
            if not any(u.get("role") == "admin" for u in self.data["users"]):
                self.create_admin()
                self.save()

    def create_admin(self):
        if any(u.get("username") == "admin" for u in self.data["users"]):
            return
        salt, digest = hash_password("Admin12345")
        self.data["users"].append({
            "username": "admin", "display_name": "Administrator",
            "email": "admin@petlink.local", "phone": "", "location": "",
            "role": "admin", "salt": salt, "password_hash": digest,
            "created_at": now()
        })

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)

    def user(self, username):
        return next((u for u in self.data["users"]
                     if u["username"].lower() == username.lower()), None)

    def authenticate(self, username, password):
        u = self.user(username.strip())
        if not u:
            return None
        _, digest = hash_password(password, u["salt"])
        return u if secrets.compare_digest(digest, u["password_hash"]) else None

    def register(self, username, display_name, email, phone, location, password):
        username = username.strip()
        if len(username) < 3:
            raise ValueError("Username must contain at least 3 characters.")
        if self.user(username):
            raise ValueError("That username is already taken.")
        if len(password) < 8 or len(password) > 13:
            raise ValueError("Password must be 8–13 characters long.")
        if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
            raise ValueError("Password must include at least one letter and one number.")
        salt, digest = hash_password(password)
        u = {"username": username, "display_name": display_name.strip() or username,
             "email": email.strip(), "phone": phone.strip(), "location": location.strip(),
             "role": "user", "salt": salt, "password_hash": digest, "created_at": now()}
        self.data["users"].append(u)
        self.save()
        return u

    def verify_password(self, user, password):
        _, digest = hash_password(password, user["salt"])
        return secrets.compare_digest(digest, user["password_hash"])

    def change_password(self, user, old, new):
        if not self.verify_password(user, old):
            raise ValueError("Current password is incorrect.")
        if len(new) < 8 or len(new) > 13 or not any(c.isalpha() for c in new) or not any(c.isdigit() for c in new):
            raise ValueError("New password must be 8–13 characters and include a letter and a number.")
        user["salt"], user["password_hash"] = hash_password(new)
        self.save()


class PetLink(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PetLink: An Online Adoption & Tracking System")
        self.geometry("1320x820")
        self.minsize(980, 650)
        self.configure(bg=BG)
        self.db = Database()
        self.current_user = None
        self.show_password = tk.BooleanVar(value=False)
        self._style()
        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True)
        self.show_login()

    def _style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", rowheight=30, background=WHITE, fieldbackground=WHITE,
                        foreground=TEXT, borderwidth=0, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=MINT, foreground=TEAL_DARK,
                        font=("Segoe UI", 10, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", "#c7e8e2")], foreground=[("selected", TEXT)])
        style.configure("TCombobox", padding=7)
        style.configure("TEntry", padding=7)

    def clear(self):
        for child in self.container.winfo_children():
            child.destroy()

    def button(self, parent, text, command, primary=True, **kwargs):
        return tk.Button(parent, text=text, command=command, cursor="hand2",
                         bg=TEAL if primary else WHITE,
                         fg=WHITE if primary else TEAL,
                         activebackground=TEAL_DARK, activeforeground=WHITE,
                         relief="flat", bd=0, padx=16, pady=9,
                         font=("Segoe UI", 10, "bold"), **kwargs)

    def field(self, parent, label, variable=None, show=None):
        wrap = tk.Frame(parent, bg=parent.cget("bg"))
        wrap.pack(fill="x", pady=6)
        tk.Label(wrap, text=label, bg=parent.cget("bg"), fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))
        entry = ttk.Entry(wrap, textvariable=variable, show=show)
        entry.pack(fill="x", ipady=3)
        return entry

    def show_login(self):
        self.clear()
        page = tk.Frame(self.container, bg=BG)
        page.pack(fill="both", expand=True)
        card = tk.Frame(page, bg=WHITE, padx=42, pady=36, highlightbackground="#d6e8e8", highlightthickness=1)
        card.place(relx=.5, rely=.48, anchor="center", width=440)
        tk.Label(card, text="🐾 PETLINK", bg=WHITE, fg=TEAL,
                 font=("Segoe UI", 27, "bold")).pack(pady=(0, 6))
        tk.Label(card, text="Helping pets find safe and loving homes", bg=WHITE,
                 fg=MUTED, font=("Segoe UI", 10)).pack(pady=(0, 22))
        self.login_user = tk.StringVar()
        self.login_pass = tk.StringVar()
        self.field(card, "Username", self.login_user)
        self.field(card, "Password", self.login_pass, show="•")
        self.login_show = tk.BooleanVar(value=False)
        tk.Checkbutton(card, text="Show password", variable=self.login_show,
                       command=lambda: self._toggle_entry(pass_entry, self.login_show),
                       bg=WHITE, fg=TEXT, activebackground=WHITE).pack(anchor="w", pady=4)
        # Retrieve the password entry from its field wrapper.
        pass_entry = card.winfo_children()[3].winfo_children()[1]
        self.button(card, "Log In", self.login, width=30).pack(fill="x", pady=(14, 8))
        row = tk.Frame(card, bg=WHITE)
        row.pack(fill="x")
        self.button(row, "Create an Account", self.show_register, primary=False).pack(side="left", expand=True, fill="x", padx=(0, 5))
        self.button(row, "Forgot Password", self.show_reset, primary=False).pack(side="left", expand=True, fill="x", padx=(5, 0))
        tk.Label(card, text="Demo admin: admin  |  Password: Admin12345",
                 bg=WHITE, fg=MUTED, font=("Segoe UI", 9)).pack(pady=(18, 0))
        self.bind("<Return>", lambda e: self.login())

    def _toggle_entry(self, entry, var):
        if entry is not None and entry.winfo_exists():
            entry.configure(show="" if var.get() else "•")

    def login(self):
        user = self.db.authenticate(self.login_user.get(), self.login_pass.get())
        if not user:
            messagebox.showerror("Log In", "Incorrect username or password.")
            return
        self.current_user = user
        self.show_dashboard()

    def show_register(self):
        self.clear()
        page = tk.Frame(self.container, bg=BG)
        page.pack(fill="both", expand=True)
        card = tk.Frame(page, bg=WHITE, padx=34, pady=24, highlightbackground="#d6e8e8", highlightthickness=1)
        card.place(relx=.5, rely=.5, anchor="center", width=500)
        tk.Label(card, text="Create your PetLink account", bg=WHITE, fg=TEAL,
                 font=("Segoe UI", 21, "bold")).pack(anchor="w", pady=(0, 12))
        self.reg_vars = {k: tk.StringVar() for k in ("username", "name", "email", "phone", "location", "password", "confirm")}
        for key, label in (("username", "Username"), ("name", "Full name"),
                           ("email", "Email"), ("phone", "Phone"), ("location", "Location"),
                           ("password", "Password (8–13 characters)"), ("confirm", "Confirm password")):
            self.field(card, label, self.reg_vars[key], show="•" if key in ("password", "confirm") else None)
        self.reg_show = tk.BooleanVar(value=False)
        entries = [child.winfo_children()[1] for child in card.winfo_children() if isinstance(child, tk.Frame)]
        tk.Checkbutton(card, text="Show passwords", variable=self.reg_show,
                       command=lambda: [e.configure(show="" if self.reg_show.get() else ("•" if i >= 5 else "")) for i, e in enumerate(entries)],
                       bg=WHITE, fg=TEXT, activebackground=WHITE).pack(anchor="w", pady=5)
        self.button(card, "Create Account", self.register, width=30).pack(fill="x", pady=(10, 6))
        self.button(card, "Back to Log In", self.show_login, primary=False).pack(fill="x")
    def register(self):
        v = self.reg_vars
        if not v["username"].get().strip() or not v["password"].get():
            messagebox.showwarning("Create Account", "Username and password are required.")
            return
        if v["password"].get() != v["confirm"].get():
            messagebox.showerror("Create Account", "Passwords do not match.")
            return
        try:
            self.current_user = self.db.register(v["username"].get(), v["name"].get(), v["email"].get(),
                                                 v["phone"].get(), v["location"].get(), v["password"].get())
        except ValueError as e:
            messagebox.showerror("Create Account", str(e))
            return
        messagebox.showinfo("PetLink", "Account created successfully.")
        self.show_dashboard()

    def show_reset(self):
        self.clear()
        card = tk.Frame(self.container, bg=WHITE, padx=36, pady=30, highlightbackground="#d6e8e8", highlightthickness=1)
        card.place(relx=.5, rely=.5, anchor="center", width=440)
        tk.Label(card, text="Reset Password", bg=WHITE, fg=TEAL, font=("Segoe UI", 22, "bold")).pack(anchor="w", pady=(0, 14))
        self.reset_user = tk.StringVar()
        self.reset_email = tk.StringVar()
        self.reset_new = tk.StringVar()
        self.field(card, "Username", self.reset_user)
        self.field(card, "Registered email", self.reset_email)
        self.field(card, "New password (8–13 characters)", self.reset_new, show="•")
        tk.Label(card, text="For this local demo, your username and email must match your account.", bg=WHITE,
                 fg=MUTED, wraplength=350).pack(anchor="w", pady=8)
        self.button(card, "Reset Password", self.reset_password).pack(fill="x", pady=6)
        self.button(card, "Back to Log In", self.show_login, primary=False).pack(fill="x")

    def reset_password(self):
        u = self.db.user(self.reset_user.get().strip())
        if not u or u.get("email", "").lower() != self.reset_email.get().strip().lower():
            messagebox.showerror("Reset Password", "Username and registered email do not match.")
            return
        new = self.reset_new.get()
        if len(new) < 8 or len(new) > 13 or not any(c.isalpha() for c in new) or not any(c.isdigit() for c in new):
            messagebox.showerror("Reset Password", "Password must be 8–13 characters and include a letter and a number.")
            return
        u["salt"], u["password_hash"] = hash_password(new)
        self.db.save()
        messagebox.showinfo("Reset Password", "Password updated. You can now log in.")
        self.show_login()

    def shell(self, active):
        self.clear()
        self.root_frame = tk.Frame(self.container, bg=BG)
        self.root_frame.pack(fill="both", expand=True)
        nav = tk.Frame(self.root_frame, bg=TEAL_DARK, height=64)
        nav.pack(fill="x")
        nav.pack_propagate(False)
        tk.Label(nav, text="🐾 PETLINK", bg=TEAL_DARK, fg=WHITE,
                 font=("Segoe UI", 20, "bold")).pack(side="left", padx=22)
        links = [("Dashboard", self.show_dashboard), ("Available Pets", self.show_pets),
                 ("Pet Posting", self.show_posting), ("Stray Status", self.show_strays),
                 ("Applications", self.show_applications), ("Profile", self.show_profile)]
        if self.current_user.get("role") == "admin":
            links.insert(5, ("Admin", self.show_admin))
        for label, command in links:
            tk.Button(nav, text=label, command=command, bg=TEAL_DARK,
                      fg=WHITE, activebackground=TEAL, activeforeground=WHITE,
                      relief="flat", bd=0, padx=10, font=("Segoe UI", 10, "bold"),
                      cursor="hand2").pack(side="left", expand=True, fill="x", pady=4)
        tk.Button(nav, text="Log Out", command=self.logout, bg=TEAL_DARK, fg=WHITE,
                  activebackground=RED, relief="flat", bd=0, padx=16,
                  font=("Segoe UI", 10, "bold"), cursor="hand2").pack(side="right", padx=12)
        self.content = tk.Frame(self.root_frame, bg=BG)
        self.content.pack(fill="both", expand=True)
        footer = tk.Label(self.root_frame, text="PETLINK  |  Helping pets find safe and loving homes",
                          bg=BG, fg=MUTED, font=("Segoe UI", 9))
        footer.pack(side="bottom", pady=(4, 10))

    def page_heading(self, title, subtitle=None):
        tk.Label(self.content, text=title, bg=BG, fg=TEAL_DARK,
                 font=("Segoe UI", 23, "bold")).pack(anchor="w", padx=26, pady=(22, 2))
        if subtitle:
            tk.Label(self.content, text=subtitle, bg=BG, fg=MUTED,
                     font=("Segoe UI", 10)).pack(anchor="w", padx=28, pady=(0, 14))

    def scroll_area(self, parent=None):
        parent = parent or self.content
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw", width=1180)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return inner

    def stat_card(self, parent, title, value, note, accent):
        card = tk.Frame(parent, bg=WHITE, highlightbackground="#d6e8e8", highlightthickness=1)
        tk.Frame(card, bg=accent, height=5).pack(fill="x")
        tk.Label(card, text=title.upper(), bg=WHITE, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=16, pady=(14, 2))
        tk.Label(card, text=str(value), bg=WHITE, fg=TEAL_DARK,
                 font=("Segoe UI", 25, "bold")).pack(anchor="w", padx=16)
        tk.Label(card, text=note, bg=WHITE, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(0, 14))
        return card

    def show_dashboard(self):
        self.shell("Dashboard")
        name = self.current_user.get("display_name") or self.current_user["username"]
        hero = tk.Frame(self.content, bg=TEAL, padx=28, pady=22)
        hero.pack(fill="x", padx=22, pady=(18, 14))
        tk.Label(hero, text=f"Welcome back, {name}!", bg=TEAL, fg=WHITE,
                 font=("Segoe UI", 24, "bold")).pack(anchor="w")
        tk.Label(hero, text="Every pet deserves a safe home.", bg=TEAL, fg="#d7efec",
                 font=("Segoe UI", 12)).pack(anchor="w", pady=(4, 0))
        pets = [p for p in self.db.data["pets"] if p.get("status", "Available") == "Available"]
        apps = [a for a in self.db.data["applications"] if a.get("applicant") == self.current_user["username"]]
        pending = [a for a in self.db.data["applications"] if a.get("owner") == self.current_user["username"] and a.get("status") == "Pending"]
        posts = [p for p in self.db.data["pets"] if p.get("owner") == self.current_user["username"]]
        if self.current_user.get("role") == "admin":
            pending = [a for a in self.db.data["applications"] if a.get("status") == "Pending"]
        stats = tk.Frame(self.content, bg=BG)
        stats.pack(fill="x", padx=22)
        for i, item in enumerate([
            ("Available Pets", len(pets), "Waiting for a home", GREEN),
            ("My Applications", len(apps), f"{sum(a.get('status') == 'Pending' for a in apps)} still pending", "#4f9db0"),
            ("Pending Requests", len(pending), "Adoption requests for your pets", GOLD),
            ("My Pet Posts", len(posts), "Pets you posted", RED)]):
            stats.grid_columnconfigure(i, weight=1, uniform="stat")
            self.stat_card(stats, *item).grid(row=0, column=i, sticky="nsew", padx=5)
        lower = tk.Frame(self.content, bg=BG)
        lower.pack(fill="both", expand=True, padx=22, pady=16)
        lower.grid_columnconfigure(0, weight=3)
        lower.grid_columnconfigure(1, weight=1)
        recent = tk.Frame(lower, bg=WHITE, highlightbackground="#d6e8e8", highlightthickness=1, padx=16, pady=14)
        recent.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk.Label(recent, text="🐾  Recently Posted Pets", bg=WHITE, fg=TEAL,
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 8))
        recent_pets = sorted(self.db.data["pets"], key=lambda p: p.get("created_at", ""), reverse=True)[:4]
        if not recent_pets:
            tk.Label(recent, text="No pets have been posted yet. Be the first to help a pet find a home!",
                     bg=WHITE, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=20)
        for p in recent_pets:
            row = tk.Frame(recent, bg=WHITE, pady=8)
            row.pack(fill="x")
            photo = "📷" if p.get("photo") else "🐾"
            tk.Label(row, text=photo, bg=MINT, fg=TEAL, font=("Segoe UI", 20), width=4, height=2).pack(side="left", padx=(0, 10))
            details = tk.Frame(row, bg=WHITE)
            details.pack(side="left", fill="x", expand=True)
            tk.Label(details, text=f"{p.get('name','Pet')}  •  {p.get('breed','Mixed')}", bg=WHITE,
                     fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w")
            tk.Label(details, text=f"Type: {p.get('type','')}   |   Age: {p.get('age','')}   |   Status: {p.get('status','Available')}",
                     bg=WHITE, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 0))
            tk.Frame(recent, bg="#e3eeee", height=1).pack(fill="x")
        quick = tk.Frame(lower, bg="#e0f0ef", padx=14, pady=14)
        quick.grid(row=0, column=1, sticky="nsew", padx=(0, 0))
        tk.Label(quick, text="⚡  QUICK ACTIONS", bg="#e0f0ef", fg=TEAL,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 12))
        self.button(quick, "🐾  Find a Pet", self.show_pets).pack(fill="x", pady=5)
        self.button(quick, "＋  Post a Pet", self.show_posting).pack(fill="x", pady=5)
        self.button(quick, "▤  Report a Stray", self.show_strays).pack(fill="x", pady=5)

    def make_tree(self, parent, columns, headings, height=12):
        frame = tk.Frame(parent, bg=WHITE)
        frame.pack(fill="both", expand=True, padx=24, pady=10)
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=height)
        for col, heading in zip(columns, headings):
            tree.heading(col, text=heading)
            tree.column(col, width=130, anchor="w")
        sy = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        sx = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        tree.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        return tree

    def show_pets(self):
        self.shell("Available Pets")
        self.page_heading("Available Pets", "Browse pets looking for a safe, loving home.")
        controls = tk.Frame(self.content, bg=BG)
        controls.pack(fill="x", padx=26)
        self.pet_search = tk.StringVar()
        ttk.Entry(controls, textvariable=self.pet_search).pack(side="left", fill="x", expand=True, ipady=5)
        self.button(controls, "Search", self.refresh_pets).pack(side="left", padx=8)
        self.button(controls, "Clear", lambda: (self.pet_search.set(""), self.refresh_pets()), primary=False).pack(side="left")
        self.pet_tree = self.make_tree(self.content, ("id", "name", "type", "breed", "age", "location", "owner", "status"),
                                       ("ID", "Pet Name", "Type", "Breed", "Age", "Location", "Posted By", "Status"))
        actions = tk.Frame(self.content, bg=BG)
        actions.pack(fill="x", padx=26, pady=(0, 12))
        self.button(actions, "Apply to Adopt Selected Pet", self.apply_for_pet).pack(side="left")
        self.button(actions, "View Pet Details", self.pet_details, primary=False).pack(side="left", padx=8)
        self.refresh_pets()

    def refresh_pets(self):
        if not hasattr(self, "pet_tree") or not self.pet_tree.winfo_exists():
            return
        for item in self.pet_tree.get_children():
            self.pet_tree.delete(item)
        query = self.pet_search.get().lower().strip()
        for p in self.db.data["pets"]:
            if p.get("status", "Available") != "Available":
                continue
            text = " ".join(str(p.get(k, "")) for k in ("name", "type", "breed", "location", "owner")).lower()
            if query and query not in text:
                continue
            self.pet_tree.insert("", "end", values=(p["id"], p.get("name"), p.get("type"), p.get("breed"),
                p.get("age"), p.get("location"), p.get("owner"), p.get("status", "Available")))

    def selected_pet(self):
        selection = self.pet_tree.selection()
        if not selection:
            messagebox.showwarning("Select a pet", "Please select a pet first.")
            return None
        pid = int(self.pet_tree.item(selection[0], "values")[0])
        return next((p for p in self.db.data["pets"] if p["id"] == pid), None)

    def pet_details(self):
        p = self.selected_pet()
        if not p:
            return
        details = "\n".join(f"{label}: {p.get(key, 'Not provided')}" for key, label in [
            ("name", "Name"), ("type", "Type"), ("breed", "Breed"), ("age", "Age"),
            ("gender", "Gender"), ("location", "Location"), ("description", "Description"),
            ("owner", "Posted by"), ("status", "Status")])
        if p.get("photo"):
            details += f"\nPhoto file: {p['photo']}"
        messagebox.showinfo("Pet Details", details)

    def apply_for_pet(self):
        p = self.selected_pet()
        if not p:
            return
        if p.get("owner") == self.current_user["username"]:
            messagebox.showerror("Adoption Application", "You cannot apply to adopt your own pet.")
            return
        if any(a.get("pet_id") == p["id"] and a.get("applicant") == self.current_user["username"]
               and a.get("status") in ("Pending", "Approved") for a in self.db.data["applications"]):
            messagebox.showinfo("Adoption Application", "You already have an active application for this pet.")
            return
        win = tk.Toplevel(self)
        win.title("Adoption Application")
        win.configure(bg=WHITE)
        win.geometry("500x520")
        win.transient(self)
        frame = tk.Frame(win, bg=WHITE, padx=24, pady=20)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text=f"Apply to adopt {p.get('name')}", bg=WHITE, fg=TEAL,
                 font=("Segoe UI", 17, "bold")).pack(anchor="w", pady=(0, 12))
        vars_ = {k: tk.StringVar() for k in ("phone", "address", "home", "experience")}
        for k, label in (("phone", "Contact number"), ("address", "Home address"),
                         ("home", "Home type (house/apartment)"), ("experience", "Pet care experience")):
            self.field(frame, label, vars_[k])
        tk.Label(frame, text="Why would you like to adopt this pet?", bg=WHITE, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 4))
        reason = tk.Text(frame, height=4, wrap="word", font=("Segoe UI", 10), relief="solid", bd=1)
        reason.pack(fill="x")
        def submit():
            if not vars_["phone"].get().strip() or not vars_["address"].get().strip():
                messagebox.showwarning("Application", "Contact number and home address are required.", parent=win)
                return
            a = {"id": self.db.data["next_application_id"], "pet_id": p["id"], "pet_name": p.get("name"),
                 "owner": p.get("owner"), "applicant": self.current_user["username"],
                 "phone": vars_["phone"].get().strip(), "address": vars_["address"].get().strip(),
                 "home_type": vars_["home"].get().strip(), "experience": vars_["experience"].get().strip(),
                 "reason": reason.get("1.0", "end").strip(), "status": "Pending", "created_at": now()}
            self.db.data["applications"].append(a)
            self.db.data["next_application_id"] += 1
            self.db.save()
            win.destroy()
            messagebox.showinfo("Application", "Your adoption application has been submitted.")
            self.show_pets()
        self.button(frame, "Submit Application", submit).pack(fill="x", pady=12)

    def show_posting(self):
        self.shell("Pet Posting")
        self.page_heading("Pet Posting", "Share a pet that needs a safe and loving home.")
        body = tk.Frame(self.content, bg=WHITE, padx=24, pady=18, highlightbackground="#d6e8e8", highlightthickness=1)
        body.pack(fill="both", expand=True, padx=26, pady=(0, 16))
        self.post_vars = {k: tk.StringVar() for k in ("name", "type", "age", "breed", "gender", "location")}
        for k, label in (("name", "Pet Name *"), ("type", "Pet Type (dog, cat, etc.) *"),
                         ("age", "Age (e.g. 2 years or 6 months) *"), ("breed", "Breed"),
                         ("gender", "Gender"), ("location", "Location *")):
            self.field(body, label, self.post_vars[k])
        tk.Label(body, text="Post Type", bg=WHITE, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 4))
        self.post_type = tk.StringVar(value="Pet for Adoption")
        ttk.Combobox(body, textvariable=self.post_type, values=("Pet for Adoption", "Lost Pet", "Found Pet"),
                     state="readonly").pack(fill="x", ipady=3)
        tk.Label(body, text="Description", bg=WHITE, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 4))
        self.post_description = tk.Text(body, height=4, wrap="word", font=("Segoe UI", 10), relief="solid", bd=1)
        self.post_description.pack(fill="x")
        photo_row = tk.Frame(body, bg=WHITE)
        photo_row.pack(fill="x", pady=8)
        self.post_photo = tk.StringVar()
        tk.Label(photo_row, text="Pet Photo", bg=WHITE, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(photo_row, textvariable=self.post_photo, bg=WHITE, fg=MUTED).pack(side="left", padx=10)
        self.button(photo_row, "Choose Photo", self.choose_photo, primary=False).pack(side="right")
        self.button(body, "Publish Pet Post", self.publish_pet).pack(anchor="w", pady=(8, 0))

    def choose_photo(self):
        path = filedialog.askopenfilename(title="Choose a pet photo",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")])
        if path:
            self.post_photo.set(path)

    def publish_pet(self):
        v = self.post_vars
        if not v["name"].get().strip() or not v["type"].get().strip() or not v["age"].get().strip() or not v["location"].get().strip():
            messagebox.showwarning("Pet Posting", "Please complete Pet Name, Pet Type, Age, and Location.")
            return
        photo_path = ""
        source = self.post_photo.get()
        if source and os.path.isfile(source):
            ext = os.path.splitext(source)[1].lower()
            photo_path = os.path.join(UPLOAD_DIR, f"pet_{self.db.data['next_pet_id']}{ext}")
            try:
                shutil.copy2(source, photo_path)
            except OSError as e:
                messagebox.showerror("Photo", f"Could not copy photo: {e}")
                return
        p = {"id": self.db.data["next_pet_id"], "name": v["name"].get().strip(),
             "type": v["type"].get().strip(), "age": v["age"].get().strip(),
             "breed": v["breed"].get().strip() or "Mixed", "gender": v["gender"].get().strip(),
             "location": v["location"].get().strip(), "post_type": self.post_type.get(),
             "description": self.post_description.get("1.0", "end").strip(),
             "photo": photo_path, "owner": self.current_user["username"],
             "status": "Available", "created_at": now()}
        self.db.data["pets"].append(p)
        self.db.data["next_pet_id"] += 1
        self.db.save()
        messagebox.showinfo("Pet Posting", "Your pet post has been published.")
        self.show_dashboard()

    def show_strays(self):
        self.shell("Stray Status")
        self.page_heading("Stray Status", "Report a stray animal and follow its rescue progress.")
        form = tk.Frame(self.content, bg=WHITE, padx=18, pady=14, highlightbackground="#d6e8e8", highlightthickness=1)
        form.pack(fill="x", padx=26, pady=(0, 10))
        self.stray_vars = {k: tk.StringVar() for k in ("animal", "location", "condition", "contact")}
        top = tk.Frame(form, bg=WHITE)
        top.pack(fill="x")
        for k, label in (("animal", "Animal type *"), ("location", "Location found *"),
                         ("condition", "Condition"), ("contact", "Contact number")):
            box = tk.Frame(top, bg=WHITE)
            box.pack(side="left", fill="x", expand=True, padx=5)
            tk.Label(box, text=label, bg=WHITE, fg=TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w")
            ttk.Entry(box, textvariable=self.stray_vars[k]).pack(fill="x", ipady=3, pady=4)
        tk.Label(form, text="Additional details", bg=WHITE, fg=TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=5)
        self.stray_details = tk.Text(form, height=2, font=("Segoe UI", 10), wrap="word", relief="solid", bd=1)
        self.stray_details.pack(fill="x", padx=5, pady=4)
        self.button(form, "Submit Stray Report", self.submit_stray).pack(anchor="w", padx=5, pady=(5, 0))
        tk.Label(self.content, text="Reported Animals", bg=BG, fg=TEAL,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=26, pady=(6, 0))
        self.stray_tree = self.make_tree(self.content, ("id", "animal", "location", "condition", "reporter", "status", "created"),
                                         ("ID", "Animal", "Location", "Condition", "Reported By", "Status", "Date"))
        self.refresh_strays()

    def submit_stray(self):
        v = self.stray_vars
        if not v["animal"].get().strip() or not v["location"].get().strip():
            messagebox.showwarning("Stray Report", "Animal type and location are required.")
            return
        item = {"id": self.db.data["next_stray_id"], "animal": v["animal"].get().strip(),
                "location": v["location"].get().strip(), "condition": v["condition"].get().strip() or "Unknown",
                "contact": v["contact"].get().strip(), "details": self.stray_details.get("1.0", "end").strip(),
                "reporter": self.current_user["username"], "status": "Reported", "created_at": now()}
        self.db.data["strays"].append(item)
        self.db.data["next_stray_id"] += 1
        self.db.save()
        messagebox.showinfo("Stray Report", "Your report has been submitted.")
        self.show_strays()

    def refresh_strays(self):
        if not hasattr(self, "stray_tree") or not self.stray_tree.winfo_exists():
            return
        for row in self.stray_tree.get_children():
            self.stray_tree.delete(row)
        for s in self.db.data["strays"]:
            if self.current_user.get("role") == "admin" or s.get("reporter") == self.current_user["username"]:
                self.stray_tree.insert("", "end", values=(s["id"], s.get("animal"), s.get("location"),
                    s.get("condition"), s.get("reporter"), s.get("status"), s.get("created_at")))

    def show_applications(self):
        self.shell("Applications")
        self.page_heading("Applications", "Track your adoption applications or review requests for pets you posted.")
        self.app_tree = self.make_tree(self.content, ("id", "pet", "applicant", "owner", "status", "date"),
                                       ("ID", "Pet", "Applicant", "Pet Owner", "Status", "Submitted"))
        for a in self.db.data["applications"]:
            visible = self.current_user.get("role") == "admin" or a.get("applicant") == self.current_user["username"] or a.get("owner") == self.current_user["username"]
            if visible:
                self.app_tree.insert("", "end", values=(a["id"], a.get("pet_name"), a.get("applicant"),
                    a.get("owner"), a.get("status"), a.get("created_at")))
        actions = tk.Frame(self.content, bg=BG)
        actions.pack(fill="x", padx=26, pady=(0, 14))
        self.button(actions, "Approve Selected", lambda: self.update_application("Approved")).pack(side="left")
        self.button(actions, "Reject Selected", lambda: self.update_application("Rejected"), primary=False).pack(side="left", padx=8)
        self.button(actions, "Cancel My Application", lambda: self.update_application("Cancelled"), primary=False).pack(side="left")

    def update_application(self, status):
        sel = self.app_tree.selection()
        if not sel:
            messagebox.showwarning("Applications", "Select an application first.")
            return
        aid = int(self.app_tree.item(sel[0], "values")[0])
        a = next((x for x in self.db.data["applications"] if x["id"] == aid), None)
        if not a:
            return
        admin = self.current_user.get("role") == "admin"
        owner = a.get("owner") == self.current_user["username"]
        applicant = a.get("applicant") == self.current_user["username"]
        if status in ("Approved", "Rejected") and not (admin or owner):
            messagebox.showerror("Permission", "Only the pet owner or admin can approve or reject applications.")
            return
        if status == "Cancelled" and not applicant:
            messagebox.showerror("Permission", "You can cancel only your own application.")
            return
        if status == "Approved":
            pet = next((p for p in self.db.data["pets"] if p["id"] == a["pet_id"]), None)
            if pet:
                pet["status"] = "Adopted"
                for other in self.db.data["applications"]:
                    if other.get("pet_id") == pet["id"] and other["id"] != aid and other.get("status") == "Pending":
                        other["status"] = "Rejected"
        a["status"] = status
        self.db.save()
        messagebox.showinfo("Applications", f"Application marked {status.lower()}.")
        self.show_applications()

    def show_profile(self):
        self.shell("Profile")
        self.page_heading("My Profile", "Manage your account details and password.")
        card = tk.Frame(self.content, bg=WHITE, padx=26, pady=22, highlightbackground="#d6e8e8", highlightthickness=1)
        card.pack(fill="x", padx=26, pady=(0, 16))
        u = self.current_user
        self.profile_vars = {k: tk.StringVar(value=u.get(key, "")) for k, key in [
            ("name", "display_name"), ("email", "email"), ("phone", "phone"), ("location", "location")]}
        tk.Label(card, text=f"Username: {u['username']}   •   Role: {u['role'].title()}",
                 bg=WHITE, fg=TEAL, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
        for k, label in (("name", "Full name"), ("email", "Email"), ("phone", "Phone"), ("location", "Location")):
            self.field(card, label, self.profile_vars[k])
        self.button(card, "Save Profile", self.save_profile).pack(anchor="w", pady=8)
        pw = tk.Frame(self.content, bg=WHITE, padx=26, pady=20, highlightbackground="#d6e8e8", highlightthickness=1)
        pw.pack(fill="x", padx=26, pady=(0, 16))
        tk.Label(pw, text="Change Password", bg=WHITE, fg=TEAL, font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 8))
        self.old_pw, self.new_pw, self.confirm_pw = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.field(pw, "Current password", self.old_pw, show="•")
        self.field(pw, "New password (8–13 characters)", self.new_pw, show="•")
        self.field(pw, "Confirm new password", self.confirm_pw, show="•")
        self.button(pw, "Update Password", self.save_password).pack(anchor="w", pady=6)

    def save_profile(self):
        u = self.current_user
        u["display_name"] = self.profile_vars["name"].get().strip() or u["username"]
        u["email"] = self.profile_vars["email"].get().strip()
        u["phone"] = self.profile_vars["phone"].get().strip()
        u["location"] = self.profile_vars["location"].get().strip()
        self.db.save()
        messagebox.showinfo("Profile", "Profile updated successfully.")
        self.show_profile()

    def save_password(self):
        if self.new_pw.get() != self.confirm_pw.get():
            messagebox.showerror("Password", "New passwords do not match.")
            return
        try:
            self.db.change_password(self.current_user, self.old_pw.get(), self.new_pw.get())
        except ValueError as e:
            messagebox.showerror("Password", str(e))
            return
        messagebox.showinfo("Password", "Password changed successfully.")
        self.show_profile()

    def show_admin(self):
        if self.current_user.get("role") != "admin":
            messagebox.showerror("Admin", "Administrator access is required.")
            return
        self.shell("Admin")
        self.page_heading("Admin Management", "Manage pet posts, stray reports, users, and adoption applications.")
        tabs = ttk.Notebook(self.content)
        tabs.pack(fill="both", expand=True, padx=24, pady=(0, 14))
        # Pets tab
        pets_tab = tk.Frame(tabs, bg=BG)
        tabs.add(pets_tab, text="Pet Posts")
        self.admin_pet_tree = self.make_tree(pets_tab, ("id", "name", "type", "owner", "status", "location"),
                                             ("ID", "Name", "Type", "Owner", "Status", "Location"))
        for p in self.db.data["pets"]:
            self.admin_pet_tree.insert("", "end", values=(p["id"], p.get("name"), p.get("type"), p.get("owner"), p.get("status"), p.get("location")))
        pet_actions = tk.Frame(pets_tab, bg=BG)
        pet_actions.pack(fill="x", padx=24, pady=(0, 10))
        self.button(pet_actions, "Mark Available", lambda: self.admin_pet_status("Available")).pack(side="left")
        self.button(pet_actions, "Mark Adopted", lambda: self.admin_pet_status("Adopted"), primary=False).pack(side="left", padx=8)
        self.button(pet_actions, "Delete Selected Pet", self.admin_delete_pet, primary=False).pack(side="left")
        # Strays tab
        stray_tab = tk.Frame(tabs, bg=BG)
        tabs.add(stray_tab, text="Stray Reports")
        self.admin_stray_tree = self.make_tree(stray_tab, ("id", "animal", "location", "reporter", "status"),
                                               ("ID", "Animal", "Location", "Reporter", "Status"))
        for s in self.db.data["strays"]:
            self.admin_stray_tree.insert("", "end", values=(s["id"], s.get("animal"), s.get("location"), s.get("reporter"), s.get("status")))
        stray_actions = tk.Frame(stray_tab, bg=BG)
        stray_actions.pack(fill="x", padx=24, pady=(0, 10))
        self.button(stray_actions, "Mark In Progress", lambda: self.admin_stray_status("In Progress")).pack(side="left")
        self.button(stray_actions, "Mark Rescued", lambda: self.admin_stray_status("Rescued")).pack(side="left", padx=8)
        self.button(stray_actions, "Mark Closed", lambda: self.admin_stray_status("Closed"), primary=False).pack(side="left")
        # Users tab
        users_tab = tk.Frame(tabs, bg=BG)
        tabs.add(users_tab, text="Users")
        tree = self.make_tree(users_tab, ("username", "name", "email", "role", "created"),
                              ("Username", "Name", "Email", "Role", "Created"))
        for u in self.db.data["users"]:
            tree.insert("", "end", values=(u["username"], u.get("display_name"), u.get("email"), u.get("role"), u.get("created_at")))
        # All applications tab
        apps_tab = tk.Frame(tabs, bg=BG)
        tabs.add(apps_tab, text="Applications")
        self.admin_app_tree = self.make_tree(apps_tab, ("id", "pet", "applicant", "owner", "status"),
                                             ("ID", "Pet", "Applicant", "Owner", "Status"))
        for a in self.db.data["applications"]:
            self.admin_app_tree.insert("", "end", values=(a["id"], a.get("pet_name"), a.get("applicant"), a.get("owner"), a.get("status")))

    def admin_pet_status(self, status):
        sel = self.admin_pet_tree.selection()
        if not sel:
            messagebox.showwarning("Admin", "Select a pet.")
            return
        pid = int(self.admin_pet_tree.item(sel[0], "values")[0])
        pet = next(p for p in self.db.data["pets"] if p["id"] == pid)
        pet["status"] = status
        self.db.save()
        self.show_admin()

    def admin_delete_pet(self):
        sel = self.admin_pet_tree.selection()
        if not sel:
            messagebox.showwarning("Admin", "Select a pet.")
            return
        pid = int(self.admin_pet_tree.item(sel[0], "values")[0])
        if not messagebox.askyesno("Delete Pet", "Permanently delete this pet post?"):
            return
        self.db.data["pets"] = [p for p in self.db.data["pets"] if p["id"] != pid]
        self.db.data["applications"] = [a for a in self.db.data["applications"] if a.get("pet_id") != pid]
        self.db.save()
        self.show_admin()

    def admin_stray_status(self, status):
        sel = self.admin_stray_tree.selection()
        if not sel:
            messagebox.showwarning("Admin", "Select a stray report.")
            return
        sid = int(self.admin_stray_tree.item(sel[0], "values")[0])
        stray = next(s for s in self.db.data["strays"] if s["id"] == sid)
        stray["status"] = status
        self.db.save()
        self.show_admin()

    def logout(self):
        if messagebox.askyesno("Log Out", "Are you sure you want to log out?"):
            self.current_user = None
            self.show_login()


if __name__ == "__main__":
    app = PetLink()
    app.mainloop()
