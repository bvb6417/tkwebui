"""Real Tk popups with simulated monitor work areas (no second display required)."""
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import Mock, patch

import tkwebui as ui
from tkwebui.extras import MenuPopup
from tkwebui.popups import ChoicePopup


class PopupMonitorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ui.enable_dpi_awareness()

    def setUp(self):
        self.root = tk.Tk()
        self.root.geometry('500x320+100+100')
        ui.apply_theme(self.root)
        self.owner = ttk.Button(self.root, text='Popup anchor')
        self.owner.pack(padx=20, pady=20)
        self.root.update()
        self.tip = None

    def tearDown(self):
        if self.tip:
            self.tip.hide()
        popup = getattr(self.root, '_choice_popup', None)
        if popup is not None:
            popup.close()
        self.root.update_idletasks()
        self.root.destroy()

    def choice(self, x, y, bounds, above=None):
        with patch.object(self.owner, 'winfo_rootx', return_value=x), \
             patch.object(self.owner, 'winfo_rooty', return_value=y), \
             patch.object(MenuPopup, 'work_area', return_value=bounds):
            popup = ChoicePopup(self.owner, [dict(label='One'), dict(label='Two')],
                                x, y + self.owner.winfo_height() + 4, above=above)
            self.addCleanup(lambda: popup.close() if not popup._closed else None)
            return popup

    def assert_inside(self, popup, bounds):
        popup.update_idletasks()
        left, top, right, bottom = bounds
        self.assertGreaterEqual(popup.winfo_rootx(), left)
        self.assertGreaterEqual(popup.winfo_rooty(), top)
        self.assertLessEqual(popup.winfo_rootx() + popup.winfo_width(), right)
        self.assertLessEqual(popup.winfo_rooty() + popup.winfo_height(), bottom)

    def test_dropdown_stays_on_right_monitor(self):
        x = self.root.winfo_screenwidth() + 100
        bounds = (x - 100, 0, x + 1820, 1040)
        popup = self.choice(x, 200, bounds)
        self.assert_inside(popup, bounds)
        self.assertEqual(popup.winfo_rootx(), x)

    def test_child_window_does_not_use_root_chrome_monitor(self):
        child = tk.Toplevel(self.root)
        self.owner = ttk.Button(child, text='Child popup anchor')
        self.owner.pack()
        self.root.update()
        chrome = self.root._window_chrome = Mock(attached=True)
        chrome.work_area.return_value = None
        popup = self.choice(-1700, 100, (-1920, 0, 0, 1040))
        self.assert_inside(popup, (-1920, 0, 0, 1040))
        chrome.work_area.assert_not_called()
        popup.close()
        child.destroy()

    def test_choice_negative_coordinates_are_absolute(self):
        bounds = (-1920, -1080, 0, 0)
        popup = self.choice(-1700, -800, bounds)
        self.assert_inside(popup, bounds)
        self.assertEqual(popup.winfo_rootx(), -1700)

    def test_choice_flips_above_near_work_area_bottom(self):
        popup = self.choice(500, 970, (0, 0, 1920, 1000), above=970)
        self.assert_inside(popup, (0, 0, 1920, 1000))
        self.assertLessEqual(popup.winfo_rooty() + popup.winfo_height(), 966)

    def test_menu_negative_coordinates_are_absolute(self):
        menu = ui.ThemedMenu(self.root, tearoff=False)
        menu.add_command(label='Menu item')
        bounds = (-1920, -1080, 0, 0)
        with patch.object(MenuPopup, 'work_area', return_value=bounds):
            popup = MenuPopup(self.owner, menu, -1700, -800)
        self.assert_inside(popup, bounds)
        self.assertEqual(popup.winfo_rootx(), -1700)
        self.assertEqual(popup.winfo_rooty(), -800)

    def tooltip(self, x, y, bounds, text='Tooltip on the owner monitor'):
        self.tip = ui.Tooltip(self.owner, text)
        with patch.object(self.owner, 'winfo_rootx', return_value=x), \
             patch.object(self.owner, 'winfo_rooty', return_value=y), \
             patch.object(MenuPopup, 'work_area', return_value=bounds):
            self.tip.show()
        self.tip.window.update_idletasks()
        return self.tip.window

    def test_tooltip_stays_on_right_monitor(self):
        x = self.root.winfo_screenwidth() + 100
        bounds = (x - 100, 0, x + 1820, 1040)
        popup = self.tooltip(x, 200, bounds)
        self.assert_inside(popup, bounds)
        self.assertEqual(popup.winfo_rootx(), x)

    def test_tooltip_negative_coordinates_and_bottom_edge(self):
        bounds = (-1920, -1080, 0, -40)
        popup = self.tooltip(-300, -90, bounds)
        self.assert_inside(popup, bounds)
        self.assertLess(popup.winfo_rooty(), -90)

    def test_long_tooltip_wraps_within_work_area(self):
        bounds = (0, 0, 600, 1000)
        popup = self.tooltip(550, 100, bounds, text='Long tooltip text ' * 20)
        self.assert_inside(popup, bounds)


if __name__ == '__main__':
    unittest.main()
