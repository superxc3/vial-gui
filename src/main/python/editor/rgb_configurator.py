# SPDX-License-Identifier: GPL-2.0-or-later
import json
import os

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QObject, Qt, QStandardPaths
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QSizePolicy, QGridLayout, QLabel, \
    QSlider, QComboBox, QColorDialog, QCheckBox, QScrollArea, QApplication, QButtonGroup, QSpinBox

from editor.basic_editor import BasicEditor
from widgets.clickable_label import ClickableLabel
from widgets.keyboard_widget import KeyboardWidget
from util import tr
from vial_device import VialKeyboard


def _colors_save_path(keyboard_id):
    """Return path for storing per-key color data for a keyboard."""
    data_dir = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "customise_colors_{:016x}.json".format(keyboard_id))

VIALRGB_DIRECT_IDX = 45


class QmkRgblightEffect:

    def __init__(self, idx, name, color_picker):
        self.idx = idx
        self.name = name
        self.color_picker = color_picker


QMK_RGBLIGHT_EFFECTS = [
    QmkRgblightEffect(0, "All Off", False),
    QmkRgblightEffect(1, "Solid Color", True),
    QmkRgblightEffect(2, "Breathing 1", True),
    QmkRgblightEffect(3, "Breathing 2", True),
    QmkRgblightEffect(4, "Breathing 3", True),
    QmkRgblightEffect(5, "Breathing 4", True),
    QmkRgblightEffect(6, "Rainbow Mood 1", False),
    QmkRgblightEffect(7, "Rainbow Mood 2", False),
    QmkRgblightEffect(8, "Rainbow Mood 3", False),
    QmkRgblightEffect(9, "Rainbow Swirl 1", False),
    QmkRgblightEffect(10, "Rainbow Swirl 2", False),
    QmkRgblightEffect(11, "Rainbow Swirl 3", False),
    QmkRgblightEffect(12, "Rainbow Swirl 4", False),
    QmkRgblightEffect(13, "Rainbow Swirl 5", False),
    QmkRgblightEffect(14, "Rainbow Swirl 6", False),
    QmkRgblightEffect(15, "Snake 1", True),
    QmkRgblightEffect(16, "Snake 2", True),
    QmkRgblightEffect(17, "Snake 3", True),
    QmkRgblightEffect(18, "Snake 4", True),
    QmkRgblightEffect(19, "Snake 5", True),
    QmkRgblightEffect(20, "Snake 6", True),
    QmkRgblightEffect(21, "Knight 1", True),
    QmkRgblightEffect(22, "Knight 2", True),
    QmkRgblightEffect(23, "Knight 3", True),
    QmkRgblightEffect(24, "Christmas", True),
    QmkRgblightEffect(25, "Gradient 1", True),
    QmkRgblightEffect(26, "Gradient 2", True),
    QmkRgblightEffect(27, "Gradient 3", True),
    QmkRgblightEffect(28, "Gradient 4", True),
    QmkRgblightEffect(29, "Gradient 5", True),
    QmkRgblightEffect(30, "Gradient 6", True),
    QmkRgblightEffect(31, "Gradient 7", True),
    QmkRgblightEffect(32, "Gradient 8", True),
    QmkRgblightEffect(33, "Gradient 9", True),
    QmkRgblightEffect(34, "Gradient 10", True),
    QmkRgblightEffect(35, "RGB Test", True),
    QmkRgblightEffect(36, "Alternating", True),
]


class VialRGBEffect:

    def __init__(self, idx, name):
        self.idx = idx
        self.name = name


VIALRGB_EFFECTS = [
    VialRGBEffect(0, "Disable"),
    VialRGBEffect(1, "Direct Control"),
    VialRGBEffect(2, "Solid Color"),
    VialRGBEffect(3, "Alphas Mods"),
    VialRGBEffect(4, "Gradient Up Down"),
    VialRGBEffect(5, "Gradient Left Right"),
    VialRGBEffect(6, "Breathing"),
    VialRGBEffect(7, "Band Sat"),
    VialRGBEffect(8, "Band Val"),
    VialRGBEffect(9, "Band Pinwheel Sat"),
    VialRGBEffect(10, "Band Pinwheel Val"),
    VialRGBEffect(11, "Band Spiral Sat"),
    VialRGBEffect(12, "Band Spiral Val"),
    VialRGBEffect(13, "Cycle All"),
    VialRGBEffect(14, "Cycle Left Right"),
    VialRGBEffect(15, "Cycle Up Down"),
    VialRGBEffect(16, "Rainbow Moving Chevron"),
    VialRGBEffect(17, "Cycle Out In"),
    VialRGBEffect(18, "Cycle Out In Dual"),
    VialRGBEffect(19, "Cycle Pinwheel"),
    VialRGBEffect(20, "Cycle Spiral"),
    VialRGBEffect(21, "Dual Beacon"),
    VialRGBEffect(22, "Rainbow Beacon"),
    VialRGBEffect(23, "Rainbow Pinwheels"),
    VialRGBEffect(24, "Raindrops"),
    VialRGBEffect(25, "Jellybean Raindrops"),
    VialRGBEffect(26, "Hue Breathing"),
    VialRGBEffect(27, "Hue Pendulum"),
    VialRGBEffect(28, "Hue Wave"),
    VialRGBEffect(29, "Typing Heatmap"),
    VialRGBEffect(30, "Digital Rain"),
    VialRGBEffect(31, "Solid Reactive Simple"),
    VialRGBEffect(32, "Solid Reactive"),
    VialRGBEffect(33, "Solid Reactive Wide"),
    VialRGBEffect(34, "Solid Reactive Multiwide"),
    VialRGBEffect(35, "Solid Reactive Cross"),
    VialRGBEffect(36, "Solid Reactive Multicross"),
    VialRGBEffect(37, "Solid Reactive Nexus"),
    VialRGBEffect(38, "Solid Reactive Multinexus"),
    VialRGBEffect(39, "Splash"),
    VialRGBEffect(40, "Multisplash"),
    VialRGBEffect(41, "Solid Splash"),
    VialRGBEffect(42, "Solid Multisplash"),
    VialRGBEffect(43, "Pixel Rain"),
    VialRGBEffect(44, "Pixel Fractal"),
    VialRGBEffect(45, "Customise"),
]


