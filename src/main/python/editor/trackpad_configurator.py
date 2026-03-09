# SPDX-License-Identifier: GPL-2.0-or-later
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QGroupBox, QLabel, QSlider, QCheckBox, QPushButton,
                             QComboBox, QScrollArea, QFrame, QSizePolicy, QTabWidget)
from PyQt5.QtCore import Qt

from editor.basic_editor import BasicEditor
from vial_device import VialKeyboard


# QMK modifier bit positions (matches get_mods() bitmask)
_MOD_NAMES = ["LCtrl", "LShift", "LAlt", "LGui", "RCtrl", "RShift", "RAlt", "RGui"]

# Trackpad layer behaviour choices (index matches combo selection)
_LAYER_BEHAVIOURS = [
    "Cursor (pointer moves)",
    "Scroll (2-finger drag)",
    "2-Finger Swipe (back / forward)",
    "3-Finger Swipe (action centre / desktop)",
]

# Number of configurable layers shown (layers 1-9; layer 0 is always cursor)
_NUM_LAYERS = 9

_PATCH = "Patch: D83E"


def _make_scrollable(inner_layout):
    """Wrap a QVBoxLayout in a transparent QScrollArea."""
    w = QWidget()
    w.setLayout(inner_layout)
    w.setObjectName("tpInner")
    scroll = QScrollArea()
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setStyleSheet("QScrollArea { background-color: transparent; }")
    w.setStyleSheet("#tpInner { background-color: transparent; }")
    scroll.setWidgetResizable(True)
    scroll.setWidget(w)
    return scroll


def _centered_scroll(inner_layout):
    """Mirror the Key Overrides pattern: constrain content to its natural width
    and centre it horizontally inside a scroll area.  This gives visible
    left/right (and top/bottom) margins like every other Vial GUI tab."""
    content = QWidget()
    content.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
    content.setLayout(inner_layout)

    outer = QVBoxLayout()
    outer.addWidget(content)
    outer.setAlignment(content, Qt.AlignHCenter)

    return _make_scrollable(outer)


