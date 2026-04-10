# SPDX-License-Identifier: GPL-2.0-or-later
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QGroupBox,
                             QScrollArea, QFrame, QSizePolicy, QTabWidget,
                             QComboBox, QGridLayout)
from PyQt5.QtCore import Qt

from editor.basic_editor import BasicEditor
from vial_device import VialKeyboard

_PATCH = "Patch: F47A"
_MAX_CHARS = 5

# Widget definitions: (id, label, rows)
# rows = how many OLED rows (8px each) this widget occupies
WIDGETS = [
    (0x00, "Blank",             1),
    (0x01, "KB Name",           1),
    (0x02, "OS Detect",         1),
    (0x03, "Num Lock",          1),
    (0x04, "Caps Lock",         1),
    (0x05, "Layer Name",        1),
    (0x06, "DPI",               1),
    (0x07, "Scroll Speed",      1),
    (0x08, "Tracking Mode",     1),
    (0x0A, "WPM",               1),
    (0x10, "Gesture Bitmap",    2),
    (0x20, "Layer Number",      4),
    (0x30, "Calcifer Anim",    16),
]

_WID_TO_IDX = {wid: i for i, (wid, _, _) in enumerate(WIDGETS)}
_WID_ROWS   = {wid: rows for wid, _, rows in WIDGETS}


def _make_scrollable(inner_layout):
    w = QWidget()
    w.setLayout(inner_layout)
    w.setObjectName("oledInner")
    scroll = QScrollArea()
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setStyleSheet("QScrollArea { background-color: transparent; }")
    w.setStyleSheet("#oledInner { background-color: transparent; }")
    scroll.setWidgetResizable(True)
    scroll.setWidget(w)
    return scroll


def _centered_scroll(inner_layout):
    """Content constrained to natural width, centred horizontally."""
    content = QWidget()
    content.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
    content.setLayout(inner_layout)
    outer = QVBoxLayout()
    outer.addWidget(content)
    outer.setAlignment(content, Qt.AlignHCenter)
    return _make_scrollable(outer)


def _make_char_field(placeholder=""):
    """QLineEdit limited to 5 printable ASCII characters with live counter."""
    row = QWidget()
    row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    hl = QHBoxLayout(row)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(6)

    edit = QLineEdit()
    edit.setMaxLength(_MAX_CHARS)
    edit.setFixedWidth(80)
    edit.setPlaceholderText(placeholder)

    counter = QLabel("0/5")
    counter.setFixedWidth(28)

    def _on_change(text):
        counter.setText("{}/{}".format(len(text), _MAX_CHARS))

    edit.textChanged.connect(_on_change)
    hl.addWidget(edit)
    hl.addWidget(counter)
    hl.addStretch()

    row._edit = edit
    return row


class _ScreenPanel(QWidget):
    """16-slot widget slot editor for one OLED screen."""

    def __init__(self, screen_label, on_apply):
        super().__init__()
        self._on_apply_cb = on_apply

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        note = QLabel(
            "Each slot is one 8-pixel row on the {} OLED (portrait, 16 rows total).\n"
            "Multi-row widgets automatically occupy consecutive slots.\n"
            "Changes take effect immediately after clicking Apply.".format(screen_label)
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)
        grid.addWidget(QLabel("<b>Slot</b>"), 0, 0)
        grid.addWidget(QLabel("<b>Widget</b>"), 0, 1)
        grid.addWidget(QLabel("<b>Rows</b>"), 0, 2)

        self._combos = []
        self._row_labels = []
        for slot in range(16):
            lbl_slot = QLabel("{}".format(slot))
            lbl_slot.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            combo = QComboBox()
            for wid, name, rows in WIDGETS:
                combo.addItem("{} ({} row{})".format(name, rows, "s" if rows > 1 else ""),
                              userData=wid)
            combo.currentIndexChanged.connect(lambda _, s=slot: self._on_combo_changed(s))

            lbl_rows = QLabel("")
            lbl_rows.setAlignment(Qt.AlignCenter)

            grid.addWidget(lbl_slot, slot + 1, 0)
            grid.addWidget(combo, slot + 1, 1)
            grid.addWidget(lbl_rows, slot + 1, 2)

            self._combos.append(combo)
            self._row_labels.append(lbl_rows)

        layout.addLayout(grid)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn = QPushButton("Apply to Keyboard")
        btn.setMinimumWidth(200)
        btn.clicked.connect(self._on_apply)
        btn_row.addWidget(btn)
        layout.addLayout(btn_row)

    def _on_combo_changed(self, changed_slot):
        """Re-walk all 16 slots from 0 to recalculate which are occupied."""
        # Step 1: re-enable all combos so we start clean
        for combo in self._combos:
            combo.blockSignals(True)
            combo.setEnabled(True)
            combo.blockSignals(False)
        # Step 2: walk from slot 0, locking consumed downstream slots
        slot = 0
        while slot < 16:
            wid = self._combos[slot].currentData()
            rows = _WID_ROWS.get(wid, 1)
            self._row_labels[slot].setText(str(rows))
            for sub in range(1, rows):
                if slot + sub >= 16:
                    break
                sub_combo = self._combos[slot + sub]
                sub_combo.blockSignals(True)
                sub_combo.setCurrentIndex(0)   # BLANK placeholder
                sub_combo.setEnabled(False)
                sub_combo.blockSignals(False)
                self._row_labels[slot + sub].setText("(occ)")
            slot += rows

    def load_slots(self, slots):
        """Populate UI from a list of 16 widget IDs."""
        # First pass: unblock all combos
        for combo in self._combos:
            combo.blockSignals(True)
            combo.setEnabled(True)
        # Set values
        for i, wid in enumerate(slots[:16]):
            idx = _WID_TO_IDX.get(wid, 0)  # default to BLANK if unknown
            self._combos[i].setCurrentIndex(idx)
        for combo in self._combos:
            combo.blockSignals(False)
        # Trigger layout lock from slot 0
        self._on_combo_changed(0)

    def get_slots(self):
        """Read the 16 widget IDs from the UI (occupied slots emit their actual wid=0x00)."""
        slots = []
        for combo in self._combos:
            if combo.isEnabled():
                slots.append(combo.currentData())
            else:
                slots.append(0x00)  # occupied → BLANK in protocol
        return slots

    def _on_apply(self):
        self._on_apply_cb(self.get_slots())


