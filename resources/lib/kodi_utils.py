# -*- coding: utf-8 -*-
"""
    Utility functions to interact easily with Kodi

    Copyright (C) 2021 Thomas Bétous

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSE.txt for more information.
"""
import xbmc
import xbmcgui


def debug(message):
    """Log a message in Kodi's log with the level xbmc.LOGDEBUG

    :param str message: Message to log
    """
    xbmc.log(message, xbmc.LOGDEBUG)

def get_property(name):
    """Retrieve the value of a window property related to the add-on

    :param str name: name of the property which value will be retrieved (the
    actual name of the property is prefixed with "peertube_")
    :return: the value of the window property
    :rtype: str
    """
    return xbmcgui.Window(10000).getProperty('peertube_{}'.format(name))

def notif_error(title, message):
    """Display a notification with the error icon

    :param str title: Title of the notification
    :param str message: Message of the notification
    """
    xbmcgui.Dialog().notification(heading=title,
                                  message=message,
                                  icon=xbmcgui.NOTIFICATION_ERROR)

def notif_info(title, message):
    """Display a notification with the info icon

    :param str title: Title of the notification
    :param str message: Message of the notification
    """
    xbmcgui.Dialog().notification(heading=title,
                                  message=message,
                                  icon=xbmcgui.NOTIFICATION_INFO)

def notif_warning(title, message):
    """Display a notification with the warning icon

    :param str title: Title of the notification
    :param str message: Message of the notification
    """
    xbmcgui.Dialog().notification(heading=title,
                                  message=message,
                                  icon=xbmcgui.NOTIFICATION_WARNING)

def open_dialog(title, message):
    """Open a dialog box with an "OK" button

    :param str title: Title of the box
    :param str message: Message in the box
    """
    xbmcgui.Dialog().ok(heading=title, line1=message)

def set_property(name, value):
    """Modify the value of a window property related to the add-on

    :param str name: Name of the property which value will be modified (the
    actual name of the property is prefixed with "peertube_")
    :param str value: New value of the property
    """
    xbmcgui.Window(10000).setProperty('peertube_{}'.format(name), value)
