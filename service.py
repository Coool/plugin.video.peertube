# -*- coding: utf-8 -*-
"""
    PeerTube service to perform action on torrents in background

    Copyright (C) 2018 Cyrille Bollu
    Copyright (C) 2021 Thomas Bétous

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSE.txt for more information.
"""
import AddonSignals
import xbmc
import xbmcvfs

from resources.lib.kodi_utils import kodi

class PeertubePlayer(xbmc.Player):
    # Initialize the attributes and call the parent class constructor
    def __init__(self):
        self.torrent_url = None
        super(xbmc.Player, self).__init__()
        # super().__init__()

    # This function will be called through AddonSignals when a video is played.
    # It will save the URL expected by vfs.libtorrent to control the torrent. 
    def receive_torrent(self, data):
        self.torrent_url = data["torrent_url"]
        kodi.debug(message="Received handle:\n{}".format(self.torrent_url), prefix="PeertubePlayer")

    # Callback when the playback is stopped. It is used to pause the torrent to
    # avoid downloading in background a video which may never be played.
    def onPlayBackStopped(self):
        if self.torrent_url is not None:
            kodi.debug(message="Playback stopped: pausing torrent...", prefix="PeertubePlayer")            
            # Get the torrent handle
            torrent = xbmcvfs.File(self.torrent_url)
            # Call seek() to pause the torrent. 0 is used as second argument so
            # that GetLength() is not called.
            torrent.seek(0, 0)
            self.torrent_url = None

class PeertubeService():
    """
    Class used to run a service when Kodi starts
    """

    def __init__(self):
        """
        Create an instance of PeertubePlayer that will always be active
        (required to monitor the events and call the callbacks)
        """
        self.player = PeertubePlayer()

    def debug(self, message):
        """Log a debug message

        :param str message: Message to log (will be prefixed with the name of
        the class)
        """
        kodi.debug(message=message, prefix="PeertubeService")

    def run(self):
        """
        Main loop of the PeertubeService class

        """

        # Signal that is sent by the main script of the add-on
        AddonSignals.registerSlot(kodi.addon_id,
                                  "get_torrent",
                                  self.player.receive_torrent)


        # Display a notification now that the service started.
        self.debug("Service started")
        if kodi.get_setting("service_start_notif") == "true":
            kodi.notif_info(title=kodi.get_string(30400),
                            message=kodi.get_string(30401))

        # Run the service until Kodi exits
        monitor = xbmc.Monitor()
        while not monitor.abortRequested():
            if monitor.waitForAbort(1):
                # Abort was requested while waiting. We must exit.
                self.debug("Exiting")
                break

if __name__ == "__main__":
    # Create a PeertubeService instance
    service = PeertubeService()

    # Start the service
    service.run()
