# -*- coding: utf-8 -*-

from typing import Union, List
import wx
import numpy as np


def centerOnAppMonitor(window):
    """Center a window on the application's monitor.

    This function determines the correct monitor by:
    1. If main window exists, use its monitor
    2. Otherwise, try to get saved monitor_index from app settings
    3. Fall back to primary monitor

    Call this after the window is created and sized but before Show().
    """
    app = wx.GetApp()
    target_monitor = None

    # Try to get monitor from main window (but not if we ARE the main window)
    if app:
        main_window = app.GetTopWindow()
        # Skip if main_window is the window we're trying to position
        if main_window and main_window is not window and main_window.IsShown():
            main_rect = main_window.GetScreenRect()
            target_monitor = wx.Display.GetFromPoint(
                wx.Point(main_rect.x + main_rect.width // 2,
                         main_rect.y + main_rect.height // 2)
            )

    # Fall back to saved monitor from settings
    if target_monitor is None or target_monitor == wx.NOT_FOUND:
        if app and hasattr(app, 'settings'):
            try:
                saved_monitor = app.settings.getint("window", "monitor_index")
                if 0 <= saved_monitor < wx.Display.GetCount():
                    target_monitor = saved_monitor
            except (KeyError, ValueError, AttributeError):
                pass

    # Fall back to primary monitor
    if target_monitor is None or target_monitor == wx.NOT_FOUND:
        target_monitor = 0

    # Center on target monitor
    if target_monitor < wx.Display.GetCount():
        display = wx.Display(target_monitor)
        display_rect = display.GetGeometry()
        window_size = window.GetSize()
        x = display_rect.x + (display_rect.width - window_size.width) // 2
        y = display_rect.y + (display_rect.height - window_size.height) // 2
        window.SetPosition(wx.Point(x, y))


def getButtonFromStdDialogButtonSizer(
    sizer: wx.StdDialogButtonSizer, buttonId: int
) -> Union[wx.Button, None]:
    for child in sizer.GetChildren():
        if (
            isinstance(child.GetWindow(), wx.Button)
            and child.GetWindow().GetId() == buttonId
        ):
            return child.GetWindow()

    return None


def getAlphaDataFromImage(image: wx.Image):
    """Get image alpha data as a NumPy uint8 array."""
    return np.frombuffer(image.GetAlpha(), dtype=np.uint8)


def setAlphaDataToImage(image: wx.Image, data):
    """Set alpha data on image. Supports NumPy arrays, bytes, lists."""
    if not image.HasAlpha():
        image.InitAlpha()

    width = image.GetWidth()
    height = image.GetHeight()
    expected_size = width * height

    if isinstance(data, np.ndarray):
        data_array = data.astype(np.uint8).flatten()
    elif isinstance(data, (list, tuple)):
        data_array = np.array(data, dtype=np.uint8)
    elif isinstance(data, (bytes, bytearray)):
        data_array = np.frombuffer(data, dtype=np.uint8)
    else:
        raise TypeError(f"Unsupported data type: {type(data)}")

    if data_array.size != expected_size:
        if data_array.size > expected_size:
            data_array = data_array[:expected_size]
        else:
            padded_data = np.zeros(expected_size, dtype=np.uint8)
            padded_data[: data_array.size] = data_array
            data_array = padded_data

    data_array = np.clip(data_array, 0, 255)
    image.SetAlpha(data_array.tobytes())


def clearAlphaDataOfImage(image: wx.Image, value: int):
    """Fill image alpha channel with a uniform value."""
    if not image.HasAlpha():
        image.InitAlpha()

    size = image.GetWidth() * image.GetHeight()
    alpha_array = np.full(size, value, dtype=np.uint8)
    image.SetAlpha(alpha_array.tobytes())


def mergeImagesWithAlpha(main_image, overlay_image, overlay_position):
    """Merge alpha channels of two images."""
    main_width, main_height = main_image.GetWidth(), main_image.GetHeight()
    overlay_width, overlay_height = (
        overlay_image.GetWidth(),
        overlay_image.GetHeight(),
    )
    overlay_x, overlay_y = overlay_position

    y_start, y_end = overlay_y, min(overlay_y + overlay_height, main_height)
    x_start, x_end = overlay_x, min(overlay_x + overlay_width, main_width)
    actual_overlay_height = y_end - y_start
    actual_overlay_width = x_end - x_start

    main_alpha = getAlphaDataFromImage(main_image).reshape(
        main_height, main_width
    )
    overlay_alpha = np.frombuffer(
        overlay_image.GetAlphaBuffer(), dtype=np.uint8
    ).reshape(overlay_height, overlay_width)

    if (actual_overlay_height < overlay_height
            or actual_overlay_width < overlay_width):
        overlay_alpha = overlay_alpha[
            :actual_overlay_height, :actual_overlay_width
        ]

    result_alpha = main_alpha.copy()
    result_alpha[y_start:y_end, x_start:x_end] = np.maximum(
        result_alpha[y_start:y_end, x_start:x_end], overlay_alpha
    )

    result_image = main_image.Copy()
    setAlphaDataToImage(result_image, result_alpha)

    return result_image
