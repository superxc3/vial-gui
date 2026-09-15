# SPDX-License-Identifier: GPL-2.0-or-later

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import QTabWidget, QWidget, QScrollArea, QApplication, QVBoxLayout, QHBoxLayout, QLineEdit, \
    QLabel
from PyQt5.QtGui import QPalette

from constants import KEYCODE_BTN_RATIO
from widgets.display_keyboard import DisplayKeyboard
from widgets.display_keyboard_defs import ansi_100, ansi_80, ansi_70, iso_100, iso_80, iso_70, mods, mods_narrow
from widgets.flowlayout import FlowLayout
from keycodes.keycodes import KEYCODES_BASIC, KEYCODES_ISO, KEYCODES_MACRO, KEYCODES_LAYERS, KEYCODES_QUANTUM, \
    KEYCODES_BOOT, KEYCODES_MODIFIERS, \
    KEYCODES_BACKLIGHT, KEYCODES_MEDIA, KEYCODES_SPECIAL, KEYCODES_SHIFTED, KEYCODES_USER, Keycode, \
    KEYCODES_TAP_DANCE, KEYCODES_MIDI, KEYCODES_BASIC_NUMPAD, KEYCODES_BASIC_NAV, KEYCODES_ISO_KR
from widgets.square_button import SquareButton
from util import tr, KeycodeDisplay


class AlternativeDisplay(QWidget):

    keycode_changed = pyqtSignal(str)

    def __init__(self, kbdef, keycodes, prefix_buttons):
        super().__init__()

        self.kb_display = None
        self.keycodes = keycodes
        self.buttons = []

        self.key_layout = FlowLayout()

        if prefix_buttons:
            for title, code in prefix_buttons:
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.setText(title)
                btn.clicked.connect(lambda st, k=code: self.keycode_changed.emit(title))
                self.key_layout.addWidget(btn)

        layout = QVBoxLayout()
        if kbdef:
            self.kb_display = DisplayKeyboard(kbdef)
            self.kb_display.keycode_changed.connect(self.keycode_changed)
            layout.addWidget(self.kb_display)
            layout.setAlignment(self.kb_display, Qt.AlignHCenter)
        layout.addLayout(self.key_layout)
        self.setLayout(layout)

    def recreate_buttons(self, keycode_filter):
        for btn in self.buttons:
            btn.hide()
            btn.deleteLater()
        self.buttons = []

        for keycode in self.keycodes:
            if keycode.hidden or not keycode_filter(keycode.qmk_id):
                continue
            btn = SquareButton()
            btn.setRelSize(KEYCODE_BTN_RATIO)
            btn.setToolTip(Keycode.tooltip(keycode.qmk_id))
            btn.clicked.connect(lambda st, k=keycode: self.keycode_changed.emit(k.qmk_id))
            btn.keycode = keycode
            self.key_layout.addWidget(btn)
            self.buttons.append(btn)

        self.relabel_buttons()

    def relabel_buttons(self):
        if self.kb_display:
            self.kb_display.relabel_buttons()

        KeycodeDisplay.relabel_buttons(self.buttons)

    def required_width(self):
        return self.kb_display.sizeHint().width() if self.kb_display else 0

    def has_buttons(self):
        return len(self.buttons) > 0


class Tab(QScrollArea):

    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, alts, prefix_buttons=None):
        super().__init__(parent)

        self.label = label
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.alternatives = []
        for kb, keys in alts:
            alt = AlternativeDisplay(kb, keys, prefix_buttons)
            alt.keycode_changed.connect(self.keycode_changed)
            self.layout.addWidget(alt)
            self.alternatives.append(alt)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)

        w = QWidget()
        w.setLayout(self.layout)
        self.setWidget(w)

    def recreate_buttons(self, keycode_filter):
        for alt in self.alternatives:
            alt.recreate_buttons(keycode_filter)
        self.setVisible(self.has_buttons())

    def relabel_buttons(self):
        for alt in self.alternatives:
            alt.relabel_buttons()

    def has_buttons(self):
        for alt in self.alternatives:
            if alt.has_buttons():
                return True
        return False

    def select_alternative(self):
        # hide everything first
        for alt in self.alternatives:
            alt.hide()

        # then display first alternative which fits on screen w/o horizontal scroll
        for alt in self.alternatives:
            if self.width() - self.verticalScrollBar().width() > alt.required_width():
                alt.show()
                break

    def resizeEvent(self, evt):
        super().resizeEvent(evt)
        self.select_alternative()


