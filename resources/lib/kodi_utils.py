# -*- coding: utf-8 -*-
"""
    Utility functions to interact easily with Kodi

    Copyright (C) 2021 Thomas Bétous

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSE.txt for more information.
"""
import os

from requests.compat import urlencode
from urllib.parse import parse_qsl

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin


class KodiUtils:
    """Utility class to call Kodi APIs"""

    def __init__(self):
        """Initialize the object with information about the add-on"""
        self.addon_name = xbmcaddon.Addon().getAddonInfo("name")
        self.addon_id = xbmcaddon.Addon().getAddonInfo("id")
        self.addon_media = os.path.join(xbmcaddon.Addon().getAddonInfo("path"),
                                        "resources", "media")

        # Prepare other attributes that will be initialized with sys.argv
        self.addon_url = ""
        self.addon_handle = 0
        self.addon_parameters = ""

    def build_kodi_url(self, parameters):
        """Build a Kodi URL based on the parameters.

        This URL will be used to call the add-on with the expected parameters.

        :param dict parameters: The parameters that will be encoded in the URL
        """

        return "{}?{}".format(self.addon_url, urlencode(parameters))

    def create_items_in_ui(self, items_info):
        """Create items in Kodi UI

        :param list items_info: A list of dict containing all the required
        information to create the items (i.e. the return value of the method
        generate_item_info)
        """
        # Tell Kodi to use the "video" viewtypes
        xbmcplugin.setContent(handle=self.addon_handle, content="videos")

        list_of_items = []

        for info in items_info:
            # Create the ListItem object
            list_item = xbmcgui.ListItem(label=info["name"])

            # Add the general info of the item
            list_item.setInfo("video", info["info"])

            # Add the art info of the item
            list_item.setArt(info["art"])

            if not info["is_folder"]:
                list_item.setProperty("IsPlayable", "true")

            # Add to the list the tuple expected by addDirectoryItems
            list_of_items.append((info["url"], list_item, info["is_folder"]))

        # Create the items
        xbmcplugin.addDirectoryItems(
                handle=self.addon_handle,
                items=list_of_items,
                totalItems=len(list_of_items)
            )

        # Terminate the items creation
        xbmcplugin.endOfDirectory(self.addon_handle)

    def debug(self, message, prefix=None):
        """Log a message in Kodi's log with the level xbmc.LOGDEBUG

        The message will be prefixed with the prefix passed as argument or with
        the name of the add-on.

        :param str message: Message to log
        :param str prefix: String to prefix the message with
        """
        if not prefix:
            prefix = self.addon_name

        xbmc.log("[{}] {}".format(prefix, message), xbmc.LOGDEBUG)

    def generate_item_info(self, name, url, is_folder=True, thumbnail="",
                           aired="", duration=0, plot="",):
        """Return all the information required to create an item in Kodi UI

        This function makes the creation of an item easier: it allows to pass
        to the function only the known information about an item, and it will
        return a dict with all the keys expected by create_items_in_ui
        correctly initialized (including the ones that were not passed).

        :param str name: Name of the item
        :param str url: URL to reach when the item is used
        :param bool is_folder: Whether the item is a folder or is playable
        :param <other>: The other parameters are the ones expected by
        ListItem.setInfo() and ListItem.setArt()
        :return: Information required to create the item in Kodi UI
        :rtype: dict
        """
        return {
            "name": name,
            "url": url,
            "is_folder": is_folder,
            "art": {
                "thumb": thumbnail,
            },
            "info": {
                "aired": aired,
                "duration": duration,
                "plot": plot,
                "title": name
            }
        }

    def get_property(self, name):
        """Retrieve the value of a window property related to the add-on

        :param str name: Name of the property which value will be retrieved (the
        actual name of the property is prefixed with "peertube_")
        :return: Value of the window property
        :rtype: str
        """
        return xbmcgui.Window(10000).getProperty("peertube_{}".format(name))

    def get_run_parameters(self):
        """Return the parameter the add-on was called with

        The parameters are read in the method "update_call_info"

        :return: The extracted parameters
        :rtype: dict
        """
        # The first character ("?") is skipped
        return dict(parse_qsl(self.addon_parameters[1:]))

    def get_setting(self, setting_name):
        """Retrieve the value of a setting

        :param str setting_name: Name of the setting
        :return: Value of the setting named setting_name
        :rtype: str
        """
        return xbmcaddon.Addon().getSetting(setting_name)

    def get_string(self, string_id):
        """Retrieve a localized string

        :param int string_id: ID of the string in strings.po
        :return: the localized value of the string
        :rtype: str
        """
        return xbmcaddon.Addon().getLocalizedString(string_id)

    def notif_error(self, title, message):
        """Display a notification with the error icon

        :param str title: Title of the notification
        :param str message: Message of the notification
        """
        xbmcgui.Dialog().notification(
            heading=title,
            message=message,
            icon=os.path.join(self.addon_media, "icon_error.png"))

    def notif_info(self, title, message):
        """Display a notification with the info icon

        :param str title: Title of the notification
        :param str message: Message of the notification
        """
        xbmcgui.Dialog().notification(
            heading=title,
            message=message,
            icon=os.path.join(self.addon_media, "icon_info.png"))

    def notif_warning(self, title, message):
        """Display a notification with the warning icon

        :param str title: Title of the notification
        :param str message: Message of the notification
        """
        xbmcgui.Dialog().notification(
            heading=title,
            message=message,
            icon=os.path.join(self.addon_media, "icon_warning.png"))

    def open_dialog(self, title, message):
        """Open a dialog box with an "OK" button

        :param str title: Title of the box
        :param str message: Message in the box
        """
        xbmcgui.Dialog().ok(heading=title, message=message)

    def open_input_box(self, title):
        """Open a box for the user to input alphanumeric data

        :param str title: Title of the box
        :return: Entered data as a unicode string
        :rtype: str
        """
        entered_string = xbmcgui.Dialog().input(heading=title,
                                                type=xbmcgui.INPUT_ALPHANUM)

        # Check the type of the string against the type "bytes" to confirm if
        # it is a unicode or a byte string ("bytes" is known in both python 2
        # and 3).
        if isinstance(entered_string, bytes):
            return entered_string.decode("utf-8")
        else:
            return entered_string

    def play(self, url):
        """Play the media behind the URL

        :param str url: URL of the media to play
        """
        xbmcplugin.setResolvedUrl(handle=self.addon_handle,
                                  succeeded=True,
                                  listitem=xbmcgui.ListItem(path=url))

    def set_property(self, name, value):
        """Modify the value of a window property related to the add-on

        :param str name: Name of the property which value will be modified (the
        actual name of the property is prefixed with "peertube_")
        :param str value: New value of the property
        """
        xbmcgui.Window(10000).setProperty("peertube_{}".format(name), value)

    def set_setting(self, setting_name, setting_value):
        """Modify the value of a setting

        :param str setting_name: Name of the setting
        :param str setting_value: New value of the setting
        """
        xbmcaddon.Addon().setSetting(setting_name, setting_value)

    def sleep(self, time_us):
        """Sleep for some micro seconds

        :param int time_us: Sleep time in micro seconds
        """
        xbmc.sleep(time_us)

    def translate_path(self, path):
        """Translate a path using Kodi specialprotocol to an actual path
        
        :param str path: Path using Kodi special protocol
        :return: Translated path
        :rtype: str
        """
        return xbmc.translatePath(path)

    def update_call_info(self, argv):
        """Update the attributes related to the current call of the add-on

        :param list argv: System arguments
        """
        self.addon_url = argv[0]
        self.addon_handle = int(argv[1])
        self.addon_parameters = argv[2]

    def warning(self, message, prefix=None):
        """Log a message in Kodi's log with the level xbmc.LOGWARNING

        The message will be prefixed with the prefix passed as argument or with
        the name of the add-on.

        :param str message: Message to log
        :param str prefix: String to prefix the message with
        """
        if not prefix:
            prefix = self.addon_name

        xbmc.log("[{}] {}".format(prefix, message), xbmc.LOGWARNING)

kodi = KodiUtils()
