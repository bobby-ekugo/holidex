"""
Tkinter UI for Holidex.
Requires: pip install tkcalendar

AI cultural context is fetched lazily — only when a holiday date is
clicked, not for the whole list on search — to stay within Gemini's
free-tier daily request quota. Results are cached on the Holiday object
itself, so re-clicking an already-viewed date costs no extra API calls.
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from typing import Callable
from tkcalendar import Calendar

from validators.input_validator import validate_country_code, validate_year
from services.holiday_api_client import HolidayAPIClient
from services.culture_guide_generator import CultureGuideGenerator
from services.holiday_comparator import HolidayComparator
from storage.file_manager import FileManager
from models.country import Country
from models.holiday import Holiday
from typing_defs import ComparisonResult
from exceptions import APIRequestError, HolidexError

TEAL: str = "#1B6B73"
AMBER: str = "#E8A23D"
CREAM: str = "#FAF7F2"
CHARCOAL: str = "#2B2B2B"


def _friendly_error(error: HolidexError) -> str:
    """Return user-friendly text for known UI errors."""
    if isinstance(error, APIRequestError):
        return "Couldn't reach the holiday service. Check your internet connection and try again."
    return str(error)


class SplashScreen:
    """Display the startup splash window and reveal the main app after fading out."""

    def __init__(
        self,
        root: tk.Misc,
        on_complete: Callable[[], None],
        hold_ms: int = 2000,
        fade_step_ms: int = 30,
        fade_step: float = 0.05,
    ) -> None:
        self.on_complete: Callable[[], None] = on_complete
        self.window: tk.Toplevel = tk.Toplevel(root)
        self.window.overrideredirect(True)
        self.window.configure(bg=CREAM)
        self.window.attributes("-alpha", 1.0)

        w, h = 400, 250
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.window.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(self.window, text="Holidex", font=("Georgia", 32, "bold"), fg=TEAL, bg=CREAM).pack(expand=True)
        tk.Label(self.window, text="Discover the world's celebrations",
                 font=("Segoe UI", 11), fg=CHARCOAL, bg=CREAM).pack()

        self.fade_step_ms = fade_step_ms
        self.fade_step = fade_step
        self.window.after(hold_ms, self._fade_out)

    def _fade_out(self, alpha: float = 1.0) -> None:
        """Reduce window opacity until the splash screen can be destroyed."""
        alpha -= self.fade_step
        if alpha > 0:
            self.window.attributes("-alpha", alpha)
            self.window.after(self.fade_step_ms, self._fade_out, alpha)
        else:
            self.window.destroy()
            self.on_complete()


class HolidexApp:
    """Coordinate the Tkinter interface with API, comparison, and storage services."""

    def __init__(self, root: tk.Tk) -> None:
        self.root: tk.Tk = root
        self.root.title("Holidex — Public Holiday & Cultural Awareness Planner")
        self.root.geometry("950x650")

        self.api_client = HolidayAPIClient()
        self.culture_generator = CultureGuideGenerator()
        self.comparator = HolidayComparator()
        self.file_manager = FileManager()

        self.current_country: Country | None = None
        self.current_holidays_by_date: dict[date, list[Holiday]] = {}
        self.current_comparison: ComparisonResult | None = None
        self._first_holiday_date: date | None = None
        self._enriching_holidays: set[int] = set()

        self._build_layout()

    def _build_layout(self) -> None:
        """Create the notebook container and populate both application tabs."""
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.browse_tab = ttk.Frame(notebook)
        self.compare_tab = ttk.Frame(notebook)
        notebook.add(self.browse_tab, text="Browse")
        notebook.add(self.compare_tab, text="Compare")

        self._build_browse_tab()
        self._build_compare_tab()

    # ---------------- Browse Tab ----------------
    def _build_browse_tab(self) -> None:
        """Build controls for fetching, viewing, enriching, and saving holidays."""
        top = ttk.Frame(self.browse_tab, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Country code:").grid(row=0, column=0, padx=5, sticky="w")
        self.browse_country_var: tk.StringVar = tk.StringVar()
        ttk.Entry(top, textvariable=self.browse_country_var, width=8).grid(row=0, column=1, padx=5)

        ttk.Label(top, text="Year:").grid(row=0, column=2, padx=5, sticky="w")
        self.browse_year_var: tk.StringVar = tk.StringVar()
        ttk.Entry(top, textvariable=self.browse_year_var, width=8).grid(row=0, column=3, padx=5)

        self.get_holidays_button: ttk.Button = ttk.Button(top, text="Get Holidays", command=self._on_get_holidays)
        self.get_holidays_button.grid(row=0, column=4, padx=10)

        self.jump_button: ttk.Button = ttk.Button(
            top, text="Jump to first holiday", command=self._jump_to_first_holiday, state="disabled"
        )
        self.jump_button.grid(row=0, column=5, padx=5)

        ttk.Label(top, text="Favourites:").grid(row=0, column=6, padx=(10, 5), sticky="w")
        self.favourites_var: tk.StringVar = tk.StringVar()
        self.favourites_combo: ttk.Combobox = ttk.Combobox(
            top, textvariable=self.favourites_var, width=8, state="readonly"
        )
        self.favourites_combo.grid(row=0, column=7, padx=5)
        self.favourites_combo.bind("<<ComboboxSelected>>", self._on_favourite_selected)
        self._refresh_favourites_dropdown()

        body = ttk.Frame(self.browse_tab, padding=10)
        body.pack(fill="both", expand=True)

        cal_frame = ttk.Frame(body)
        cal_frame.pack(side="left", fill="both", expand=True)

        self.calendar: Calendar = Calendar(cal_frame, selectmode="day", date_pattern="yyyy-mm-dd")
        self.calendar.pack(fill="both", expand=True)
        self.calendar.tag_config("holiday", background=AMBER, foreground=CHARCOAL)
        self.calendar.bind("<<CalendarSelected>>", self._on_date_selected)

        detail_frame = ttk.LabelFrame(body, text="Holiday Details", padding=10)
        detail_frame.pack(side="left", fill="both", expand=True, padx=(10, 0))

        self.detail_text: tk.Text = tk.Text(detail_frame, wrap="word", height=20, width=38, state="disabled")
        self.detail_text.pack(fill="both", expand=True)

        bottom = ttk.Frame(self.browse_tab, padding=10)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="Save Guide", command=self._on_save_guide).pack(side="left", padx=5)
        ttk.Button(bottom, text="Save Favourite", command=self._on_save_favourite).pack(side="left", padx=5)

    def _on_get_holidays(self) -> None:
        """Validate browse inputs and start a background holiday fetch."""
        try:
            code = validate_country_code(self.browse_country_var.get())
            year = validate_year(self.browse_year_var.get())
        except HolidexError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        self._set_browse_loading(True)
        threading.Thread(target=self._fetch_holidays_worker, args=(code, year), daemon=True).start()

    def _fetch_holidays_worker(self, code: str, year: int) -> None:
        """Fetch holidays off the UI thread and schedule the result on the event loop."""
        try:
            holidays = self.api_client.get_holidays(code, year)
            self.root.after(0, self._on_holidays_ready, code, year, holidays, None)
        except HolidexError as exc:
            self.root.after(0, self._on_holidays_ready, code, year, None, exc)
        except Exception as exc:
            self.root.after(0, self._on_holidays_ready, code, year, None, APIRequestError(str(exc)))

    def _on_holidays_ready(
        self,
        code: str,
        year: int,
        holidays: list[Holiday] | None,
        error: HolidexError | None,
    ) -> None:
        """Render fetched holidays, reset loading state, and populate the date index."""
        self._set_browse_loading(False)
        if error:
            messagebox.showerror("Error fetching holidays", _friendly_error(error))
            return
        assert holidays is not None

        country_name = self.api_client.get_country_name(code)
        self.current_country = Country(code=code, name=country_name, year=year, holidays=holidays)
        self.calendar.calevent_remove("all")
        self.current_holidays_by_date = {}
        # Keep every holiday on a date; some calendars contain multiple observances.
        for h in holidays:
            self.calendar.calevent_create(h.date, h.name, "holiday")
            self.current_holidays_by_date.setdefault(h.date, []).append(h)

        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.config(state="disabled")

        if holidays:
            self._first_holiday_date = min(h.date for h in holidays)
            self.jump_button.config(state="normal")
        else:
            self._first_holiday_date = None
            self.jump_button.config(state="disabled")
            messagebox.showinfo("No holidays", f"No holidays found for {code} in {year}.")

    def _set_browse_loading(self, loading: bool) -> None:
        """Enable or disable browse controls while a fetch is in progress."""
        state = "disabled" if loading else "normal"
        self.get_holidays_button.config(state=state)
        self.root.config(cursor="watch" if loading else "")

    def _jump_to_first_holiday(self) -> None:
        """Select the earliest fetched holiday and refresh its detail panel."""
        if self._first_holiday_date:
            self.calendar.selection_set(self._first_holiday_date)
            self._on_date_selected()

    def _on_date_selected(self, event: tk.Event | None = None) -> None:
        """Display all holidays for the selected date and request missing context."""
        selected_str = self.calendar.get_date()
        try:
            selected = date.fromisoformat(selected_str)
        except ValueError:
            return

        holidays = self.current_holidays_by_date.get(selected, [])
        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", "end")

        if not holidays:
            self.detail_text.insert("end", "No holiday on this date.")
            self.detail_text.config(state="disabled")
            return

        for holiday in holidays:
            self.detail_text.insert("end", f"{holiday.name}\n\n")
            self.detail_text.insert("end", f"{holiday.date} — {holiday.holiday_type}\n\n")
            if holiday.cultural_note:
                self.detail_text.insert("end", f"{holiday.cultural_note}\n\n")
                if holiday.greeting:
                    self.detail_text.insert("end", f"Greeting: {holiday.greeting}\n\n")
            elif holiday.enrichment_error:
                self.detail_text.insert("end", f"{holiday.enrichment_error}\n(Retrying cultural context...)\n\n")
                holiday_id = id(holiday)
                if holiday_id not in self._enriching_holidays:
                    self._enriching_holidays.add(holiday_id)
                    holiday.enrichment_error = None
                    c_name = self.current_country.name if self.current_country else ""
                    c_code = self.current_country.code if self.current_country else ""
                    threading.Thread(
                        target=self._enrich_holiday_worker,
                        args=(holiday, selected, c_name, c_code),
                        daemon=True,
                    ).start()
            else:
                self.detail_text.insert("end", "Loading cultural context...\n\n")
                holiday_id = id(holiday)
                if holiday_id not in self._enriching_holidays:
                    self._enriching_holidays.add(holiday_id)
                    c_name = self.current_country.name if self.current_country else ""
                    c_code = self.current_country.code if self.current_country else ""
                    threading.Thread(
                        target=self._enrich_holiday_worker,
                        args=(holiday, selected, c_name, c_code),
                        daemon=True,
                    ).start()
        self.detail_text.config(state="disabled")

    def _enrich_holiday_worker(
        self,
        holiday: Holiday,
        selected_date: date,
        country_name: str,
        country_code: str,
    ) -> None:
        """Fetch cultural context off-thread using the country active at dispatch time."""
        try:
            self.culture_generator.enrich_holiday(
                holiday, country_name or country_code
            )
            error: Exception | None = None
        except Exception as exc:
            error = exc
        self.root.after(0, self._on_holiday_enriched, holiday, selected_date, country_code, error)

    def _on_holiday_enriched(
        self,
        holiday: Holiday,
        selected_date: date,
        dispatched_country_code: str,
        error: Exception | None = None,
    ) -> None:
        """Apply enrichment results only when they still belong to the active country."""
        self._enriching_holidays.discard(id(holiday))
        if error:
            holiday.enrichment_error = f"Cultural context unavailable right now ({type(error).__name__})."

        # Check if active country has changed since worker dispatch
        if not self.current_country or self.current_country.code != dispatched_country_code:
            return

        try:
            current_selected = date.fromisoformat(self.calendar.get_date())
        except ValueError:
            return
        if current_selected == selected_date:
            self._on_date_selected()

    def _on_save_guide(self) -> None:
        """Save the currently displayed country's fetched-year guide to Markdown."""
        if not self.current_country or self.current_country.year is None:
            messagebox.showwarning("Nothing to save", "Get holidays for a country first.")
            return
        path = self.file_manager.save_guide(self.current_country, self.current_country.year)
        messagebox.showinfo("Saved", f"Guide saved to:\n{path}")

    def _on_save_favourite(self) -> None:
        """Validate and persist the browse country code, then refresh the selector."""
        try:
            code = validate_country_code(self.browse_country_var.get())
        except HolidexError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return
        self.file_manager.save_favourite(code)
        self._refresh_favourites_dropdown()
        messagebox.showinfo("Saved", f"{code} added to favourites.")

    def _refresh_favourites_dropdown(self) -> None:
        """Load saved country codes into the browse-tab favourites combobox."""
        try:
            favs = self.file_manager.load_favourites()
            self.favourites_combo["values"] = favs
            if favs and not self.favourites_var.get():
                self.favourites_var.set("")
        except Exception:
            pass

    def _on_favourite_selected(self, event: tk.Event | None = None) -> None:
        """Copy the selected favourite country code into the browse input field."""
        selected_code = self.favourites_var.get()
        if selected_code:
            self.browse_country_var.set(selected_code)

    # ---------------- Compare Tab ----------------
    def _build_compare_tab(self) -> None:
        """Build controls for fetching and displaying a two-country comparison."""
        top = ttk.Frame(self.compare_tab, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Country A:").grid(row=0, column=0, padx=5)
        self.cmp_a_var: tk.StringVar = tk.StringVar()
        ttk.Entry(top, textvariable=self.cmp_a_var, width=8).grid(row=0, column=1, padx=5)

        ttk.Label(top, text="Country B:").grid(row=0, column=2, padx=5)
        self.cmp_b_var: tk.StringVar = tk.StringVar()
        ttk.Entry(top, textvariable=self.cmp_b_var, width=8).grid(row=0, column=3, padx=5)

        ttk.Label(top, text="Year:").grid(row=0, column=4, padx=5)
        self.cmp_year_var: tk.StringVar = tk.StringVar()
        ttk.Entry(top, textvariable=self.cmp_year_var, width=8).grid(row=0, column=5, padx=5)

        self.compare_button: ttk.Button = ttk.Button(top, text="Compare", command=self._on_compare)
        self.compare_button.grid(row=0, column=6, padx=10)

        self.summary_label: ttk.Label = ttk.Label(self.compare_tab, text="", padding=10, font=("Segoe UI", 10, "bold"))
        self.summary_label.pack(fill="x")

        columns_frame = ttk.Frame(self.compare_tab, padding=10)
        columns_frame.pack(fill="both", expand=True)

        left_frame = ttk.LabelFrame(columns_frame, text="Country A")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.cmp_left_list: tk.Listbox = tk.Listbox(left_frame)
        self.cmp_left_list.pack(fill="both", expand=True)

        right_frame = ttk.LabelFrame(columns_frame, text="Country B")
        right_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        self.cmp_right_list: tk.Listbox = tk.Listbox(right_frame)
        self.cmp_right_list.pack(fill="both", expand=True)

        ttk.Button(self.compare_tab, text="Save Comparison", command=self._on_save_comparison).pack(pady=10)

    def _on_compare(self) -> None:
        """Validate comparison inputs and start both holiday fetches in the background."""
        try:
            code_a = validate_country_code(self.cmp_a_var.get())
            code_b = validate_country_code(self.cmp_b_var.get())
            year = validate_year(self.cmp_year_var.get())
        except HolidexError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return
        if code_a == code_b:
            messagebox.showerror("Invalid input", "Choose two different countries to compare.")
            return

        self._set_compare_loading(True)
        threading.Thread(target=self._compare_worker, args=(code_a, code_b, year), daemon=True).start()

    def _compare_worker(self, code_a: str, code_b: str, year: int) -> None:
        """Fetch both calendars off the UI thread and return them to the event loop."""
        try:
            holidays_a = self.api_client.get_holidays(code_a, year)
            holidays_b = self.api_client.get_holidays(code_b, year)
            self.root.after(0, self._on_compare_ready, code_a, code_b, year, holidays_a, holidays_b, None)
        except HolidexError as exc:
            self.root.after(0, self._on_compare_ready, code_a, code_b, year, None, None, exc)
        except Exception as exc:
            self.root.after(0, self._on_compare_ready, code_a, code_b, year, None, None, APIRequestError(str(exc)))

    def _on_compare_ready(
        self,
        code_a: str,
        code_b: str,
        year: int,
        holidays_a: list[Holiday] | None,
        holidays_b: list[Holiday] | None,
        error: HolidexError | None,
    ) -> None:
        """Build country models and render the completed comparison result."""
        self._set_compare_loading(False)
        if error:
            messagebox.showerror("Error fetching holidays", _friendly_error(error))
            return
        assert holidays_a is not None and holidays_b is not None

        name_a = self.api_client.get_country_name(code_a)
        name_b = self.api_client.get_country_name(code_b)
        country_a = Country(code=code_a, name=name_a, year=year, holidays=holidays_a)
        country_b = Country(code=code_b, name=name_b, year=year, holidays=holidays_b)
        result = self.comparator.compare(country_a, country_b)
        self.current_comparison = result

        label_a = f"{name_a} ({code_a})" if name_a else code_a
        label_b = f"{name_b} ({code_b})" if name_b else code_b
        self.summary_label.config(
            text=(
                f"{len(result['same_date'])} overlapping dates   |   "
                f"{len(result['shared_celebrations'])} shared celebrations   |   "
                f"{len(result['unique_to_a'])} unique to {label_a}   |   "
                f"{len(result['unique_to_b'])} unique to {label_b}"
            )
        )

        self.cmp_left_list.delete(0, "end")
        self.cmp_right_list.delete(0, "end")

        for pair in result["same_date"]:
            self.cmp_left_list.insert("end", f"[SAME DATE] {pair['a'].date} {pair['a'].name}")
            self.cmp_right_list.insert("end", f"[SAME DATE] {pair['b'].date} {pair['b'].name}")

        for pair in result["shared_celebrations"]:
            self.cmp_left_list.insert("end", f"[SHARED] {pair['a'].date} {pair['a'].name}")
            self.cmp_right_list.insert("end", f"[SHARED] {pair['b'].date} {pair['b'].name}")

        for h in result["unique_to_a"]:
            self.cmp_left_list.insert("end", f"{h.date} {h.name}")

        for h in result["unique_to_b"]:
            self.cmp_right_list.insert("end", f"{h.date} {h.name}")

    def _set_compare_loading(self, loading: bool) -> None:
        """Enable or disable comparison controls while API requests are running."""
        state = "disabled" if loading else "normal"
        self.compare_button.config(state=state)
        self.root.config(cursor="watch" if loading else "")

    def _on_save_comparison(self) -> None:
        """Save the most recent comparison result as a Markdown report."""
        if not self.current_comparison:
            messagebox.showwarning("Nothing to save", "Run a comparison first.")
            return
        path = self.file_manager.save_comparison(self.current_comparison)
        messagebox.showinfo("Saved", f"Comparison saved to:\n{path}")


def run() -> None:
    """Start the Tkinter event loop with a splash screen and main application window."""
    root: tk.Tk = tk.Tk()
    root.withdraw()

    def show_main() -> None:
        root.deiconify()
        HolidexApp(root)

    SplashScreen(root, on_complete=show_main)
    root.mainloop()


if __name__ == "__main__":
    run()