class BasicHandler(QObject):

    update = pyqtSignal()

    def __init__(self, container):
        super().__init__()
        self.device = self.keyboard = None
        self.widgets = []

    def set_device(self, device):
        self.device = device
        if self.valid():
            self.keyboard = self.device.keyboard
            self.show()
        else:
            self.hide()

    def show(self):
        for w in self.widgets:
            w.show()

    def hide(self):
        for w in self.widgets:
            w.hide()

    def block_signals(self):
        for w in self.widgets:
            w.blockSignals(True)

    def unblock_signals(self):
        for w in self.widgets:
            w.blockSignals(False)

    def update_from_keyboard(self):
        raise NotImplementedError

    def valid(self):
        raise NotImplementedError


class QmkRgblightHandler(BasicHandler):

    def __init__(self, container):
        super().__init__(container)

        row = container.rowCount()

        self.lbl_underglow_effect = QLabel(tr("RGBConfigurator", "Underglow Effect"))
        container.addWidget(self.lbl_underglow_effect, row, 0)
        self.underglow_effect = QComboBox()
        for ef in QMK_RGBLIGHT_EFFECTS:
            self.underglow_effect.addItem(ef.name)
        container.addWidget(self.underglow_effect, row, 1)

        self.lbl_underglow_brightness = QLabel(tr("RGBConfigurator", "Underglow Brightness"))
        container.addWidget(self.lbl_underglow_brightness, row + 1, 0)
        self.underglow_brightness = QSlider(QtCore.Qt.Horizontal)
        self.underglow_brightness.setMinimum(0)
        self.underglow_brightness.setMaximum(255)
        self.underglow_brightness.valueChanged.connect(self.on_underglow_brightness_changed)
        container.addWidget(self.underglow_brightness, row + 1, 1)

        self.lbl_underglow_color = QLabel(tr("RGBConfigurator", "Underglow Color"))
        container.addWidget(self.lbl_underglow_color, row + 2, 0)
        self.underglow_color = ClickableLabel(" ")
        self.underglow_color.clicked.connect(self.on_underglow_color)
        container.addWidget(self.underglow_color, row + 2, 1)

        self.underglow_effect.currentIndexChanged.connect(self.on_underglow_effect_changed)

        self.widgets = [self.lbl_underglow_effect, self.underglow_effect, self.lbl_underglow_brightness,
                        self.underglow_brightness, self.lbl_underglow_color, self.underglow_color]

    def update_from_keyboard(self):
        if not self.valid():
            return

        self.underglow_brightness.setValue(self.device.keyboard.underglow_brightness)
        self.underglow_effect.setCurrentIndex(self.device.keyboard.underglow_effect)
        self.underglow_color.setStyleSheet("QWidget { background-color: %s}" % self.current_color().name())

    def valid(self):
        return isinstance(self.device, VialKeyboard) and self.device.keyboard.lighting_qmk_rgblight

    def on_underglow_brightness_changed(self, value):
        self.device.keyboard.set_qmk_rgblight_brightness(value)
        self.update.emit()

    def on_underglow_effect_changed(self, index):
        self.lbl_underglow_color.setVisible(QMK_RGBLIGHT_EFFECTS[index].color_picker)
        self.underglow_color.setVisible(QMK_RGBLIGHT_EFFECTS[index].color_picker)

        self.device.keyboard.set_qmk_rgblight_effect(index)

    def on_underglow_color(self):
        self.dlg_color = QColorDialog()
        self.dlg_color.setModal(True)
        self.dlg_color.finished.connect(self.on_underglow_color_finished)
        self.dlg_color.setCurrentColor(self.current_color())
        self.dlg_color.show()

    def on_underglow_color_finished(self):
        color = self.dlg_color.selectedColor()
        if not color.isValid():
            return
        self.underglow_color.setStyleSheet("QWidget { background-color: %s}" % color.name())
        h, s, v, a = color.getHsvF()
        if h < 0:
            h = 0
        self.device.keyboard.set_qmk_rgblight_color(int(255 * h), int(255 * s), int(255 * v))
        self.update.emit()

    def current_color(self):
        return QColor.fromHsvF(self.device.keyboard.underglow_color[0] / 255.0,
                               self.device.keyboard.underglow_color[1] / 255.0,
                               self.device.keyboard.underglow_brightness / 255.0)


