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
        self.run_url = None
        self.playback_started = False
        super(xbmc.Player, self).__init__()
        # TODO: Use the python3 format on Matrix
        # super().__init__()

    def debug(self, message):
        """Log a debug message with the name of the class as prefix

        :param str message: message to log
        """
        kodi.debug(message=message, prefix="PeertubePlayer")

    def onAVStarted(self):
        """Callback called when Kodi has a video stream.

        When it is called we consider that the video is actually being played
        and we set the according flag.
        """
        # Check if the file that is being played belongs to this add-on to not
        # conflict with other add-ons or players.
        if self.torrent_url is not None:
            self.playback_started = True
            self.debug(message="Playback started for {}".format(self.torrent_url))

    def onPlayBackStopped(self):
        """Callback called when the playback stops

        If the file was actually being played (i.e. onAVStarted() was called for
        this file before), then we consider that the playback didn't encounter
        any error and it was stopped willingly by the user. In this case we
        pause the download of the torrent to avoid downloading in background a
        video which may never be played again.
        But if no file was being played, we ask the user if the download should
        be paused or not: it supports the use case when the playback started
        whereas the portion of the file that was downloaded was not big enough.
        """
        # First check if the file that was being played belongs to this add-on
        # to not conflict with other add-ons or players.
        if self.torrent_url is not None:
            # Then check if the playback actually started: if the playback
            # didn't start (probably because there was a too small portion of
            # the file that was downloaded), ask the user if the download of
            # the torrent should be paused (Kodi do not call onPlayBackError()
            # in this case for some reason...).
            # Otherwise pause the torrent because we consider the user decided
            # to stop the playback.
            if self.playback_started:
                self.debug(message="Playback stopped: pausing download...")
                self.pause_torrent()
                self.torrent_url = None
                self.playback_started = False
            else:
                self.debug(message="Playback stopped but an error was"
                                    " detected: asking the user if the"
                                    " download must be stopped.")
                if kodi.open_yes_no_dialog(title=kodi.get_string(30423),
                                           message=kodi.get_string(30424)):
                    self.debug(message="Pausing the download...")
                    self.pause_torrent()
                    self.torrent_url = None
                    self.playback_started = False

    def pause_torrent(self):
        """Pause download of the torrent self.torrent_url"""
        # Get the torrent handle
        torrent = xbmcvfs.File(self.torrent_url)
        # Call seek() with -1 to pause the torrent.
        torrent.seek(-1)

    def update_torrent_info(self, data):
        """Save the information about the torrent being played currently

        This function is called through AddonSignals when a video is played.
        """
        self.torrent_url = data["torrent_url"]
        self.run_url = data["run_url"]
        self.debug(message="Received information:\nURL={}\nrun_url={}"
                           .format(self.torrent_url, self.run_url))


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
                                  "torrent_information",
                                  self.player.update_torrent_info)


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