class SimpleTab(Tab):

    def __init__(self, parent, label, keycodes):
        super().__init__(parent, label, [(None, keycodes)])


class SearchTab(QWidget):
    """ Finds keycodes across all the other tabs by label, QMK ID, alias or description,
    grouped by the tab they live in """

    keycode_changed = pyqtSignal(str)

    MAX_RESULTS = 80
    # wait for typing to pause before rebuilding the result buttons
    DEBOUNCE_MS = 150

    def __init__(self, parent, tabs):
        super().__init__(parent)

        self.label = "Search"
        self.tabs = tabs
        self.keycode_filter = keycode_filter_any
        self.buttons = []
        self.groups = []

        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("TabbedKeycodes", "Search keycodes..."))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.on_text_changed)
        # a quarter of the width is plenty and keeps the clear button close to the text
        search_row = QHBoxLayout()
        search_row.addWidget(self.search, 1)
        search_row.addStretch(3)

        self.hint = QLabel()
        self.hint.setWordWrap(True)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(self.DEBOUNCE_MS)
        self.timer.timeout.connect(self.refresh)

        self.results_layout = QVBoxLayout()
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        results = QWidget()
        results_outer = QVBoxLayout(results)
        results_outer.setContentsMargins(0, 0, 0, 0)
        results_outer.addLayout(self.results_layout)
        results_outer.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(results)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(search_row)
        layout.addWidget(self.hint)
        layout.addWidget(scroll)
        self.setLayout(layout)

        self.refresh()

    def on_text_changed(self):
        self.timer.start()

    def recreate_buttons(self, keycode_filter):
        # keyboard or filter changed: the dynamic keycodes (layers, macros...) may have changed too
        self.keycode_filter = keycode_filter
        self.refresh()

    def relabel_buttons(self):
        KeycodeDisplay.relabel_buttons(self.buttons)

    def has_buttons(self):
        return True

    def focus_search(self):
        self.search.setFocus()
        self.search.selectAll()

    def candidates(self):
        """ Every keycode shown in the other tabs, with the tab it belongs to, without duplicates """
        seen = set()
        for tab in self.tabs:
            for alt in tab.alternatives:
                for keycode in alt.keycodes:
                    if keycode.qmk_id in seen or keycode.hidden or not self.keycode_filter(keycode.qmk_id):
                        continue
                    seen.add(keycode.qmk_id)
                    yield tab.label, keycode

    @staticmethod
    def match_rank(keycode, query):
        """ Lower is better. 0: the label or QMK ID is the query, 1: starts with it, 2: contains it,
        3: an alias contains it, 4: every word appears somewhere in label/ID/aliases/description;
        None: no match """
        label = keycode.label.replace("\n", " ").lower()
        qmk_id = keycode.qmk_id.lower()
        short_id = qmk_id[3:] if qmk_id.startswith("kc_") else qmk_id
        if query in (label, qmk_id, short_id):
            return 0
        if label.startswith(query) or short_id.startswith(query):
            return 1
        if query in label or query in qmk_id:
            return 2
        aliases = [a.lower() for a in keycode.alias]
        if any(query in a for a in aliases):
            return 3
        haystack = " ".join([label, qmk_id, keycode.tooltip.lower() if keycode.tooltip else ""] + aliases)
        if all(word in haystack for word in query.split()):
            return 4
        return None

    def refresh(self):
        for btn in self.buttons:
            btn.hide()
            btn.deleteLater()
        for group in self.groups:
            group.hide()
            group.deleteLater()
        self.buttons = []
        self.groups = []

        query = " ".join(self.search.text().lower().split())
        if not query:
            self.hint.setText(tr("TabbedKeycodes", "Type a key name, QMK ID or description, e.g. \"sleep\", "
                                                   "\"eeh\" or \"reset\". Results are grouped by the tab the "
                                                   "keycode belongs to."))
            return

        # per tab, in tab order; within a tab best matches first, otherwise original order
        matches = {}
        total = 0
        for tab_label, keycode in self.candidates():
            rank = self.match_rank(keycode, query)
            if rank is None:
                continue
            matches.setdefault(tab_label, []).append((rank, keycode))
            total += 1

        if total == 0:
            self.hint.setText(tr("TabbedKeycodes", "No keycode matches \"{}\".").format(self.search.text()))
            return
        if total > self.MAX_RESULTS:
            self.hint.setText(tr("TabbedKeycodes", "{} matches, showing the first {}. Type more to narrow it down.")
                              .format(total, self.MAX_RESULTS))
        else:
            self.hint.setText(tr("TabbedKeycodes", "{} matches").format(total))

        shown = 0
        for tab_label, found in matches.items():
            found.sort(key=lambda entry: entry[0])
            group = QWidget()
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.addWidget(QLabel("<b>{}</b>".format(tr("TabbedKeycodes", tab_label))))
            flow = FlowLayout()
            for rank, keycode in found:
                if shown >= self.MAX_RESULTS:
                    break
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.setToolTip(self.tooltip(keycode))
                btn.clicked.connect(lambda st, k=keycode: self.keycode_changed.emit(k.qmk_id))
                btn.keycode = keycode
                flow.addWidget(btn)
                self.buttons.append(btn)
                shown += 1
            group_layout.addLayout(flow)
            self.results_layout.addWidget(group)
            self.groups.append(group)
            if shown >= self.MAX_RESULTS:
                break

        self.relabel_buttons()

    @staticmethod
    def tooltip(keycode):
        tooltip = Keycode.tooltip(keycode.qmk_id)
        aliases = [a for a in keycode.alias if a != keycode.qmk_id]
        if aliases:
            tooltip = "{}\n{}: {}".format(tooltip, tr("TabbedKeycodes", "Also known as"), ", ".join(aliases))
        return tooltip