class QmkBacklightHandler(BasicHandler):

    def __init__(self, container):
        super().__init__(container)

        row = container.rowCount()

        self.lbl_backlight_brightness = QLabel(tr("RGBConfigurator", "Backlight Brightness"))
        container.addWidget(self.lbl_backlight_brightness, row, 0)
        self.backlight_brightness = QSlider(QtCore.Qt.Horizontal)
        self.backlight_brightness.setMinimum(0)
        self.backlight_brightness.setMaximum(255)
        self.backlight_brightness.valueChanged.connect(self.on_backlight_brightness_changed)
        container.addWidget(self.backlight_brightness, row, 1)

        self.lbl_backlight_breathing = QLabel(tr("RGBConfigurator", "Backlight Breathing"))
        container.addWidget(self.lbl_backlight_breathing, row + 1, 0)
        self.backlight_breathing = QCheckBox()
        self.backlight_breathing.stateChanged.connect(self.on_backlight_breathing_changed)
        container.addWidget(self.backlight_breathing, row + 1, 1)

        self.widgets = [self.lbl_backlight_brightness, self.backlight_brightness, self.lbl_backlight_breathing,
                        self.backlight_breathing]

    def update_from_keyboard(self):
        if not self.valid():
            return

        self.backlight_brightness.setValue(self.device.keyboard.backlight_brightness)
        self.backlight_breathing.setChecked(self.device.keyboard.backlight_effect == 1)

    def valid(self):
        return isinstance(self.device, VialKeyboard) and self.device.keyboard.lighting_qmk_backlight

    def on_backlight_brightness_changed(self, value):
        self.device.keyboard.set_qmk_backlight_brightness(value)

    def on_backlight_breathing_changed(self, checked):
        self.device.keyboard.set_qmk_backlight_effect(int(checked))


class VialRGBHandler(BasicHandler):

    mode_changed = pyqtSignal(int)

    def __init__(self, container):
        super().__init__(container)

        row = container.rowCount()

        self.lbl_rgb_effect = QLabel(tr("RGBConfigurator", "RGB Effect"))
        container.addWidget(self.lbl_rgb_effect, row, 0)
        self.rgb_effect = QComboBox()
        self.rgb_effect.addItem("0")
        self.rgb_effect.addItem("1")
        self.rgb_effect.addItem("2")
        self.rgb_effect.addItem("3")
        self.rgb_effect.currentIndexChanged.connect(self.on_rgb_effect_changed)
        container.addWidget(self.rgb_effect, row, 1)

        self.lbl_rgb_color = QLabel(tr("RGBConfigurator", "RGB Color"))
        container.addWidget(self.lbl_rgb_color, row + 1, 0)
        self.rgb_color = ClickableLabel(" ")
        self.rgb_color.clicked.connect(self.on_rgb_color)
        container.addWidget(self.rgb_color, row + 1, 1)

        self.lbl_rgb_brightness = QLabel(tr("RGBConfigurator", "RGB Brightness"))
        container.addWidget(self.lbl_rgb_brightness, row + 2, 0)
        self.rgb_brightness = QSlider(QtCore.Qt.Horizontal)
        self.rgb_brightness.setMinimum(0)
        self.rgb_brightness.setMaximum(255)
        self.rgb_brightness.valueChanged.connect(self.on_rgb_brightness_changed)
        container.addWidget(self.rgb_brightness, row + 2, 1)

        self.lbl_rgb_speed = QLabel(tr("RGBConfigurator", "RGB Speed"))
        container.addWidget(self.lbl_rgb_speed, row + 3, 0)
        self.rgb_speed = QSlider(QtCore.Qt.Horizontal)
        self.rgb_speed.setMinimum(0)
        self.rgb_speed.setMaximum(255)
        self.rgb_speed.valueChanged.connect(self.on_rgb_speed_changed)
        container.addWidget(self.rgb_speed, row + 3, 1)

        self.lbl_rgb_sleep = QLabel(tr("RGBConfigurator", "Sleep Time"))
        container.addWidget(self.lbl_rgb_sleep, row + 4, 0)
        self.rgb_sleep = QSpinBox()
        self.rgb_sleep.setMinimum(1)
        self.rgb_sleep.setMaximum(30)
        self.rgb_sleep.setSuffix(tr("RGBConfigurator", " min"))
        self.rgb_sleep.setToolTip(tr("RGBConfigurator",
            "Minutes of inactivity before the OLED and RGB sleep (shared for both)."))
        self.rgb_sleep.valueChanged.connect(self.on_rgb_sleep_changed)
        container.addWidget(self.rgb_sleep, row + 4, 1)

        self.widgets = [self.lbl_rgb_effect, self.rgb_effect, self.lbl_rgb_brightness, self.rgb_brightness,
                        self.lbl_rgb_color, self.rgb_color, self.lbl_rgb_speed, self.rgb_speed,
                        self.lbl_rgb_sleep, self.rgb_sleep]

        self.effects = []

    def on_rgb_brightness_changed(self, value):
        self.keyboard.set_vialrgb_brightness(value)

    def on_rgb_speed_changed(self, value):
        self.keyboard.set_vialrgb_speed(value)

    def on_rgb_sleep_changed(self, value):
        self.keyboard.set_power_settings(value)

    def on_rgb_effect_changed(self, index):
        vialrgb_id = self.effects[index].idx
        self.keyboard.set_vialrgb_mode(vialrgb_id)
        self.mode_changed.emit(vialrgb_id)

    def on_rgb_color(self):
        self.dlg_color = QColorDialog()
        self.dlg_color.setModal(True)
        self.dlg_color.finished.connect(self.on_rgb_color_finished)
        self.dlg_color.setCurrentColor(self.current_color())
        self.dlg_color.show()

    def on_rgb_color_finished(self):
        color = self.dlg_color.selectedColor()
        if not color.isValid():
            return
        self.rgb_color.setStyleSheet("QWidget { background-color: %s}" % color.name())
        h, s, v, a = color.getHsvF()
        if h < 0:
            h = 0
        self.keyboard.set_vialrgb_color(int(255 * h), int(255 * s), self.keyboard.rgb_hsv[2])
        self.update.emit()

    def current_color(self):
        return QColor.fromHsvF(self.keyboard.rgb_hsv[0] / 255.0,
                               self.keyboard.rgb_hsv[1] / 255.0,
                               1.0)

    def rebuild_effects(self):
        self.effects = []
        for effect in VIALRGB_EFFECTS:
            if effect.idx in self.keyboard.rgb_supported_effects:
                self.effects.append(effect)

        self.rgb_effect.clear()
        for effect in self.effects:
            self.rgb_effect.addItem(effect.name)

    def update_from_keyboard(self):
        if not self.valid():
            return

        self.rebuild_effects()
        for x, effect in enumerate(self.effects):
            if effect.idx == self.keyboard.rgb_mode:
                self.rgb_effect.setCurrentIndex(x)
                break
        self.rgb_brightness.setMaximum(self.keyboard.rgb_maximum_brightness)
        self.rgb_brightness.setValue(self.keyboard.rgb_hsv[2])
        self.rgb_speed.setValue(self.keyboard.rgb_speed)
        self.rgb_sleep.setValue(getattr(self.keyboard, "sleep_timeout_min", 1))
        self.rgb_color.setStyleSheet("QWidget { background-color: %s}" % self.current_color().name())
        self.mode_changed.emit(self.keyboard.rgb_mode)

    def valid(self):
        return isinstance(self.device, VialKeyboard) and self.device.keyboard.lighting_vialrgb


