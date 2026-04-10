# SPDX-License-Identifier: GPL-2.0-or-later
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QGroupBox,
                             QScrollArea, QFrame, QSizePolicy, QTabWidget,
                             QComboBox, QToolButton)
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPainter, QColor, QFont, QPen

from editor.basic_editor import BasicEditor
from vial_device import VialKeyboard

_PATCH = "Patch: F47A"
_MAX_CHARS = 5
_OLED_ROWS = 16          # portrait OLED: 16 rows of 8 px each = 128 px tall
_PREV_ROW_H = 20         # preview pixel height per OLED row
_PREV_W     = 80         # preview widget width (OLED is 32 px physical → 2.5×)
_PREV_H     = _OLED_ROWS * _PREV_ROW_H   # 320 px

# Widget definitions: (id, label, rows, preview_color_rgb)
WIDGETS = [
    (0x00, "Blank",           1,  (30,  30,  30)),
    (0x01, "KB Name",         1,  (30,  80, 160)),
    (0x02, "OS Detect",       1,  (100, 40, 160)),
    (0x03, "Num Lock",        1,  (160, 90,  20)),
    (0x04, "Caps Lock",       1,  (160, 30,  30)),
    (0x05, "Layer Name",      1,  (30, 140,  60)),
    (0x06, "DPI",             1,  (20, 140, 140)),
    (0x07, "Scroll Speed",    1,  (20, 110, 130)),
    (0x08, "Tracking Mode",   1,  (140, 130, 20)),
    (0x0A, "WPM",             1,  (80, 160,  20)),
    (0x10, "Gesture Bitmap",  2,  (60,  60, 180)),
    (0x20, "Layer Number",    4,  (100, 20, 140)),
    (0x30, "Calcifer Anim",  16,  (180, 70,  10)),
]

_WID_META  = {wid: (name, rows, color) for wid, name, rows, color in WIDGETS}
_WID_ROWS  = {wid: rows  for wid, _, rows, _ in WIDGETS}
_WID_COLOR = {wid: color for wid, _, _, color in WIDGETS}
_WID_NAME  = {wid: name  for wid, name, _, _ in WIDGETS}


def _slots_from_blocks(block_wids):
    """Convert ordered block list → 16-element slot array the firmware reads."""
    slots = [0] * _OLED_ROWS
    idx = 0
    for wid in block_wids:
        if idx >= _OLED_ROWS:
            break
        rows = _WID_ROWS.get(wid, 1)
        slots[idx] = wid
        idx += rows
    return slots


def _blocks_from_slots(slots):
    """Convert 16-element slot array → ordered block list (skip occupied rows)."""
    blocks = []
    idx = 0
    while idx < _OLED_ROWS:
        wid = slots[idx] if idx < len(slots) else 0
        rows = _WID_ROWS.get(wid, 1)
        blocks.append(wid)
        idx += rows
    return blocks


def _total_rows(block_wids):
    return sum(_WID_ROWS.get(w, 1) for w in block_wids)


# ── Live OLED preview ─────────────────────────────────────────────────────────

class OledPreview(QWidget):
    """Scaled-up portrait OLED preview with colour-coded widget zones."""

    def __init__(self):
        super().__init__()
        self._slots = [0] * _OLED_ROWS
        self.setFixedSize(_PREV_W, _PREV_H)
        self.setToolTip("Live OLED layout preview ({}×{} rows)".format(_PREV_W, _OLED_ROWS))

    def update_slots(self, slots):
        self._slots = list(slots)[:_OLED_ROWS]
        while len(self._slots) < _OLED_ROWS:
            self._slots.append(0)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)

        # Black OLED background
        p.fillRect(self.rect(), QColor(0, 0, 0))

        # Walk slots, paint each widget block
        idx = 0
        while idx < _OLED_ROWS:
            wid = self._slots[idx]
            rows = _WID_ROWS.get(wid, 1)
            rgb  = _WID_COLOR.get(wid, (40, 40, 40))
            name = _WID_NAME.get(wid, "?")

            y = idx * _PREV_ROW_H
            h = rows * _PREV_ROW_H

            if wid != 0x00:
                p.fillRect(QRect(1, y + 1, _PREV_W - 2, h - 2),
                            QColor(*rgb))
                p.setPen(QColor(220, 220, 220))
                fnt = QFont("Arial", 7)
                fnt.setBold(True)
                p.setFont(fnt)
                p.drawText(QRect(1, y + 1, _PREV_W - 2, h - 2),
                           Qt.AlignCenter | Qt.TextWordWrap, name)

            idx += rows

        # Row grid lines
        p.setPen(QPen(QColor(55, 55, 55), 1))
        for row in range(_OLED_ROWS + 1):
            y = row * _PREV_ROW_H
            p.drawLine(0, y, _PREV_W, y)

        # Outer border
        p.setPen(QPen(QColor(120, 120, 120), 1))
        p.drawRect(0, 0, _PREV_W - 1, _PREV_H - 1)

        p.end()