def keycode_filter_any(kc):
    return True


def keycode_filter_masked(kc):
    return Keycode.is_basic(kc)


class FilteredTabbedKeycodes(QTabWidget):

    keycode_changed = pyqtSignal(str)
    anykey = pyqtSignal()

    def __init__(self, parent=None, keycode_filter=keycode_filter_any):
        super().__init__(parent)

        self.keycode_filter = keycode_filter

        self.tabs = [
            Tab(self, "Basic", [
                (ansi_100, KEYCODES_SPECIAL + KEYCODES_SHIFTED),
                (ansi_80, KEYCODES_SPECIAL + KEYCODES_BASIC_NUMPAD + KEYCODES_SHIFTED),
                (ansi_70, KEYCODES_SPECIAL + KEYCODES_BASIC_NUMPAD + KEYCODES_BASIC_NAV + KEYCODES_SHIFTED),
                (None, KEYCODES_SPECIAL + KEYCODES_BASIC + KEYCODES_SHIFTED),
            ], prefix_buttons=[("Any", -1)]),
            Tab(self, "ISO/JIS", [
                (iso_100, KEYCODES_SPECIAL + KEYCODES_SHIFTED + KEYCODES_ISO_KR),
                (iso_80, KEYCODES_SPECIAL + KEYCODES_BASIC_NUMPAD + KEYCODES_SHIFTED + KEYCODES_ISO_KR),
                (iso_70, KEYCODES_SPECIAL + KEYCODES_BASIC_NUMPAD + KEYCODES_BASIC_NAV + KEYCODES_SHIFTED +
                 KEYCODES_ISO_KR),
                (None, KEYCODES_ISO),
            ], prefix_buttons=[("Any", -1)]),
            SimpleTab(self, "Layers", KEYCODES_LAYERS),
            Tab(self, "Quantum", [(mods, (KEYCODES_BOOT + KEYCODES_QUANTUM)),
                                  (mods_narrow, (KEYCODES_BOOT + KEYCODES_QUANTUM)),
                                  (None, (KEYCODES_BOOT + KEYCODES_MODIFIERS + KEYCODES_QUANTUM))]),
            SimpleTab(self, "Backlight", KEYCODES_BACKLIGHT),
            SimpleTab(self, "App, Media and Mouse", KEYCODES_MEDIA),
            SimpleTab(self, "MIDI", KEYCODES_MIDI),
            SimpleTab(self, "Tap Dance", KEYCODES_TAP_DANCE),
            SimpleTab(self, "User", KEYCODES_USER),
            SimpleTab(self, "Macro", KEYCODES_MACRO),
        ]
        self.tabs.insert(0, SearchTab(self, list(self.tabs)))

        for tab in self.tabs:
            tab.keycode_changed.connect(self.on_keycode_changed)

        self.currentChanged.connect(self.on_current_changed)
        self.recreate_keycode_buttons()
        KeycodeDisplay.notify_keymap_override(self)

    def on_current_changed(self, index):
        widget = self.widget(index)
        if isinstance(widget, SearchTab):
            widget.focus_search()

    def on_keycode_changed(self, code):
        if code == "Any":
            self.anykey.emit()
        else:
            self.keycode_changed.emit(Keycode.normalize(code))

    def recreate_keycode_buttons(self):
        prev_tab = self.tabText(self.currentIndex()) if self.currentIndex() >= 0 else ""
        while self.count() > 0:
            self.removeTab(0)

        for tab in self.tabs:
            tab.recreate_buttons(self.keycode_filter)
            if tab.has_buttons():
                self.addTab(tab, tr("TabbedKeycodes", tab.label))
                if tab.label == prev_tab:
                    self.setCurrentIndex(self.count() - 1)

        # Search sits first for discoverability, but start on Basic like before
        if not prev_tab:
            for index in range(self.count()):
                if self.widget(index).label == "Basic":
                    self.setCurrentIndex(index)
                    break

    def on_keymap_override(self):
        for tab in self.tabs:
            tab.relabel_buttons()