class PerKeyRGBWidget(QWidget):
    """Shows the keyboard layout so individual keys can be assigned colors in Customise mode.

    Click to select a key. Ctrl+click to add/remove from selection.
    'Set Color' applies to all selected keys; 'Reset Selected' turns them off.
    """

    def __init__(self, layout_editor):
        super().__init__()
        self.keyboard = None
        self._selected_positions = set()  # set of (row, col) tuples with a valid LED

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        self.setLayout(outer)

        lbl = QLabel(tr("RGBConfigurator",
            "Click to select a key. Windows: Ctrl+Click, macOS: Cmd+Click to add/remove from selection.\n"
            "Remember to click Save (bottom-right) to keep your colours."))
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignCenter)
        outer.addWidget(lbl)

        self.kb_widget = KeyboardWidget(layout_editor)
        self.kb_widget.clicked.connect(self.on_key_clicked)

        # Wrap in a container so the keyboard is centered with top/bottom breathing room
        kb_container = QWidget()
        kb_container_layout = QHBoxLayout(kb_container)
        kb_container_layout.setContentsMargins(0, 18, 0, 18)
        kb_container_layout.setAlignment(Qt.AlignCenter)
        kb_container_layout.addWidget(self.kb_widget)

        scroll = QScrollArea()
        scroll.setWidget(kb_container)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(280)
        outer.addWidget(scroll)

        btn_row = QHBoxLayout()
        self.lbl_selected = QLabel(tr("RGBConfigurator", "No key selected"))
        btn_row.addWidget(self.lbl_selected)
        btn_row.addStretch()
        self.btn_select_all = QPushButton(tr("RGBConfigurator", "Select All"))
        self.btn_select_all.setEnabled(False)
        self.btn_select_all.clicked.connect(self.on_select_all)
        btn_row.addWidget(self.btn_select_all)
        self.btn_color = QPushButton(tr("RGBConfigurator", "Set Color"))
        self.btn_color.setEnabled(False)
        self.btn_color.clicked.connect(self.on_pick_color)
        btn_row.addWidget(self.btn_color)
        self.btn_reset = QPushButton(tr("RGBConfigurator", "Reset Selected"))
        self.btn_reset.setEnabled(False)
        self.btn_reset.clicked.connect(self.on_reset_key)
        btn_row.addWidget(self.btn_reset)
        outer.addLayout(btn_row)

    def set_keyboard(self, keyboard):
        self.keyboard = keyboard
        self._selected_positions = set()
        self.kb_widget.deselect()
        self.lbl_selected.setText(tr("RGBConfigurator", "No key selected"))
        self.btn_select_all.setEnabled(keyboard is not None)
        self.btn_color.setEnabled(False)
        self.btn_reset.setEnabled(False)
        if keyboard is None:
            return
        self.kb_widget.set_keys(keyboard.keys, keyboard.encoders)
        self._sync_selected_widgets()
        self.refresh_key_colors()

    def refresh_key_colors(self):
        if self.keyboard is None:
            return
        for widget in self.kb_widget.widgets:
            row, col = widget.desc.row, widget.desc.col
            if row is None or col is None:
                widget.setBgColor(None)
                continue
            led = self.keyboard.vialrgb_led_map.get((row, col))
            if led is not None:
                h, s, v = self.keyboard.vialrgb_direct_colors[led]
                color = QColor.fromHsvF(h / 255.0, s / 255.0, v / 255.0) if (h or s or v) else None
                widget.setBgColor(color)
            else:
                widget.setBgColor(None)
        self.kb_widget.update()

    def _update_selection_ui(self):
        """Refresh the label, button states, and key highlights based on current selection."""
        n = len(self._selected_positions)
        if n == 0:
            self.lbl_selected.setText(tr("RGBConfigurator", "No key selected"))
            self.btn_color.setEnabled(False)
            self.btn_reset.setEnabled(False)
        elif n == 1:
            pos = next(iter(self._selected_positions))
            led = self.keyboard.vialrgb_led_map[pos]
            self.lbl_selected.setText(tr("RGBConfigurator", "LED {}").format(led))
            self.btn_color.setEnabled(True)
            self.btn_reset.setEnabled(True)
        else:
            self.lbl_selected.setText(tr("RGBConfigurator", "{} keys selected").format(n))
            self.btn_color.setEnabled(True)
            self.btn_reset.setEnabled(True)
        self._sync_selected_widgets()

    def _sync_selected_widgets(self):
        """Mark key widgets as selected so paintEvent can draw a highlight border."""
        for widget in self.kb_widget.widgets:
            row, col = widget.desc.row, widget.desc.col
            widget.selected = (row is not None and col is not None
                               and (row, col) in self._selected_positions)
        self.kb_widget.update()

    def on_key_clicked(self):
        key = self.kb_widget.active_key
        if key is None or self.keyboard is None:
            return
        row, col = key.desc.row, key.desc.col
        if row is None or col is None:
            self._selected_positions = set()
            self._update_selection_ui()
            return
        pos = (row, col)
        led = self.keyboard.vialrgb_led_map.get(pos)
        if led is None:
            # Key exists in layout but has no LED — don't include it
            if not (QApplication.keyboardModifiers() & Qt.ControlModifier):
                self._selected_positions = set()
            self._update_selection_ui()
            return

        if QApplication.keyboardModifiers() & Qt.ControlModifier:
            # Ctrl+click: toggle this key in the selection
            if pos in self._selected_positions:
                self._selected_positions.discard(pos)
            else:
                self._selected_positions.add(pos)
        else:
            # Plain click: select only this key
            self._selected_positions = {pos}

        self._update_selection_ui()

    def on_select_all(self):
        if self.keyboard is None:
            return
        self._selected_positions = {
            (w.desc.row, w.desc.col)
            for w in self.kb_widget.widgets
            if w.desc.row is not None and w.desc.col is not None
            and self.keyboard.vialrgb_led_map.get((w.desc.row, w.desc.col)) is not None
        }
        self._update_selection_ui()

    def on_pick_color(self):
        if not self._selected_positions or self.keyboard is None:
            return
        # Use the first selected key's current color as the dialog starting point
        pos = next(iter(self._selected_positions))
        led = self.keyboard.vialrgb_led_map[pos]
        h, s, v = self.keyboard.vialrgb_direct_colors[led]
        init_color = QColor.fromHsvF(h / 255.0, s / 255.0, v / 255.0) if (h or s or v) else QColor(Qt.white)

        dlg = QColorDialog(init_color)
        dlg.setModal(True)
        if dlg.exec_():
            color = dlg.selectedColor()
            if color.isValid():
                hf, sf, vf, _ = color.getHsvF()
                if hf < 0:
                    hf = 0
                new_h, new_s, new_v = int(255 * hf), int(255 * sf), int(255 * vf)
                # Update in-memory colors for all selected keys
                for pos in self._selected_positions:
                    sel_led = self.keyboard.vialrgb_led_map[pos]
                    self.keyboard.vialrgb_direct_colors[sel_led] = (new_h, new_s, new_v)
                # Send the full updated array to firmware in one batched call
                n = self.keyboard.vialrgb_num_leds
                self.keyboard.set_vialrgb_direct_fastset(0, self.keyboard.vialrgb_direct_colors[:n])
                self.refresh_key_colors()

    def on_reset_key(self):
        if not self._selected_positions or self.keyboard is None:
            return
        for pos in self._selected_positions:
            sel_led = self.keyboard.vialrgb_led_map[pos]
            self.keyboard.vialrgb_direct_colors[sel_led] = (0, 0, 0)
        n = self.keyboard.vialrgb_num_leds
        self.keyboard.set_vialrgb_direct_fastset(0, self.keyboard.vialrgb_direct_colors[:n])
        self.refresh_key_colors()

    def save_colors(self, keyboard_id):
        """Persist per-key HSV colors to a JSON file keyed by keyboard_id."""
        if self.keyboard is None:
            return
        path = _colors_save_path(keyboard_id)
        colors = [list(c) for c in self.keyboard.vialrgb_direct_colors]
        try:
            # Read existing file to preserve indicator keys if present
            existing = {}
            if os.path.exists(path):
                with open(path, "r") as f:
                    existing = json.load(f)
                if isinstance(existing, list):
                    existing = {}
            existing["version"] = 2
            existing["colors"] = colors
            with open(path, "w") as f:
                json.dump(existing, f)
        except OSError:
            pass

    def _load_colors(self, keyboard_id):
        """Load previously saved per-key HSV colors. Returns list of (h,s,v) or None."""
        path = _colors_save_path(keyboard_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            # Support both old list format and new dict format
            if isinstance(data, list):
                colors = data
            else:
                colors = data.get("colors")
                if colors is None:
                    return None
            return [(int(c[0]), int(c[1]), int(c[2])) for c in colors]
        except Exception:
            return None

    def restore_colors(self, keyboard_id):
        """Load saved colors from file and send to keyboard.
        If no saved file exists, leave the keyboard's current state untouched
        (it may have EEPROM-persisted colors already loaded from firmware).
        """
        if self.keyboard is None:
            return
        colors = self._load_colors(keyboard_id)
        if colors and len(colors) == self.keyboard.vialrgb_num_leds:
            for i, c in enumerate(colors):
                self.keyboard.vialrgb_direct_colors[i] = c
            self.keyboard.set_vialrgb_direct_fastset(0, colors)
        # No saved file: don't send anything — firmware already loaded EEPROM colors.
        self.refresh_key_colors()


class IndicatorWidget(QWidget):
    """Per-role indicator configurator.

    Select a role (Caps Lock or Layer 1-9) using the role buttons at the top.
    Click any key on the keyboard to toggle it as an indicator for that role.
    The same key can be an indicator for multiple roles simultaneously.
    Click the color swatch to change the color for the active role.
    """

    _ROLE_LABELS = ["Caps", "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9"]
    _ROLE_FULL_LABELS = [
        "Caps Lock",
        "Layer 1", "Layer 2", "Layer 3", "Layer 4", "Layer 5",
        "Layer 6", "Layer 7", "Layer 8", "Layer 9",
    ]

    def __init__(self, layout_editor):
        super().__init__()
        self.keyboard = None
        self._assignments = [{'leds': [], 'r': 0, 'g': 0, 'b': 0} for _ in range(10)]
        self._active_role = 0
        self._full_labels = list(self._ROLE_FULL_LABELS)  # mutable copy, updated per keyboard

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        self.setLayout(outer)

        help_lbl = QLabel(tr("RGBConfigurator",
            "Click to select a key. Windows: Ctrl+Click, macOS: Cmd+Click to add/remove from selection.\n"
            "Remember to click 'Apply to Keyboard', then 'Save' (bottom-right), for changes to take effect and persist."))
        help_lbl.setWordWrap(True)
        help_lbl.setAlignment(Qt.AlignCenter)
        outer.addWidget(help_lbl)

        # --- Role selector row ---
        role_row = QHBoxLayout()
        role_row.setSpacing(4)
        role_row.addWidget(QLabel(tr("RGBConfigurator", "Role:")))
        self._role_btn_group = QButtonGroup(self)
        self._role_btn_group.setExclusive(True)
        self._role_btns = []
        for idx, label in enumerate(self._ROLE_LABELS):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedWidth(38)
            self._role_btn_group.addButton(btn, idx)
            role_row.addWidget(btn)
            self._role_btns.append(btn)
        self._role_btns[0].setChecked(True)
        role_row.addStretch()
        outer.addLayout(role_row)

        # --- Active-role info row: color swatch + name + count ---
        info_row = QHBoxLayout()
        info_row.setContentsMargins(4, 2, 4, 2)
        self._swatch_btn = QPushButton()
        self._swatch_btn.setFixedSize(24, 24)
        self._swatch_btn.setToolTip(tr("RGBConfigurator", "Click to change color"))
        self._swatch_btn.clicked.connect(self.on_color_pick)
        info_row.addWidget(self._swatch_btn)
        self._role_name_lbl = QLabel()
        info_row.addWidget(self._role_name_lbl)
        self._count_lbl = QLabel()
        self._count_lbl.setStyleSheet("color: grey;")
        info_row.addWidget(self._count_lbl)
        info_row.addStretch()
        self._btn_clear_role = QPushButton(tr("RGBConfigurator", "Clear Role"))
        self._btn_clear_role.clicked.connect(self.on_clear_role)
        info_row.addWidget(self._btn_clear_role)
        outer.addLayout(info_row)

        # --- Keyboard widget ---
        self.kb_widget = KeyboardWidget(layout_editor)
        self.kb_widget.clicked.connect(self.on_key_clicked)

        kb_container = QWidget()
        kb_layout = QHBoxLayout(kb_container)
        kb_layout.setContentsMargins(0, 12, 0, 12)
        kb_layout.setAlignment(Qt.AlignCenter)
        kb_layout.addWidget(self.kb_widget)

        scroll = QScrollArea()
        scroll.setWidget(kb_container)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(260)
        outer.addWidget(scroll)

        # --- Bottom row ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_apply = QPushButton(tr("RGBConfigurator", "Apply to Keyboard"))
        self.btn_apply.clicked.connect(self.on_apply)
        btn_row.addWidget(self.btn_apply)
        outer.addLayout(btn_row)

        # Wire role buttons
        self._role_btn_group.buttonClicked[int].connect(self.on_role_selected)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def set_keyboard(self, keyboard):
        self.keyboard = keyboard
        self._active_role = 0
        self._role_btns[0].setChecked(True)
        if keyboard is None:
            return
        self.kb_widget.set_keys(keyboard.keys, keyboard.encoders)
        self._assignments = [
            {'leds': list(a.get('leds', [])), 'r': a['r'], 'g': a['g'], 'b': a['b']}
            for a in keyboard.indicator_assignments
        ]
        self._update_role_labels(keyboard)
        self._refresh_display()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_role_labels(self, keyboard):
        """Update role button text and full labels from keyboard's OLED layer names."""
        layer_names = keyboard.oled_config.get('layer_names', []) if keyboard else []
        self._full_labels = list(self._ROLE_FULL_LABELS)  # reset to defaults
        for role_idx in range(1, 10):
            layer_idx = role_idx  # role 1 = Layer 1, role 2 = Layer 2, etc. (Layer 0 has no indicator)
            name = layer_names[layer_idx].strip() if layer_idx < len(layer_names) else ''
            if name:
                self._role_btns[role_idx].setText(name[:5])
                self._full_labels[role_idx] = "Layer {} \u2014 {}".format(role_idx, name)
            else:
                self._role_btns[role_idx].setText(self._ROLE_LABELS[role_idx])
                self._full_labels[role_idx] = self._ROLE_FULL_LABELS[role_idx]

    def _refresh_display(self):
        """Refresh swatch, count label, and keyboard colors for active role."""
        if self.keyboard is None:
            return
        a = self._assignments[self._active_role]
        self._swatch_btn.setStyleSheet(
            "background-color: rgb({},{},{}); border: 2px solid #aaa;".format(
                a['r'], a['g'], a['b']))
        self._role_name_lbl.setText(
            "<b>{}</b>".format(self._full_labels[self._active_role]))
        n = len(a['leds'])
        self._count_lbl.setText(
            tr("RGBConfigurator", "— {} key{}").format(n, "s" if n != 1 else ""))
        self._refresh_key_colors()

    def _refresh_key_colors(self):
        """Color keys: active-role keys in role color, other-role keys in dim grey."""
        if self.keyboard is None:
            return
        active_leds = set(self._assignments[self._active_role]['leds'])
        other_leds = set()
        for i, a in enumerate(self._assignments):
            if i != self._active_role:
                other_leds.update(a['leds'])

        for widget in self.kb_widget.widgets:
            row, col = widget.desc.row, widget.desc.col
            led = self.keyboard.vialrgb_led_map.get((row, col)) if row is not None else None
            if led is not None and led in active_leds:
                a = self._assignments[self._active_role]
                widget.setBgColor(QColor(a['r'], a['g'], a['b']))
            elif led is not None and led in other_leds:
                widget.setBgColor(QColor(70, 70, 70))
            else:
                widget.setBgColor(None)
        self.kb_widget.update()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def on_layer_names_changed(self):
        """Called when layer names are changed in the Keymap tab."""
        if self.keyboard is not None:
            self._update_role_labels(self.keyboard)
            self._refresh_display()

    def on_role_selected(self, role_idx):
        self._active_role = role_idx
        self._refresh_display()

    def on_key_clicked(self):
        key = self.kb_widget.active_key
        if key is None or self.keyboard is None:
            return
        led = self.keyboard.vialrgb_led_map.get((key.desc.row, key.desc.col))
        if led is None:
            return
        leds = self._assignments[self._active_role]['leds']
        if led in leds:
            leds.remove(led)
        else:
            leds.append(led)
        self._refresh_display()

    def on_color_pick(self):
        a = self._assignments[self._active_role]
        dlg = QColorDialog(QColor(a['r'], a['g'], a['b']))
        dlg.setModal(True)
        if dlg.exec_():
            color = dlg.selectedColor()
            if color.isValid():
                a['r'], a['g'], a['b'] = color.red(), color.green(), color.blue()
                self._refresh_display()

    def on_clear_role(self):
        self._assignments[self._active_role]['leds'] = []
        self._refresh_display()

    def on_apply(self):
        if self.keyboard is None:
            return
        self.keyboard.set_vialrgb_indicator_leds(self._assignments)
        self.keyboard.set_vialrgb_indicator_colors(self._assignments)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_indicator_config(self, keyboard_id):
        """Merge indicator config into the shared JSON file."""
        path = _colors_save_path(keyboard_id)
        try:
            existing = {}
            if os.path.exists(path):
                with open(path, "r") as f:
                    existing = json.load(f)
                if isinstance(existing, list):
                    existing = {"version": 3, "colors": existing}
            existing["version"] = 5
            existing["indicator_assignments"] = [
                {'leds': list(a['leds']), 'r': a['r'], 'g': a['g'], 'b': a['b']}
                for a in self._assignments
            ]
            with open(path, "w") as f:
                json.dump(existing, f)
        except OSError:
            pass

    def restore_indicator_config(self, keyboard_id):
        """Load indicator config from the shared JSON file."""
        path = _colors_save_path(keyboard_id)
        if not os.path.exists(path):
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                return  # v1: no indicator data
            saved = data.get("indicator_assignments")
            if saved and len(saved) == 10:
                for i, entry in enumerate(saved):
                    # Support old formats:
                    #   v2/v3: single 'led' key (int, may be 0xFF)
                    #   v4:    'leds' list of ints with 0xFF sentinels
                    #   v5+:   'leds' list of plain LED indices (no 0xFF)
                    raw_leds = entry.get('leds')
                    if raw_leds is None:
                        # v2/v3 single-led
                        single = entry.get('led', 0xFF)
                        raw_leds = [] if single == 0xFF else [single]
                    else:
                        # Strip 0xFF sentinels from old v4 format
                        raw_leds = [int(l) for l in raw_leds if l is not None and int(l) != 0xFF]
                    self._assignments[i] = {
                        'leds': raw_leds,
                        'r':    int(entry.get('r', 0)),
                        'g':    int(entry.get('g', 0)),
                        'b':    int(entry.get('b', 0)),
                    }
                self._refresh_all()
        except Exception:
            pass


class RGBConfigurator(BasicEditor):

    def __init__(self, layout_editor):
        super().__init__()

        self.addStretch()

        w = QWidget()
        w.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.container = QGridLayout()
        w.setLayout(self.container)
        self.addWidget(w)
        self.setAlignment(w, QtCore.Qt.AlignHCenter)

        self.handler_backlight = QmkBacklightHandler(self.container)
        self.handler_backlight.update.connect(self.update_from_keyboard)
        self.handler_rgblight = QmkRgblightHandler(self.container)
        self.handler_rgblight.update.connect(self.update_from_keyboard)
        self.handler_vialrgb = VialRGBHandler(self.container)
        self.handler_vialrgb.update.connect(self.update_from_keyboard)
        self.handler_vialrgb.mode_changed.connect(self.on_vialrgb_mode_changed)
        self.handlers = [self.handler_backlight, self.handler_rgblight, self.handler_vialrgb]

        self.per_key_widget = PerKeyRGBWidget(layout_editor)
        self.addWidget(self.per_key_widget)
        self.per_key_widget.hide()

        self.indicator_widget = IndicatorWidget(layout_editor)
        self.addWidget(self.indicator_widget)
        self.indicator_widget.hide()

        self.addStretch()
        buttons = QHBoxLayout()
        buttons.addStretch()
        save_btn = QPushButton(tr("RGBConfigurator", "Save"))
        buttons.addWidget(save_btn)
        save_btn.clicked.connect(self.on_save)
        self.addLayout(buttons)

    def on_vialrgb_mode_changed(self, vialrgb_id):
        if vialrgb_id == VIALRGB_DIRECT_IDX and \
                isinstance(self.device, VialKeyboard) and self.device.keyboard.vialrgb_direct_supported:
            self.per_key_widget.show()
            kb = self.device.keyboard
            # Restore colors if all LEDs are currently dark (fresh connection / mode entry)
            if all(c == (0, 0, 0) for c in kb.vialrgb_direct_colors):
                self.per_key_widget.restore_colors(kb.keyboard_id)
            else:
                self.per_key_widget.refresh_key_colors()
        else:
            self.per_key_widget.hide()

    def on_save(self):
        kb = self.device.keyboard
        kb.save_rgb()
        if kb.rgb_mode == VIALRGB_DIRECT_IDX:
            self.per_key_widget.save_colors(kb.keyboard_id)
        if kb.lighting_vialrgb:
            self.indicator_widget.save_indicator_config(kb.keyboard_id)

    def valid(self):
        return isinstance(self.device, VialKeyboard) and \
               (self.device.keyboard.lighting_qmk_rgblight or self.device.keyboard.lighting_qmk_backlight
                or self.device.keyboard.lighting_vialrgb)

    def block_signals(self):
        for h in self.handlers:
            h.block_signals()

    def unblock_signals(self):
        for h in self.handlers:
            h.unblock_signals()

    def update_from_keyboard(self):
        self.device.keyboard.reload_rgb()

        self.block_signals()

        for h in self.handlers:
            h.update_from_keyboard()

        self.unblock_signals()

    def rebuild(self, device):
        super().rebuild(device)

        for h in self.handlers:
            h.set_device(device)

        keyboard = device.keyboard if isinstance(device, VialKeyboard) else None
        direct_kb = keyboard if keyboard is not None and keyboard.vialrgb_direct_supported else None
        self.per_key_widget.set_keyboard(direct_kb)

        if keyboard is not None and keyboard.lighting_vialrgb:
            self.indicator_widget.set_keyboard(keyboard)
            self.indicator_widget.restore_indicator_config(keyboard.keyboard_id)
            self.indicator_widget.show()
        else:
            self.indicator_widget.set_keyboard(None)
            self.indicator_widget.hide()

        if not self.valid():
            return

        self.update_from_keyboard()
