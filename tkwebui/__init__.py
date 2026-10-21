"""TkWebUI: modern Web-style theme and widgets for standard tkinter/ttk.

Standard library only. Call enable_dpi_awareness() before Tk(), then
apply_theme(root) before creating widgets:

    import tkinter as tk
    from tkwebui import enable_dpi_awareness, apply_theme

    enable_dpi_awareness()
    root = tk.Tk()
    apply_theme(root)

Every component can also be imported from its own module, e.g.
``from tkwebui.charts import LineChart``.
"""
__version__ = '0.3.1'

from .scrolling import AutoScrollbar
from .placeholder import set_placeholder, PlaceholderEntry
from .core import (PALETTE, THEME, enable_dpi_awareness, icon, apply_theme, Card, SegmentedControl,
                   Sidebar, ScrollArea, Tooltip, Dropdown, Accordion, SettingRow, BarChart, CardList,
                   ProgressSlider, Modal)
from .widgets import (RoundedText, SectionCard, ResponsiveTable, configure_table, auto_hide_text_scrollbar,
                      focus_when_mapped, initial_window_bounds, align_tree_scrollbar)
from .popups import ChoicePopup, ThemedCombobox, ThemedMenu
from .extras import SquareSwitch, ToggleButton, ToolButton, MenuButton, OptionMenu, RoundedListbox
from .table import SortableTreeview, enable_sorting, Spreadsheet
from .charts import LineChart, ColumnChart, ScatterChart, DonutChart, PieChart
from .forms import (Badge, ValidatedEntry, ResultDialog, MessageDialog, InputDialog, Dialogs, DateEntry,
                    CalendarPopup, ValueSlider)
from .feedback import ToastNotification, notify, TextProgress, Meter
from .dataview import DataTable
from .media import ColorPicker, ColorDialog, FontPicker, FontDialog, ImageViewer
from .window_chrome import WindowChrome

__all__ = [
    'AutoScrollbar', 'set_placeholder', 'PlaceholderEntry',
    'PALETTE', 'THEME', 'enable_dpi_awareness', 'icon', 'apply_theme',
    'Card', 'SegmentedControl', 'Sidebar', 'ScrollArea', 'Tooltip', 'Dropdown', 'Accordion', 'SettingRow',
    'BarChart', 'CardList', 'ProgressSlider', 'Modal',
    'RoundedText', 'SectionCard', 'ResponsiveTable', 'configure_table', 'auto_hide_text_scrollbar',
    'focus_when_mapped', 'initial_window_bounds', 'align_tree_scrollbar',
    'ChoicePopup', 'ThemedCombobox', 'ThemedMenu',
    'SquareSwitch', 'ToggleButton', 'ToolButton', 'MenuButton', 'OptionMenu', 'RoundedListbox',
    'SortableTreeview', 'enable_sorting', 'Spreadsheet',
    'LineChart', 'ColumnChart', 'ScatterChart', 'DonutChart', 'PieChart',
    'Badge', 'ValidatedEntry', 'ResultDialog', 'MessageDialog', 'InputDialog', 'Dialogs', 'DateEntry',
    'CalendarPopup', 'ValueSlider',
    'ToastNotification', 'notify', 'TextProgress', 'Meter',
    'DataTable',
    'ColorPicker', 'ColorDialog', 'FontPicker', 'FontDialog', 'ImageViewer',
    'WindowChrome',
]