# ── Screen panel (block builder + live preview) ───────────────────────────────

class _ScreenPanel(QWidget):
    """Widget-block builder for one OLED screen with live preview."""

    def __init__(self, screen_label, on_apply):
        super().__init__()
        self._on_apply_cb = on_apply
        self._block_combos = []   # list of QComboBox, one per block

        root = QHBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(12)

        # ── Left: block list ──────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(6)

        hdr = QLabel("<b>{} OLED — Widget Stack</b>".format(screen_label))
        left.addWidget(hdr)

        note = QLabel(
            "Stack widgets top→bottom. Multi-row widgets (e.g. Calcifer = full screen)\n"
            "consume multiple rows. The preview updates live on the right."
        )
        note.setWordWrap(True)
        left.addWidget(note)

        # Scrollable block list
        self._block_container = QWidget()
        self._block_layout = QVBoxLayout(self._block_container)
        self._block_layout.setContentsMargins(0, 0, 0, 0)
        self._block_layout.setSpacing(4)
        self._block_layout.addStretch()

        block_scroll = QScrollArea()
        block_scroll.setFrameShape(QFrame.StyledPanel)
        block_scroll.setWidgetResizable(True)
        block_scroll.setWidget(self._block_container)
        block_scroll.setMinimumHeight(200)
        left.addWidget(block_scroll, 1)

        # Row counter + add button
        ctrl_row = QHBoxLayout()
        self._row_counter = QLabel("Total: 0 / {} rows".format(_OLED_ROWS))
        ctrl_row.addWidget(self._row_counter)
        ctrl_row.addStretch()
        self._btn_add = QPushButton("+ Add Widget")
        self._btn_add.clicked.connect(self._add_block)
        ctrl_row.addWidget(self._btn_add)
        left.addLayout(ctrl_row)

        # Apply button
        apply_row = QHBoxLayout()
        apply_row.addStretch()
        btn_apply = QPushButton("Apply to Keyboard")
        btn_apply.setMinimumWidth(180)
        btn_apply.clicked.connect(self._on_apply)
        apply_row.addWidget(btn_apply)
        left.addLayout(apply_row)

        root.addLayout(left, 1)

        # ── Right: OLED preview ───────────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(4)
        right.addWidget(QLabel("<b>Preview</b>"))
        self._preview = OledPreview()
        right.addWidget(self._preview)
        right.addStretch()
        root.addLayout(right)

    # ── Block management ──────────────────────────────────────────────────────

    def _make_block_row(self, wid=0x00):
        """Create one block row widget: [combo | rows label | ▲ | ▼ | ✕]"""
        row_w = QWidget()
        hl = QHBoxLayout(row_w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)

        combo = QComboBox()
        for w, name, rows, _ in WIDGETS:
            combo.addItem("{:12s}  ({} row{})".format(name, rows, "s" if rows > 1 else " "),
                          userData=w)
        # Select current wid
        for i in range(combo.count()):
            if combo.itemData(i) == wid:
                combo.setCurrentIndex(i)
                break
        combo.currentIndexChanged.connect(self._refresh)

        rows_lbl = QLabel()
        rows_lbl.setFixedWidth(50)
        rows_lbl.setAlignment(Qt.AlignCenter)

        btn_up   = QToolButton(); btn_up.setText("▲")
        btn_down = QToolButton(); btn_down.setText("▼")
        btn_del  = QToolButton(); btn_del.setText("✕")
        btn_del.setStyleSheet("color: #c44;")

        btn_up.clicked.connect(  lambda: self._move_block(row_w, -1))
        btn_down.clicked.connect(lambda: self._move_block(row_w, +1))
        btn_del.clicked.connect( lambda: self._remove_block(row_w))

        hl.addWidget(combo, 1)
        hl.addWidget(rows_lbl)
        hl.addWidget(btn_up)
        hl.addWidget(btn_down)
        hl.addWidget(btn_del)

        row_w._combo     = combo
        row_w._rows_lbl  = rows_lbl
        self._block_combos.append(combo)
        return row_w

    def _add_block(self, wid=0x00):
        if _total_rows(self._get_block_wids()) >= _OLED_ROWS:
            return
        row_w = self._make_block_row(wid)
        # Insert before the trailing stretch (last item)
        layout = self._block_layout
        layout.insertWidget(layout.count() - 1, row_w)
        self._refresh()

    def _remove_block(self, row_w):
        self._block_combos.remove(row_w._combo)
        self._block_layout.removeWidget(row_w)
        row_w.deleteLater()
        self._refresh()

    def _move_block(self, row_w, direction):
        layout = self._block_layout
        idx = layout.indexOf(row_w)
        target = idx + direction
        # Valid range: 0 to count-2 (last is stretch)
        if target < 0 or target >= layout.count() - 1:
            return
        layout.removeWidget(row_w)
        layout.insertWidget(target, row_w)
        # Rebuild combo list in visual order
        self._rebuild_combo_list()
        self._refresh()

    def _rebuild_combo_list(self):
        """Sync self._block_combos to the current visual order of block rows."""
        layout = self._block_layout
        self._block_combos.clear()
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if hasattr(w, '_combo'):
                    self._block_combos.append(w._combo)

    def _get_block_wids(self):
        return [c.currentData() for c in self._block_combos]

    def _refresh(self):
        """Update row counter, Add button state, and preview."""
        wids  = self._get_block_wids()
        total = _total_rows(wids)
        remaining = _OLED_ROWS - total
        self._row_counter.setText(
            "Total: {} / {} rows  ({} free)".format(total, _OLED_ROWS, max(0, remaining))
        )
        self._btn_add.setEnabled(remaining > 0)

        # Update rows label on each block row
        layout = self._block_layout
        combo_iter = iter(self._block_combos)
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget() and hasattr(item.widget(), '_rows_lbl'):
                try:
                    combo = next(combo_iter)
                    rows = _WID_ROWS.get(combo.currentData(), 1)
                    item.widget()._rows_lbl.setText("{} row{}".format(rows, "s" if rows > 1 else ""))
                except StopIteration:
                    break

        self._preview.update_slots(_slots_from_blocks(wids))

    # ── Load / get ────────────────────────────────────────────────────────────

    def load_slots(self, slots):
        """Populate from a 16-element slot array."""
        # Remove all existing block rows from layout (without triggering _refresh per item)
        layout = self._block_layout
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item and item.widget() and hasattr(item.widget(), '_combo'):
                w = item.widget()
                layout.removeWidget(w)
                w.deleteLater()
        self._block_combos.clear()

        # Add blocks for each widget found in slots
        for wid in _blocks_from_slots(slots):
            self._add_block(wid)
        self._refresh()

    def get_slots(self):
        return _slots_from_blocks(self._get_block_wids())

    def _on_apply(self):
        self._on_apply_cb(self.get_slots())


# ── Main configurator ─────────────────────────────────────────────────────────

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
    content = QWidget()
    content.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
    content.setLayout(inner_layout)
    outer = QVBoxLayout()
    outer.addWidget(content)
    outer.setAlignment(content, Qt.AlignHCenter)
    return _make_scrollable(outer)


def _make_char_field(placeholder=""):
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
            "Changes take effect immediately after clicking Apply."
        )
        note.setWordWrap(True)
        inner.addWidget(note)

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

        # ── Screen A tab (master OLED) ────────────────────────────────────────
        self._screen_a = _ScreenPanel("Master (Left)", self._on_apply_screen_a)
        sa_scroll = QScrollArea()
        sa_scroll.setFrameShape(QFrame.NoFrame)
        sa_scroll.setWidgetResizable(True)
        sa_scroll.setWidget(self._screen_a)
        tabs_widget.addTab(sa_scroll, "Screen A (Master)")

        # ── Screen B tab (slave OLED) ─────────────────────────────────────────
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
        self._screen_a.load_slots(cfg.get('screen_a', [0] * _OLED_ROWS))
        self._screen_b.load_slots(cfg.get('screen_b', [0] * _OLED_ROWS))

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
