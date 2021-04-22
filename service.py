# -*- coding: utf-8 -*-
"""
    PeerTube service to download torrents in the background

    Copyright (C) 2018 Cyrille Bollu
    Copyright (C) 2021 Thomas Bétous

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSE.txt for more information.
"""

import AddonSignals # Module exists only in Kodi - pylint: disable=import-error
from threading import Thread
import xbmc # Kodistubs for Leia is not compatible with python3 / pylint: disable=syntax-error
import xbmcvfs # Kodistubs for Leia is not compatible with python3 / pylint: disable=syntax-error

from resources.lib.kodi_utils import kodi

class PeertubeDownloader(Thread):
    """
    A class to download PeerTube torrents in the background
    """

    def __init__(self, url, temp_dir):
        """
        Initialise a PeertubeDownloader instance for downloading the torrent
        specified by url

        :param url, temp_dir: str
        :return: None
        """
        Thread.__init__(self)
        self.torrent = url
        self.temp_dir = temp_dir

    def debug(self, message):
        """Log a debug message

        :param str message: Message to log (will be prefixed with the name of
        the class)
        """
        kodi.debug(message=message, prefix="PeertubeDownloader")

    def run(self):
        """
        Download the torrent specified by self.torrent
        :param: None
        :return: None
        """

        self.debug("Opening BitTorent session")
        # Open BitTorrent session
        ses = libtorrent.session()
        ses.listen_on(6881, 6891)

        # Add torrent
        self.debug("Adding torrent {}".format(self.torrent))
        h = ses.add_torrent({"url": self.torrent, "save_path": self.temp_dir})

        # Set sequential mode to allow watching while downloading
        h.set_sequential_download(True)

        # Download torrent
        self.debug("Downloading torrent {}".format(self.torrent))
        signal_sent = 0
        while not h.is_seed():
            xbmc.sleep(1000)
            s = h.status()
            # Inform addon that all the metadata has been downloaded and that
            # it may start playing the torrent
            if s.state >=3 and signal_sent == 0:
                self.debug("Received all torrent metadata, notifying"
                           " PeertubeAddon")
                i = h.torrent_file()
                f = self.temp_dir + i.name()
                AddonSignals.sendSignal("metadata_downloaded", {"file": f})
                signal_sent = 1

class PeertubeService():
    """
    Class used to run a service when Kodi starts
    """

    def __init__(self):
        """
        PeertubeService initialisation function
        """
        # Create our temporary directory
        self.temp = "{}{}".format(xbmc.translatePath("special://temp"),
                                  "plugin.video.peertube/")
        if not xbmcvfs.exists(self.temp):
            xbmcvfs.mkdir(self.temp)

    def debug(self, message):
        """Log a debug message

        :param str message: Message to log (will be prefixed with the name of
        the class)
        """
        kodi.debug(message=message, prefix="PeertubeService")

    def download_torrent(self, data):
        """
        Start a downloader thread to download torrent specified by data["url"]
        :param data: dict
        :return: None
        """

        self.debug("Received a start_download signal")
        downloader = PeertubeDownloader(data["url"], self.temp)
        downloader.start()

    def run(self):
        """
        Main loop of the PeertubeService class

        It registers the start_download signal to start a PeertubeDownloader
        thread when needed, and exit when Kodi is shutting down.
        """

        self.debug("Starting")

        # Launch the download_torrent callback function when the
        # "start_download" signal is received
        AddonSignals.registerSlot(kodi.addon_id,
                                  "start_download",
                                  self.download_torrent)

        # Monitor Kodi's shutdown signal
        self.debug("Service started, waiting for signals")
        monitor = xbmc.Monitor()
        while not monitor.abortRequested():
            if monitor.waitForAbort(1):
                # Abort was requested while waiting. We must exit
                # TODO: Clean temporary directory
                self.debug("Exiting")
                break

if __name__ == "__main__":
    # Create a PeertubeService instance
    service = PeertubeService()

    # Import libtorrent here to manage when the library is not installed
    try:
        import libtorrent
        LIBTORRENT_IMPORTED = True
    except ImportError as exception:
        LIBTORRENT_IMPORTED = False
        service.debug("The libtorrent library could not be imported because of"
                      " the following error:\n{}".format(exception))

    # Save whether libtorrent could be imported as a window property so that
    # this information can be retrieved by the add-on
    kodi.set_property("libtorrent_imported", str(LIBTORRENT_IMPORTED))

    # Start the service
    service.run()