class TrackpadConfigurator(BasicEditor):

    def __init__(self):
        super().__init__()
        self.keyboard = None
        self._loading = False  # suppress spurious change signals while populating

        # Top-level tab widget — mirrors the pattern used by Macros, Key Overrides,
        # QMK Settings, etc.  The QTabWidget's styled content-area border provides
        # the visual frame; _centered_scroll() provides the horizontal centering.
        tabs_widget = QTabWidget()

        # ── Settings tab ─────────────────────────────────────────────────────
        inner_s = QVBoxLayout()
        inner_s.setContentsMargins(4, 4, 4, 4)
        inner_s.setSpacing(8)

        # Info banner
        info = QLabel(
            "Cursor, scroll, and behaviour settings apply in macOS / Linux mouse-fallback mode.\n"
            "On Windows, Precision Touchpad (PTP) is used and gestures are handled by the OS."
        )
        info.setWordWrap(True)
        inner_s.addWidget(info)

        # Pointer
        pointer_group = QGroupBox("Pointer")
        pointer_layout = QVBoxLayout()
        pointer_layout.setSpacing(4)
        self.cursor_slider, cursor_row = self._make_slider_row("Cursor DPI:", 1, 6)
        self.scroll_slider, scroll_row = self._make_slider_row("Scroll Speed:", 1, 8)
        pointer_layout.addWidget(cursor_row)
        pointer_layout.addWidget(scroll_row)
        pointer_group.setLayout(pointer_layout)
        inner_s.addWidget(pointer_group)

        # Scroll
        self.chk_invert_v = QCheckBox("Invert vertical scroll (natural scrolling)")
        self.chk_invert_h = QCheckBox("Invert horizontal scroll")
        scroll_group = QGroupBox("Scroll")
        scroll_layout = QVBoxLayout()
        scroll_layout.addWidget(self.chk_invert_v)
        scroll_layout.addWidget(self.chk_invert_h)
        scroll_group.setLayout(scroll_layout)
        inner_s.addWidget(scroll_group)

        # Behaviour
        self.chk_zoom = QCheckBox("Enable zoom gesture (pinch / scroll-wheel buttons 6 & 7)")
        self.chk_tap = QCheckBox("Tap-to-click")
        self.chk_enabled = QCheckBox("Trackpad enabled")
        behaviour_group = QGroupBox("Behaviour")
        behaviour_layout = QVBoxLayout()
        behaviour_layout.addWidget(self.chk_zoom)
        behaviour_layout.addWidget(self.chk_tap)
        behaviour_layout.addWidget(self.chk_enabled)
        behaviour_group.setLayout(behaviour_layout)
        inner_s.addWidget(behaviour_group)

        # Sniper Mode
        self.sniper_slider, sniper_row = self._make_slider_row("Sniper DPI:", 1, 6)
        self.mod_checks = []
        mod_grid = QGridLayout()
        mod_grid.setSpacing(4)
        for i, name in enumerate(_MOD_NAMES):
            chk = QCheckBox(name)
            self.mod_checks.append(chk)
            mod_grid.addWidget(chk, i // 4, i % 4)
        mod_note = QLabel(
            "Hold the chosen modifier(s) to activate Sniper Mode (precise cursor).\n"
            "You can also set the trigger live: hold the modifier and press the SNIPER_SET_MODS key."
        )
        mod_note.setWordWrap(True)
        sniper_group = QGroupBox("Sniper Mode")
        sniper_layout = QVBoxLayout()
        sniper_layout.setSpacing(6)
        sniper_layout.addWidget(sniper_row)
        sniper_layout.addWidget(QLabel("Trigger modifier(s):"))
        sniper_layout.addLayout(mod_grid)
        sniper_layout.addWidget(mod_note)
        sniper_group.setLayout(sniper_layout)
        inner_s.addWidget(sniper_group)

        # Apply Settings button
        btn_settings_row = QHBoxLayout()
        btn_settings_row.addStretch()
        self.btn_apply_settings = QPushButton("Apply Settings to Keyboard")
        self.btn_apply_settings.setMinimumWidth(220)
        self.btn_apply_settings.clicked.connect(self._on_apply_settings)
        btn_settings_row.addWidget(self.btn_apply_settings)
        inner_s.addLayout(btn_settings_row)

        settings_page = QWidget()
        settings_page_layout = QVBoxLayout(settings_page)
        settings_page_layout.setContentsMargins(0, 0, 0, 0)
        settings_page_layout.addWidget(_centered_scroll(inner_s))
        tabs_widget.addTab(settings_page, "Settings")

        # ── Layer Behaviour tab ───────────────────────────────────────────────
        inner_l = QVBoxLayout()
        inner_l.setContentsMargins(4, 4, 4, 4)
        inner_l.setSpacing(8)

        layer_desc = QLabel(
            "Layer 0 is always Cursor (pointer movement). "
            "For each additional layer, choose the trackpad behaviour when that layer is active:\n"
            "  \u2022  Cursor \u2014 1-finger moves the pointer\n"
            "  \u2022  Scroll \u2014 2-finger drag scrolls the page\n"
            "  \u2022  2-Finger Swipe \u2014 swipe left/right for browser back/forward\n"
            "  \u2022  3-Finger Swipe \u2014 swipe for action centre, show desktop, etc."
        )
        layer_desc.setWordWrap(True)

        self.layer_combos = []
        layer_grid = QGridLayout()
        layer_grid.setHorizontalSpacing(16)
        layer_grid.setVerticalSpacing(4)
        for i in range(_NUM_LAYERS):
            lbl = QLabel("Layer {}:".format(i + 1))
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            combo = QComboBox()
            for b in _LAYER_BEHAVIOURS:
                combo.addItem(b)
            self.layer_combos.append(combo)
            layer_grid.addWidget(lbl, i % 5, (i // 5) * 2)
            layer_grid.addWidget(combo, i % 5, (i // 5) * 2 + 1)

        layer_group = QGroupBox("Trackpad Layer Behaviour")
        layer_layout = QVBoxLayout()
        layer_layout.setSpacing(8)
        layer_layout.addWidget(layer_desc)
        layer_layout.addLayout(layer_grid)
        layer_group.setLayout(layer_layout)
        inner_l.addWidget(layer_group)

        btn_layers_row = QHBoxLayout()
        btn_layers_row.addStretch()
        self.btn_apply_layers = QPushButton("Apply Layer Behaviour to Keyboard")
        self.btn_apply_layers.setMinimumWidth(240)
        self.btn_apply_layers.clicked.connect(self._on_apply_layers)
        btn_layers_row.addWidget(self.btn_apply_layers)
        inner_l.addLayout(btn_layers_row)

        layers_page = QWidget()
        layers_page_layout = QVBoxLayout(layers_page)
        layers_page_layout.setContentsMargins(0, 0, 0, 0)
        layers_page_layout.addWidget(_centered_scroll(inner_l))
        tabs_widget.addTab(layers_page, "Layer Behaviour")

        self.addWidget(tabs_widget)

        # Version label — always visible below the tab widget so you can confirm
        # which build is running without re-entering the tab content.
        version_lbl = QLabel(_PATCH)
        version_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.addWidget(version_lbl)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_slider_row(self, label_text, min_val, max_val):
        """Return (QSlider, row_QWidget).  The slider carries ._value_lbl and ._max."""
        row = QWidget()
        row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(label_text)
        lbl.setFixedWidth(110)

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval(1)

        value_lbl = QLabel("Level {}/{}".format(min_val, max_val))
        value_lbl.setFixedWidth(70)

        slider.valueChanged.connect(
            lambda v, vl=value_lbl, mx=max_val: vl.setText("Level {}/{}".format(v, mx))
        )

        layout.addWidget(lbl)
        layout.addWidget(slider)
        layout.addWidget(value_lbl)

        slider._value_lbl = value_lbl
        slider._max = max_val
        return slider, row

    @staticmethod
    def _set_slider(slider, value):
        slider.setValue(value)
        slider._value_lbl.setText("Level {}/{}".format(value, slider._max))

    # ── Data helpers ──────────────────────────────────────────────────────────

    def _load_settings(self):
        s = self.keyboard.trackpad_settings
        self._set_slider(self.cursor_slider, s.get('cursor_dpi', 3))
        self._set_slider(self.scroll_slider, s.get('scroll_speed', 4))
        self._set_slider(self.sniper_slider, s.get('sniper_scale', 1))
        self.chk_invert_v.setChecked(s.get('scroll_invert_v', False))
        self.chk_invert_h.setChecked(s.get('scroll_invert_h', False))
        self.chk_zoom.setChecked(s.get('zoom_enabled', True))
        self.chk_tap.setChecked(s.get('taps_as_clicks', False))
        self.chk_enabled.setChecked(s.get('trackpad_enabled', True))
        mask = s.get('sniper_modifier_mask', 0)
        for i, chk in enumerate(self.mod_checks):
            chk.setChecked(bool(mask & (1 << i)))

    def _load_layers(self):
        layers = self.keyboard.trackpad_layers
        scroll_mask = layers.get('scroll', 0)
        swipe2_mask = layers.get('swipe2', 0)
        swipe3_mask = layers.get('swipe3', 0)
        for i, combo in enumerate(self.layer_combos):
            layer_num = i + 1  # layers are 1-indexed
            bit = 1 << layer_num
            if scroll_mask & bit:
                combo.setCurrentIndex(1)
            elif swipe2_mask & bit:
                combo.setCurrentIndex(2)
            elif swipe3_mask & bit:
                combo.setCurrentIndex(3)
            else:
                combo.setCurrentIndex(0)

    def _collect_settings(self):
        mask = 0
        for i, chk in enumerate(self.mod_checks):
            if chk.isChecked():
                mask |= (1 << i)
        return {
            'cursor_dpi':           self.cursor_slider.value(),
            'scroll_speed':         self.scroll_slider.value(),
            'scroll_invert_v':      self.chk_invert_v.isChecked(),
            'scroll_invert_h':      self.chk_invert_h.isChecked(),
            'zoom_enabled':         self.chk_zoom.isChecked(),
            'taps_as_clicks':       self.chk_tap.isChecked(),
            'trackpad_enabled':     self.chk_enabled.isChecked(),
            'sniper_scale':         self.sniper_slider.value(),
            'sniper_modifier_mask': mask,
        }

    def _collect_layers(self):
        scroll_mask = swipe2_mask = swipe3_mask = 0
        for i, combo in enumerate(self.layer_combos):
            layer_num = i + 1
            bit = 1 << layer_num
            idx = combo.currentIndex()
            if idx == 1:
                scroll_mask |= bit
            elif idx == 2:
                swipe2_mask |= bit
            elif idx == 3:
                swipe3_mask |= bit
        return {'scroll': scroll_mask, 'swipe2': swipe2_mask, 'swipe3': swipe3_mask}

    # ── Button handlers ───────────────────────────────────────────────────────

    def _on_apply_settings(self):
        if self.keyboard:
            self.keyboard.set_trackpad_settings(self._collect_settings())

    def _on_apply_layers(self):
        if self.keyboard:
            self.keyboard.set_trackpad_layers(self._collect_layers())

    # ── BasicEditor interface ──────────────────────────────────────────────────

    def valid(self):
        return (isinstance(self.device, VialKeyboard)
                and self.device.keyboard.trackpad_supported)

    def rebuild(self, device):
        super().rebuild(device)
        if not self.valid():
            self.keyboard = None
            return
        self.keyboard = device.keyboard
        self._loading = True
        try:
            self._load_settings()
            self._load_layers()
        finally:
            self._loading = False
