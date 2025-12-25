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


def getAlphaDataFromImage(image: wx.Image, as_numpy=True):
    """Get image alpha data, supports returning NumPy array"""
    alpha_data = image.GetAlpha()
    if as_numpy:
        return np.frombuffer(alpha_data, dtype=np.uint8)
    else:
        return alpha_data


def setAlphaDataToImage(image: wx.Image, data):
    """Enhanced setAlphaDataToImage that directly supports NumPy arrays"""
    if not image.HasAlpha():
        image.InitAlpha()

    width = image.GetWidth()
    height = image.GetHeight()
    expected_size = width * height

    # Unified handling of various input types
    if isinstance(data, np.ndarray):
        # Directly use NumPy array
        data_array = data.astype(np.uint8).flatten()
    elif isinstance(data, (list, tuple)):
        # Convert list/tuple to NumPy array
        data_array = np.array(data, dtype=np.uint8)
    elif isinstance(data, (bytes, bytearray)):
        # Directly use byte data
        data_array = np.frombuffer(data, dtype=np.uint8)
    else:
        raise TypeError(f"Unsupported data type: {type(data)}")

    # Validate and adjust data size
    if data_array.size != expected_size:
        if data_array.size > expected_size:
            data_array = data_array[:expected_size]
        else:
            # Pad with zeros if data is insufficient
            padded_data = np.zeros(expected_size, dtype=np.uint8)
            padded_data[: data_array.size] = data_array
            data_array = padded_data

    # Ensure data is within valid range
    data_array = np.clip(data_array, 0, 255)

    # Set all alpha data at once
    image.SetAlpha(data_array.tobytes())


def clearAlphaDataOfImage(image: wx.Image, value: int):
    if not image.HasAlpha():
        image.InitAlpha()

    width = image.GetWidth()
    height = image.GetHeight()

    # Create a writable array filled with the value
    alpha_array = np.full(width * height, value, dtype=np.uint8)
    image.SetAlpha(alpha_array.tobytes())


def mergeImagesWithAlpha(main_image, overlay_image, overlay_position):
    """
    Efficiently merge alpha channels of two images using NumPy
    """
    main_width, main_height = main_image.GetWidth(), main_image.GetHeight()
    overlay_width, overlay_height = (
        overlay_image.GetWidth(),
        overlay_image.GetHeight(),
    )
    overlay_x, overlay_y = overlay_position

    # Directly get NumPy arrays
    main_alpha = getAlphaDataFromImage(main_image).reshape(
        main_height, main_width
    )
    overlay_alpha = np.frombuffer(
        overlay_image.GetAlphaBuffer(), dtype=np.uint8
    ).reshape(overlay_height, overlay_width)

    # Calculate overlay region
    y_start, y_end = overlay_y, min(overlay_y + overlay_height, main_height)
    x_start, x_end = overlay_x, min(overlay_x + overlay_width, main_width)

    # Adjust overlay alpha dimensions
    actual_overlay_height = y_end - y_start
    actual_overlay_width = x_end - x_start

    if (
        actual_overlay_height < overlay_height
        or actual_overlay_width < overlay_width
    ):
        overlay_alpha = overlay_alpha[
            :actual_overlay_height, :actual_overlay_width
        ]

    # Merge alpha channels
    result_alpha = main_alpha.copy()
    result_alpha[y_start:y_end, x_start:x_end] = np.maximum(
        result_alpha[y_start:y_end, x_start:x_end], overlay_alpha
    )

    # Create result image
    result_image = main_image.Copy()
    setAlphaDataToImage(result_image, result_alpha)

    return result_image
