import os
import pprint
import queue
import random
import string
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractSpinBox, QApplication, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QSpinBox, QSizePolicy, QStackedWidget,
    QTextEdit, QVBoxLayout, QWidget,
)


APP_NAME = "LUXZ"
APP_VERSION = "v2.0.0"

# These lists are managed by the Library screen and stored in this source file.
# BEGIN EMBEDDED APP DATA
WORDLIST = []
USERNAME_LIST = ['fqmu',
 'xy6z',
 's052',
 'mu1j',
 '1iqq',
 'u52j',
 'x8ki',
 'yl20',
 'b5sb',
 'cfrp',
 'r8os',
 'lv0k',
 'r373',
 '697u',
 'dqwv',
 'ovyt',
 '27uw',
 'uiss',
 't9ru',
 'ixg7',
 'pxnj',
 '96q5',
 'od9j',
 '3dv3',
 'kzuy',
 'wjjk',
 '1j5u',
 'rp6u',
 '5yms',
 'yy3x',
 'ryqe',
 'hcd7',
 '4k77',
 'jdl3',
 'peg0',
 'v8b6',
 '1j5z',
 'lzs2',
 'kmnf',
 'zy4a',
 '429x',
 '41cq',
 '7lc4',
 '120l',
 'm0fu',
 '1m5b',
 'u0ka',
 'iup7',
 'btt3',
 '3pgk']
AVAILABLE_USERNAMES = []
# END EMBEDDED APP DATA

PLATFORMS = {
    "Roblox": {"min_len": 3, "max_len": 20, "max_workers": 10, "scan_delay": 0.15},
}
PLATFORM = "Roblox"

BG = "#050505"
SIDEBAR = "#090909"
PANEL = "#111111"
PANEL_ALT = "#171717"
INPUT = "#0b0b0b"
BORDER = "#292929"
TEXT = "#f5f5f5"
MUTED = "#a3a3a3"
WHITE = "#f3f3f3"


def check_username_roblox(username):
    try:
        response = requests.get(
            "https://auth.roblox.com/v1/usernames/validate",
            params={"Username": username, "Birthday": "2000-01-01", "Context": "Signup"},
            timeout=10,
        )
        data = response.json()
        return data.get("code") == 0, data.get("message", "")
    except requests.RequestException as exc:
        return None, str(exc)


def make_candidate(length, keyword=None, letters_only=False):
    chars = string.ascii_lowercase if letters_only else string.ascii_lowercase + string.digits
    if keyword:
        keyword = keyword.lower()
        if len(keyword) >= length:
            return keyword[:length]
        remaining = length - len(keyword)
        split = random.randint(0, remaining)
        return ("".join(random.choices(chars, k=split)) + keyword +
                "".join(random.choices(chars, k=remaining - split)))
    return "".join(random.choices(chars, k=length))


class LuxzApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} Username Tool")
        self.resize(1320, 850)
        self.setMinimumSize(1080, 720)

        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.executor = None
        self.wordlist = list(WORDLIST)
        self.username_list = list(USERNAME_LIST)
        self.available_usernames = list(AVAILABLE_USERNAMES)
        self.checked = 0
        self.hits = 0
        self.failed = 0
        self.status_text = "Ready"
        self.pages = {}

        self._build_shell()
        self._build_pages()
        self.show_page("Checker")
        self.event_timer = QTimer(self)
        self.event_timer.timeout.connect(self._process_events)
        self.event_timer.start(80)

    def _build_shell(self):
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(252)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(20, 26, 18, 18)
        side.setSpacing(7)

        brand_row = QHBoxLayout()
        brand_mark = QLabel("L")
        brand_mark.setObjectName("BrandMark")
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setFixedSize(42, 42)
        brand_row.addWidget(brand_mark)
        brand_copy = QVBoxLayout()
        brand_copy.setSpacing(1)
        brand_name = QLabel("LUXZ")
        brand_name.setObjectName("BrandName")
        brand_version = QLabel(APP_VERSION)
        brand_version.setObjectName("BrandVersion")
        brand_copy.addWidget(brand_name)
        brand_copy.addWidget(brand_version)
        brand_row.addLayout(brand_copy)
        brand_row.addStretch(1)
        side.addLayout(brand_row)

        section = QLabel("WORKSPACE")
        section.setObjectName("SectionLabel")
        section.setContentsMargins(5, 14, 0, 4)
        side.addWidget(section)

        self.nav_buttons = {}
        nav_items = (("Home", "Home"), ("Username Generator", "Checker"),
                     ("Results", "Results"), ("Library", "Library"),
                     ("Webhook settings", "Settings"), ("Help", "Help"))
        for label, name in nav_items:
            button = QPushButton(label)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, page=name: self.show_page(page))
            side.addWidget(button)
            self.nav_buttons[name] = button

        side.addStretch(1)
        status_card = self._card()
        status_layout = status_card.layout()
        status_layout.setContentsMargins(16, 13, 16, 13)
        status_layout.setSpacing(5)
        status_title = QLabel("STATUS")
        status_title.setObjectName("SectionLabel")
        self.sidebar_status = QLabel("Not scanning")
        self.sidebar_status.setObjectName("StatusValue")
        status_layout.addWidget(status_title)
        status_layout.addWidget(self.sidebar_status)
        self.sidebar_progress = QProgressBar()
        self.sidebar_progress.setObjectName("SidebarProgress")
        self.sidebar_progress.setTextVisible(False)
        self.sidebar_progress.setRange(0, 100)
        self.sidebar_progress.setValue(0)
        status_layout.addWidget(self.sidebar_progress)
        status_card.setMinimumHeight(92)
        side.addWidget(status_card)
        shell.addWidget(sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(34, 20, 34, 24)
        content_layout.setSpacing(0)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 22)
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        self.page_title = QLabel()
        self.page_title.setObjectName("PageTitle")
        self.page_subtitle = QLabel()
        self.page_subtitle.setObjectName("PageSubtitle")
        title_stack.addWidget(self.page_title)
        title_stack.addWidget(self.page_subtitle)
        header.addLayout(title_stack)
        header.addStretch(1)
        content_layout.addLayout(header)

        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, 1)
        shell.addWidget(content, 1)
        self.setStyleSheet(self._stylesheet())

    def _stylesheet(self):
        return f"""
            QWidget {{ color: {TEXT}; font-family: 'Segoe UI'; font-size: 10pt; }}
            QMainWindow {{ background: {BG}; }}
            QWidget#Root {{ background: {BG}; }}
            QWidget#Page {{ background: transparent; }}
            #Sidebar {{ background: {SIDEBAR}; border-right: 1px solid {BORDER}; }}
            #BrandMark {{ background: {WHITE}; color: #080808; border-radius: 11px; font-size: 18pt; font-weight: 800; }}
            #BrandName {{ font-size: 14pt; font-weight: 800; }}
            #BrandVersion, #PageSubtitle {{ color: {MUTED}; font-size: 9pt; }}
            #SectionLabel {{ color: #777777; font-size: 8pt; font-weight: 700; letter-spacing: 1px; }}
            #PageTitle {{ color: {TEXT}; font-size: 25pt; font-weight: 750; }}
            #StatusValue {{ color: {TEXT}; font-weight: 700; }}
            QFrame#Card {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 15px; }}
            QFrame#ModeCard {{ background: {PANEL_ALT}; border: 1px solid {BORDER}; border-radius: 11px; }}
            QLabel#CardTitle {{ font-size: 12pt; font-weight: 700; }}
            QPushButton {{ background: {PANEL_ALT}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 10px; padding: 10px 16px; font-weight: 650; }}
            QPushButton:hover {{ background: #252525; border-color: #4a4a4a; }}
            QPushButton:pressed {{ background: #333333; }}
            QPushButton#PrimaryButton {{ background: {WHITE}; color: #080808; border: 1px solid {WHITE}; }}
            QPushButton#PrimaryButton:hover {{ background: #ffffff; }}
            QPushButton#StopButton {{ background: transparent; color: {TEXT}; }}
            QPushButton#NavButton {{ text-align: left; background: transparent; border: 1px solid transparent; padding: 11px 12px; border-radius: 9px; color: #b1b1b1; }}
            QPushButton#NavButton:hover {{ color: white; background: #171717; }}
            QPushButton#NavButton:checked {{ color: white; background: #242424; border: 1px solid #414141; }}
            QLineEdit, QComboBox, QSpinBox, QTextEdit, QListWidget {{ background: {INPUT}; border: 1px solid {BORDER}; border-radius: 9px; selection-background-color: #555555; }}
            QLineEdit, QComboBox, QSpinBox {{ min-height: 40px; padding: 0 11px; }}
            QTextEdit {{ padding: 9px 11px; }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {{ border: 1px solid #666666; }}
            QComboBox::drop-down {{ border: 0; width: 28px; }}
            QComboBox QAbstractItemView {{ background: #171717; border: 1px solid #393939; selection-background-color: #393939; }}
            QCheckBox, QRadioButton {{ spacing: 8px; color: #dedede; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid #555555; border-radius: 4px; background: #080808; }}
            QCheckBox::indicator:checked {{ background: #f3f3f3; border: 1px solid #f3f3f3; }}
            QCheckBox::indicator:hover {{ border-color: #ffffff; }}
            QRadioButton::indicator {{ width: 15px; height: 15px; border: 1px solid #666666; border-radius: 8px; background: #080808; }}
            QRadioButton::indicator:checked {{ background: #f3f3f3; border: 1px solid #f3f3f3; }}
            QRadioButton::indicator:hover {{ border-color: #ffffff; }}
            QProgressBar {{ background: #222222; border: 0; border-radius: 5px; height: 9px; text-align: center; }}
            QProgressBar::chunk {{ background: #eeeeee; border-radius: 5px; }}
            QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
            QScrollBar::handle:vertical {{ background: #383838; min-height: 28px; border-radius: 5px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """

    def _card(self, title=None):
        card = QFrame()
        card.setObjectName("Card")
        card.setFrameShape(QFrame.Shape.NoFrame)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(13)
        if title:
            label = QLabel(title)
            label.setObjectName("CardTitle")
            layout.addWidget(label)
        return card

    def _button(self, text, callback, primary=False, stop=False):
        button = QPushButton(text)
        if primary:
            button.setObjectName("PrimaryButton")
        if stop:
            button.setObjectName("StopButton")
        button.clicked.connect(callback)
        return button

    def _label(self, text):
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        label.setStyleSheet("color: #a5a5a5; font-size: 9pt; font-weight: 600;")
        return label

    def _build_pages(self):
        self._build_home()
        self._build_checker()
        self._build_results()
        self._build_library()
        self._build_settings()
        self._build_help()

    def _add_page(self, name, title, subtitle):
        page = QWidget()
        page.setObjectName("Page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        self.stack.addWidget(page)
        self.pages[name] = (page, layout, title, subtitle)
        return page, layout

    def show_page(self, name):
        name = "Checker" if name == "Generator" else name
        page, _layout, title, subtitle = self.pages[name]
        self.stack.setCurrentWidget(page)
        self.page_title.setText(title)
        self.page_subtitle.setText(subtitle)
        for nav_name, button in self.nav_buttons.items():
            button.setChecked(nav_name == name)
        if name == "Results":
            self._refresh_results()
        elif name == "Library":
            self._refresh_library()

    def _build_home(self):
        page, layout = self._add_page("Home", "Dashboard", "Your username discovery workspace")
        welcome = QLabel("Welcome back")
        welcome.setStyleSheet("font-size: 17pt; font-weight: 700;")
        desc = QLabel("Generate usernames, check them automatically, and review your results.")
        desc.setStyleSheet(f"color: {MUTED};")
        layout.addWidget(welcome)
        layout.addWidget(desc)

        stats = QHBoxLayout()
        self.home_checked = self._stat_card("Checked", "0")
        self.home_hits = self._stat_card("Available", "0")
        self.home_failed = self._stat_card("Failed", "0")
        for stat in (self.home_checked, self.home_hits, self.home_failed):
            stats.addWidget(stat)
        layout.addLayout(stats)

        actions = self._card("Quick actions")
        row = QHBoxLayout()
        row.addWidget(self._button("Open Username Generator", lambda: self.show_page("Checker"), primary=True))
        row.addWidget(self._button("Manage lists", lambda: self.show_page("Library")))
        row.addStretch(1)
        actions.layout().addLayout(row)
        layout.addWidget(actions)

        library = self._card("Embedded data")
        self.home_data_summary = QLabel()
        self.home_data_summary.setStyleSheet(f"color: {MUTED}; line-height: 1.6;")
        library.layout().addWidget(self.home_data_summary)
        layout.addWidget(library)
        layout.addStretch(1)
        self._update_home_stats()

    def _stat_card(self, label, value):
        card = self._card()
        card.setMinimumHeight(92)
        title = QLabel(label.upper())
        title.setStyleSheet(f"color: {MUTED}; font-size: 8pt; font-weight: 700; letter-spacing: 1px;")
        number = QLabel(value)
        number.setObjectName("StatValue")
        number.setStyleSheet("font-size: 22pt; font-weight: 750;")
        card.layout().addWidget(title)
        card.layout().addWidget(number)
        card.layout().addStretch(1)
        card.value_label = number
        return card

    def _update_home_stats(self):
        self.home_checked.value_label.setText(f"{self.checked:,}")
        self.home_hits.value_label.setText(f"{self.hits:,}")
        self.home_failed.value_label.setText(f"{self.failed:,}")
        self.home_data_summary.setText(
            f"Word bank   ·   {len(self.wordlist):,} words\n"
            f"Available results   ·   {len(self.available_usernames):,} usernames"
        )

    def _build_checker(self):
        page, layout = self._add_page(
            "Checker", "Username Generator", "Create usernames and check them automatically"
        )
        columns = QHBoxLayout()
        columns.setSpacing(16)
        left = self._card()
        left.setMinimumWidth(330)
        left.setMaximumWidth(440)
        right = self._card("Telemetry")
        columns.addWidget(left, 4)
        columns.addWidget(right, 6)
        layout.addLayout(columns, 1)

        form = left.layout()
        run_heading = QLabel("Run settings")
        run_heading.setObjectName("CardTitle")
        form.addWidget(run_heading)
        self.generation_section = QFrame()
        self.generation_section.setObjectName("ModeCard")
        self.generation_section.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        generation_layout = QVBoxLayout(self.generation_section)
        generation_layout.setContentsMargins(13, 12, 13, 13)
        generation_layout.setSpacing(8)
        generation_layout.addWidget(self._label("Generation options"))
        self.gen_mode = QComboBox()
        self.gen_mode.addItems(("Random letters + numbers", "Two-word combinations"))
        self.gen_mode.currentIndexChanged.connect(self._sync_generation_mode)
        self.gen_mode.currentIndexChanged.connect(self._clear_telemetry_for_mode_change)
        generation_layout.addWidget(self.gen_mode)
        self.gen_mode_hint = QLabel()
        self.gen_mode_hint.setWordWrap(True)
        self.gen_mode_hint.setStyleSheet(f"color: {MUTED}; font-size: 9pt;")
        generation_layout.addWidget(self.gen_mode_hint)

        self.length_count_section = QWidget()
        length_count = QHBoxLayout(self.length_count_section)
        length_count.setContentsMargins(0, 0, 0, 0)
        length_count.setSpacing(10)
        self.length_column = QWidget()
        length_layout = QVBoxLayout(self.length_column)
        length_layout.setContentsMargins(0, 0, 0, 0)
        length_layout.setSpacing(5)
        length_layout.addWidget(self._label("Name length"))
        self.gen_length = QSpinBox()
        self.gen_length.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.gen_length.setRange(2, 32)
        self.gen_length.setValue(4)
        length_layout.addWidget(self.gen_length)
        count_column = QVBoxLayout()
        count_column.addWidget(self._label("Number of names"))
        self.gen_count = QSpinBox()
        self.gen_count.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.gen_count.setRange(1, 50000)
        self.gen_count.setValue(50)
        count_column.addWidget(self.gen_count)
        length_count.addWidget(self.length_column, 1)
        length_count.addLayout(count_column, 1)
        generation_layout.addWidget(self.length_count_section)

        self.keyword_section = QWidget()
        keyword_layout = QVBoxLayout(self.keyword_section)
        keyword_layout.setContentsMargins(0, 0, 0, 0)
        keyword_layout.setSpacing(5)
        keyword_layout.addWidget(self._label("Keyword (optional)"))
        self.gen_keyword = QLineEdit()
        self.gen_keyword.setPlaceholderText("Include this text in random names")
        keyword_layout.addWidget(self.gen_keyword)
        generation_layout.addWidget(self.keyword_section)
        self.gen_letters = QCheckBox("Letters only — exclude numbers")
        generation_layout.addWidget(self.gen_letters)
        form.addWidget(self.generation_section)

        thread_row = QHBoxLayout()
        thread_row.addWidget(self._label("Generation speed"))
        thread_row.addStretch(1)
        self.thread_spin = QSpinBox()
        self.thread_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.thread_spin.setRange(1, 10)
        self.thread_spin.setValue(2)
        self.thread_spin.setFixedWidth(100)
        thread_row.addWidget(self.thread_spin)
        form.addLayout(thread_row)

        controls = QHBoxLayout()
        self.start_btn = self._button("Generate & check", self._generate_list, primary=True)
        self.stop_btn = self._button("×  Stop", self._stop_run, stop=True)
        self.stop_btn.hide()
        controls.addWidget(self.start_btn)
        controls.addWidget(self.stop_btn)
        controls.addStretch(1)
        form.addLayout(controls)
        hint = QLabel("Every generated Roblox name is saved and checked immediately.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {MUTED}; font-size: 9pt;")
        form.addWidget(hint)
        form.addStretch(1)

        telemetry = right.layout()
        metrics = QHBoxLayout()
        metrics.setSpacing(9)
        self.metric_labels = {}
        for label in ("CHECKED", "HITS", "TAKEN", "FAILED", "SPEED"):
            tile = QFrame()
            tile.setObjectName("MetricTile")
            tile.setStyleSheet(f"QFrame#MetricTile {{ background: {PANEL_ALT}; border: 1px solid {BORDER}; border-radius: 10px; }}")
            tile_layout = QVBoxLayout(tile)
            tile_layout.setContentsMargins(12, 10, 12, 10)
            tile_layout.setSpacing(3)
            caption = QLabel(label)
            caption.setStyleSheet(f"color: {MUTED}; font-size: 8pt; font-weight: 700;")
            value = QLabel("0/s" if label == "SPEED" else "0")
            value.setStyleSheet("font-size: 15pt; font-weight: 750;")
            tile_layout.addWidget(caption)
            tile_layout.addWidget(value)
            metrics.addWidget(tile, 1)
            self.metric_labels[label] = value
        telemetry.addLayout(metrics)
        self.progress_label = QLabel("Idle")
        progress_row = QHBoxLayout()
        progress_row.addWidget(self.progress_label)
        progress_row.addStretch(1)
        self.progress_percent = QLabel("0%")
        self.progress_percent.setStyleSheet("font-weight: 700;")
        progress_row.addWidget(self.progress_percent)
        telemetry.addLayout(progress_row)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        telemetry.addWidget(self.progress)
        self.live_box = QListWidget()
        self.live_box.setMinimumHeight(230)
        telemetry.addWidget(self.live_box, 1)
        self._sync_generation_mode()
        self._sync_thread_limit()

    def _sync_generation_mode(self, *_args):
        random_mode = self.gen_mode.currentIndex() == 0
        self.length_count_section.setVisible(random_mode)
        self.keyword_section.setVisible(random_mode)
        self.gen_letters.setVisible(random_mode)
        if random_mode:
            self.gen_mode_hint.setText(
                "Create random names from letters and numbers. Add an optional keyword; "
                "turn on Letters only to leave out digits."
            )
        else:
            self.gen_mode_hint.setText(
                "Combine every word with every other word in the Library word bank. "
                "All combinations that fit Roblox's username rules will be checked; "
                "there is no name-count limit."
            )

    def _clear_telemetry_for_mode_change(self, *_args):
        if self.executor is not None:
            return
        self.checked = self.hits = self.failed = 0
        self.live_box.clear()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress_label.setText("Idle · mode changed")
        self.progress_percent.setText("0%")
        self._update_metrics("0/s")
        self._set_status("Ready")

    def _sync_thread_limit(self, *_args):
        self.thread_spin.setMaximum(PLATFORMS[PLATFORM]["max_workers"])

    def _sync_gen_length(self, *_args):
        platform = PLATFORM
        settings = PLATFORMS[platform]
        self.gen_length.setRange(settings["min_len"], settings["max_len"])
        self.gen_length.setValue(min(max(self.gen_length.value(), settings["min_len"]), settings["max_len"]))

    def _generate_list(self):
        platform = PLATFORM
        settings = PLATFORMS[platform]
        length = self.gen_length.value()
        count = self.gen_count.value()
        keyword = self.gen_keyword.text().strip() or None
        if self.gen_mode.currentIndex() != 0:
            keyword = None
        if keyword and len(keyword) > length:
            QMessageBox.warning(self, "Generator", "Keyword is longer than the selected length.")
            return

        generated, seen = [], set()
        if self.gen_mode.currentIndex() == 1:
            words = list(dict.fromkeys(x.strip().lower() for x in self.wordlist if x.strip()))
            if len(words) < 2:
                QMessageBox.warning(self, "Word bank", "Add at least 2 different words in the Library first.")
                return
            for a in words:
                for b in words:
                    if a == b:
                        continue
                    candidate = a + b
                    if (settings["min_len"] <= len(candidate) <= settings["max_len"]
                            and candidate not in seen):
                        seen.add(candidate)
                        generated.append(candidate)
        else:
            attempts = 0
            while len(generated) < count and attempts < count * 20:
                attempts += 1
                candidate = make_candidate(length, keyword, self.gen_letters.isChecked())
                if candidate not in seen:
                    seen.add(candidate)
                    generated.append(candidate)

        if not generated:
            QMessageBox.information(self, "Generator", "No names matched the selected pattern and platform length.")
            return
        self.username_list = generated
        self._set_status(f"Generated {len(generated):,}; checking now")
        self._update_home_stats()
        self._start_scan(usernames=generated)

    def _start_scan(self, usernames):
        if self.executor is not None:
            return
        platform = PLATFORM
        if not usernames:
            QMessageBox.warning(self, "Checker", "No usernames were supplied.")
            return

        settings = PLATFORMS[platform]
        workers = min(max(1, self.thread_spin.value()), settings["max_workers"])
        self.stop_event.clear()
        self.checked = self.hits = self.failed = 0
        self._update_metrics("0/s")
        self.live_box.clear()
        self.progress.setRange(0, len(usernames))
        self.progress.setValue(0)
        self.sidebar_progress.setValue(0)
        self.progress_label.setText(f"Checking 0/{len(usernames)}")
        self.progress_percent.setText("0%")
        self.start_btn.setEnabled(False)
        self.stop_btn.show()
        self.gen_mode.setEnabled(False)
        self._set_status(f"Running · {platform}")
        self.executor = ThreadPoolExecutor(max_workers=workers)
        self._scan_total = len(usernames)
        self._scan_started = time.time()
        self._scan_found = []
        for username in usernames:
            self.executor.submit(self._scan_one, username, settings["scan_delay"])
        threading.Thread(target=self._finish_executor, daemon=True).start()

    def _scan_one(self, username, delay):
        if self.stop_event.is_set():
            return
        available, message = check_username_roblox(username)
        if self.stop_event.is_set():
            return
        self.events.put(("result", username, available, message))
        if delay:
            self.stop_event.wait(delay)

    def _finish_executor(self):
        executor = self.executor
        if executor is not None:
            executor.shutdown(wait=True)
        self.events.put(("finished",))

    def _stop_run(self):
        if self.executor is None:
            return
        self.stop_event.set()
        self._set_status("Stopping…")
        self.progress_label.setText("Stopping…")

    def _process_events(self):
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            if event[0] == "result":
                _, username, available, message = event
                self.checked += 1
                if available is True:
                    self.hits += 1
                    self._scan_found.append(username)
                    line = f"✓   {username}     AVAILABLE"
                    self._send_webhook(username)
                elif available is False:
                    line = f"·   {username}     TAKEN"
                else:
                    self.failed += 1
                    line = f"!   {username}     {message}"
                self.live_box.insertItem(0, line)
                while self.live_box.count() > 250:
                    self.live_box.takeItem(self.live_box.count() - 1)
                elapsed = max(time.time() - self._scan_started, 0.001)
                self._update_metrics(f"{self.checked / elapsed:.0f}/s")
                self.progress.setValue(self.checked)
                percent = round(self.checked / max(self._scan_total, 1) * 100)
                self.progress_percent.setText(f"{percent}%")
                self.sidebar_progress.setValue(percent)
                self.progress_label.setText(f"Checking {self.checked:,}/{self._scan_total:,}")
            elif event[0] == "finished":
                self._scan_complete()

    def _update_metrics(self, speed):
        self.metric_labels["CHECKED"].setText(f"{self.checked:,}")
        self.metric_labels["HITS"].setText(f"{self.hits:,}")
        self.metric_labels["TAKEN"].setText(f"{max(self.checked - self.hits - self.failed, 0):,}")
        self.metric_labels["FAILED"].setText(f"{self.failed:,}")
        self.metric_labels["SPEED"].setText(speed)
        self._update_home_stats()

    def _scan_complete(self):
        if self.executor is None:
            return
        self.executor = None
        found = list(dict.fromkeys(self._scan_found))
        if found:
            self.available_usernames = list(dict.fromkeys(self.available_usernames + found))
            self._write_embedded_data()
        stopped = self.stop_event.is_set() and self.checked < self._scan_total
        self._set_status("Stopped" if stopped else "Ready")
        self.sidebar_progress.setValue(0)
        self.progress_label.setText("Stopped" if stopped else f"Complete · {self.checked:,} checked")
        self.start_btn.setEnabled(True)
        self.stop_btn.hide()
        self.gen_mode.setEnabled(True)
        self._update_home_stats()

    def _send_webhook(self, username):
        url = self.webhook_edit.text().strip()
        if not url:
            return

        def worker():
            try:
                requests.post(
                    url,
                    json={"content": f"**Available Roblox username found:** `{username}`"},
                    timeout=10,
                )
            except requests.RequestException:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _build_results(self):
        page, layout = self._add_page("Results", "Results", "Review usernames saved from completed scans")
        card = self._card("Available usernames")
        tools = QHBoxLayout()
        self.result_count = QLabel("0 saved")
        self.result_count.setStyleSheet(f"color: {MUTED};")
        tools.addWidget(self._button("Clear", self._clear_results, primary=True))
        tools.addStretch(1)
        tools.addWidget(self.result_count)
        card.layout().addLayout(tools)
        self.results_list = QListWidget()
        card.layout().addWidget(self.results_list, 1)
        layout.addWidget(card, 1)

    def _refresh_results(self):
        if not hasattr(self, "results_list"):
            return
        self.results_list.clear()
        self.results_list.addItems(self.available_usernames)
        self.result_count.setText(f"{len(self.available_usernames):,} saved")

    def _clear_results(self):
        if not self.available_usernames:
            self._refresh_results()
            return
        self.available_usernames = []
        if not self._write_embedded_data():
            return
        self._refresh_results()
        self._update_home_stats()
        self._set_status("Saved results cleared")

    def _build_library(self):
        page, layout = self._add_page("Library", "Data Library", "Edit the lists embedded in this Python program")
        desc = QLabel("Changes are saved directly into luxz.py, so the app stays self-contained.")
        desc.setStyleSheet(f"color: {MUTED};")
        layout.addWidget(desc)
        columns = QHBoxLayout()
        columns.setSpacing(14)
        self.library_boxes = {}
        datasets = (
            ("wordlist", "Word bank", self.wordlist, "One word per line · used for two-word generation"),
        )
        for key, title, data, hint in datasets:
            card = self._card(title)
            hint_label = QLabel(hint)
            hint_label.setWordWrap(True)
            hint_label.setStyleSheet(f"color: {MUTED}; font-size: 9pt;")
            card.layout().addWidget(hint_label)
            editor = QTextEdit()
            editor.setPlaceholderText("Enter one item per line…")
            editor.setPlainText("\n".join(data))
            card.layout().addWidget(editor, 1)
            self.library_boxes[key] = editor
            if key == "wordlist":
                editor.textChanged.connect(self._update_word_bank_buffer)
            columns.addWidget(card, 1)
        layout.addLayout(columns, 1)
        footer = QHBoxLayout()
        self.library_status = QLabel("Edits apply now · save to keep them after closing.")
        self.library_status.setStyleSheet(f"color: {MUTED};")
        footer.addWidget(self.library_status)
        footer.addStretch(1)
        footer.addWidget(self._button("Clear word bank", self._clear_word_bank))
        footer.addWidget(self._button("Save embedded data", self._save_library, primary=True))
        layout.addLayout(footer)

    def _refresh_library(self):
        # Keep the word bank editor buffer across navigation.
        return

    def _update_word_bank_buffer(self):
        editor = self.library_boxes["wordlist"]
        self.wordlist = list(dict.fromkeys(
            line.strip() for line in editor.toPlainText().splitlines() if line.strip()
        ))
        if hasattr(self, "library_status"):
            self.library_status.setText("Word bank edited · save embedded data to keep changes after restart.")
        self._update_home_stats()

    def _save_library(self):
        def read_lines(key):
            return list(dict.fromkeys(line.strip() for line in
                self.library_boxes[key].toPlainText().splitlines() if line.strip()))
        self.wordlist = read_lines("wordlist")
        if not self._write_embedded_data():
            return
        self.library_status.setText(f"Saved · {len(self.wordlist):,} words")
        self._set_status("Embedded data saved")
        self._refresh_results()
        self._update_home_stats()

    def _clear_word_bank(self):
        self.library_boxes["wordlist"].clear()
        self._save_library()

    def _write_embedded_data(self):
        try:
            with open(__file__, "r", encoding="utf-8") as source:
                program = source.read()
            start_marker = "# BEGIN EMBEDDED APP DATA"
            end_marker = "# END EMBEDDED APP DATA"
            start = program.index(start_marker) + len(start_marker)
            end = program.index(end_marker, start)
            block = (
                "\nWORDLIST = " + pprint.pformat(self.wordlist, width=76) +
                "\nUSERNAME_LIST = " + pprint.pformat(self.username_list, width=76) +
                "\nAVAILABLE_USERNAMES = " + pprint.pformat(self.available_usernames, width=76) + "\n"
            )
            temp_path = __file__ + ".tmp"
            with open(temp_path, "w", encoding="utf-8", newline="\n") as target:
                target.write(program[:start] + block + program[end:])
            os.replace(temp_path, __file__)
            return True
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Save embedded data", f"Could not update the Python program:\n{exc}")
            return False

    def _build_settings(self):
        page, layout = self._add_page("Settings", "Discord webhook", "Optional notifications for available names")
        notifications = self._card("Discord webhook")
        notifications.layout().addWidget(self._label("Webhook URL"))
        self.webhook_edit = QLineEdit()
        self.webhook_edit.setPlaceholderText("Paste a Discord webhook URL (optional)")
        notifications.layout().addWidget(self.webhook_edit)
        webhook_hint = QLabel("When set, every available Roblox username found is sent to this webhook.")
        webhook_hint.setWordWrap(True)
        webhook_hint.setStyleSheet(f"color: {MUTED};")
        notifications.layout().addWidget(webhook_hint)
        layout.addWidget(notifications)
        layout.addStretch(1)

    def _build_help(self):
        page, layout = self._add_page("Help", "Help", "A quick guide to the tools in LUXZ")
        card = self._card("About LUXZ")
        about = QLabel(
            "Username Generator  ·  Generate usernames and check each one automatically.\n\n"
            "Library  ·  Edit the word bank used for two-word generation.\n\n"
            "Results  ·  Review names found during completed scans.\n\n"
            "Webhook settings  ·  Add an optional Discord webhook for available usernames."
        )
        about.setWordWrap(True)
        card.layout().addWidget(about)
        layout.addWidget(card)
        layout.addStretch(1)

    def _set_status(self, text):
        self.status_text = text
        scanning = text.startswith(("Running", "Stopping"))
        self.sidebar_status.setText("Scanning" if scanning else "Not scanning")


if __name__ == "__main__":
    app = QApplication([])
    app.setStyle("Fusion")
    window = LuxzApp()
    window.show()
    app.exec()