class OledConfigurator(BasicEditor):

    def __init__(self):
        super().__init__()
        self.keyboard = None

        tabs_widget = QTabWidget()

        # ── Labels tab ────────────────────────────────────────────────────────
        inner = QVBoxLayout()
        inner.setContentsMargins(4, 4, 4, 4)
        inner.setSpacing(10)

        note = QLabel(
            "Text shown on the left OLED (master side).\n"
            "Maximum 5 characters — the OLED display width limit.\n"
            "Layer names are set per-layer in the Keymap tab.\n"
            "Changes take effect immediately after clicking Apply."
        )
        note.setWordWrap(True)
        inner.addWidget(note)

        # Keyboard name (row 1)
        kb_group = QGroupBox("Keyboard Name  (OLED row 1)")
        kb_layout = QHBoxLayout()
        kb_layout.setContentsMargins(8, 8, 8, 8)
        self.row1_field = _make_char_field("SOFLE")
        kb_layout.addWidget(QLabel("Display name:"))
        kb_layout.addWidget(self.row1_field)
        kb_layout.addStretch()
        kb_group.setLayout(kb_layout)
        inner.addWidget(kb_group)

        inner.addStretch()

        # Apply button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_apply = QPushButton("Apply to Keyboard")
        self.btn_apply.setMinimumWidth(200)
        self.btn_apply.clicked.connect(self._on_apply)
        btn_row.addWidget(self.btn_apply)
        inner.addLayout(btn_row)

        labels_page = QWidget()
        lp_layout = QVBoxLayout(labels_page)
        lp_layout.setContentsMargins(0, 0, 0, 0)
        lp_layout.addWidget(_centered_scroll(inner))
        tabs_widget.addTab(labels_page, "Labels")

        # ── Screen A tab (master OLED) ─────────────────────────────────────
        self._screen_a = _ScreenPanel("Master (Left)", self._on_apply_screen_a)
        sa_scroll = QScrollArea()
        sa_scroll.setFrameShape(QFrame.NoFrame)
        sa_scroll.setWidgetResizable(True)
        sa_scroll.setWidget(self._screen_a)
        tabs_widget.addTab(sa_scroll, "Screen A (Master)")

        # ── Screen B tab (slave OLED) ──────────────────────────────────────
        self._screen_b = _ScreenPanel("Slave (Right)", self._on_apply_screen_b)
        sb_scroll = QScrollArea()
        sb_scroll.setFrameShape(QFrame.NoFrame)
        sb_scroll.setWidgetResizable(True)
        sb_scroll.setWidget(self._screen_b)
        tabs_widget.addTab(sb_scroll, "Screen B (Slave)")

        self.addWidget(tabs_widget)

        version_lbl = QLabel(_PATCH)
        version_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.addWidget(version_lbl)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _populate(self):
        cfg = self.keyboard.oled_config
        self.row1_field._edit.setText(cfg.get('row1', 'SOFLE'))
        self._screen_a.load_slots(cfg.get('screen_a', [0] * 16))
        self._screen_b.load_slots(cfg.get('screen_b', [0] * 16))

    # ── Button handlers ───────────────────────────────────────────────────────

    def _on_apply(self):
        if not self.keyboard:
            return
        self.keyboard.set_oled_row1(self.row1_field._edit.text())

    def _on_apply_screen_a(self, slots):
        if not self.keyboard:
            return
        self.keyboard.set_oled_screen_slots(False, slots)

    def _on_apply_screen_b(self, slots):
        if not self.keyboard:
            return
        self.keyboard.set_oled_screen_slots(True, slots)

    # ── BasicEditor interface ─────────────────────────────────────────────────

    def valid(self):
        return (isinstance(self.device, VialKeyboard)
                and self.device.keyboard.oled_supported)

    def rebuild(self, device):
        super().rebuild(device)
        if not self.valid():
            self.keyboard = None
            return
        self.keyboard = device.keyboard
        self._populate()