class TabbedKeycodes(QWidget):

    keycode_changed = pyqtSignal(str)
    anykey = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.target = None
        self.is_tray = False

        self.layout = QVBoxLayout()

        self.all_keycodes = FilteredTabbedKeycodes()
        self.basic_keycodes = FilteredTabbedKeycodes(keycode_filter=keycode_filter_masked)
        for opt in [self.all_keycodes, self.basic_keycodes]:
            opt.keycode_changed.connect(self.keycode_changed)
            opt.anykey.connect(self.anykey)
            self.layout.addWidget(opt)

        self.setLayout(self.layout)
        self.set_keycode_filter(keycode_filter_any)

    @classmethod
    def set_tray(cls, tray):
        cls.tray = tray

    @classmethod
    def open_tray(cls, target, keycode_filter=None):
        cls.tray.set_keycode_filter(keycode_filter)
        cls.tray.show()
        if cls.tray.target is not None and cls.tray.target != target:
            cls.tray.target.deselect()
        cls.tray.target = target

    @classmethod
    def close_tray(cls):
        if cls.tray.target is not None:
            cls.tray.target.deselect()
        cls.tray.target = None
        cls.tray.hide()

    def make_tray(self):
        self.is_tray = True
        TabbedKeycodes.set_tray(self)

        self.keycode_changed.connect(self.on_tray_keycode_changed)
        self.anykey.connect(self.on_tray_anykey)

    def on_tray_keycode_changed(self, kc):
        if self.target is not None:
            self.target.on_keycode_changed(kc)

    def on_tray_anykey(self):
        if self.target is not None:
            self.target.on_anykey()

    def recreate_keycode_buttons(self):
        for opt in [self.all_keycodes, self.basic_keycodes]:
            opt.recreate_keycode_buttons()

    def set_keycode_filter(self, keycode_filter):
        if keycode_filter == keycode_filter_masked:
            self.all_keycodes.hide()
            self.basic_keycodes.show()
        else:
            self.all_keycodes.show()
            self.basic_keycodes.hide()
