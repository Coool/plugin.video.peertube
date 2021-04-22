# -*- coding: utf-8 -*-
"""
    Main class used by the add-on

    Copyright (C) 2018 Cyrille Bollu
    Copyright (C) 2021 Thomas Bétous

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSE.txt for more information.
"""
import AddonSignals # Module exists only in Kodi - pylint: disable=import-error

from resources.lib.kodi_utils import kodi
from resources.lib.peertube import PeerTube, list_instances


class PeerTubeAddon():
    """
    Main class used by the add-on
    """

    # URL of the page which explains how to install libtorrent
    HELP_URL = "https://link.infini.fr/libtorrent-peertube-kodi"

    def __init__(self):
        """Initialize parameters and create a PeerTube instance"""

        # Get the number of items to show per page
        self.items_per_page = int(kodi.get_setting("items_per_page"))

        # Get the preferred resolution for video
        self.preferred_resolution = \
            int(kodi.get_setting("preferred_resolution"))

        # Nothing to play at initialisation
        self.play = False
        self.torrent_name = ""
        self.torrent_file = ""

        # Check whether libtorrent could be imported by the service. The value
        # of the associated property is retrieved only once and stored in an
        # attribute because libtorrent is imported only once at the beginning
        # of the service (we assume it is not possible to start the add-on
        # before the service)
        self.libtorrent_imported = \
            kodi.get_property("libtorrent_imported") == "True"

        # Create a PeerTube object to send requests: settings which are used
        # only by this object are directly retrieved from the settings
        self.peertube = PeerTube(
            instance=kodi.get_setting("preferred_instance"),
            count=self.items_per_page,
            sort=kodi.get_setting("video_sort_method"),
            video_filter=kodi.get_setting("video_filter"))

    def _browse_videos(self, start):
        """Display the list of all the videos published on a PeerTube instance

        :param int start: index of the first video to display (pagination)
        """

        # Use the API to get the list of the videos
        results = self.peertube.list_videos(start)

        # Extract the information of each video from the API response
        list_of_videos = self._create_list_of_videos(results, start)

        # Create the associated items in Kodi
        kodi.create_items_in_ui(list_of_videos)

    def _browse_instances(self, start):
        """
        Function to navigate through all the PeerTube instances

        :param int start: index of the first instance to display (pagination)
        """

        # Use the API to get the list of the instances
        results = list_instances(start)

        # Extract the information of each instance from the API response
        list_of_instances = self._create_list_of_instances(results, start)

        # Create the associated items in Kodi
        kodi.create_items_in_ui(list_of_instances)

    def _create_list_of_instances(self, response, start):
        """Generator of instance items to be added in Kodi UI

        :param dict response: data returned by joinpeertube
        :param int start: index of the first item to display (pagination)
        :return: yield the information of each item
        :rtype: dict
        """

        for data in response["data"]:

            # The description of each instance in Kodi will be composed of:
            # * the description of the instance (from joinpeertube.org)
            # * the number of local videos hosted on this instance
            # * the number of users on this instance
            description = "{}\n\n----------\nNumber of local videos: {}\n"\
                          "Number of users: {}".format(
                          data["shortDescription"].encode("utf-8"),
                          data["totalLocalVideos"],
                          data["totalUsers"])
            # The value of "totalLocalVideos" and "totalUsers" are int so they
            # don't need to be encoded.

            instance_info = kodi.generate_item_info(
                name=data["name"],
                url=kodi.build_kodi_url({
                    "action": "select_instance",
                    "url": data["host"]
                    }
                ),
                is_folder=True,
                plot=description
            )

            yield instance_info
        else:
            # Add a "Next page" button when there are more items to show
            next_page_item = self._create_next_page_item(
                total=int(response["total"]),
                current_index=start,
                url=kodi.build_kodi_url(
                    {
                        "action": "browse_instances",
                        "start": start + self.items_per_page
                    }
                )
            )

            if next_page_item:
                yield next_page_item

    def _create_list_of_videos(self, response, start):
        """Generator of video items to be added in Kodi UI

        :param dict response: data returned by PeerTube
        :param int start: index of the first item to display (pagination)
        :return: yield the information of each item
        :rtype: dict
        """

        for data in response["data"]:

            video_info = kodi.generate_item_info(
                name=data["name"],
                url=kodi.build_kodi_url(
                    {
                        "action": "play_video",
                        "id": data["uuid"]
                    }
                ),
                is_folder=False,
                plot=data["description"],
                duration=data["duration"],
                thumbnail="{0}/{1}".format(self.peertube.instance,
                                           data["thumbnailPath"]),
                aired=data["publishedAt"]
            )

            yield video_info
        else:
            # Add a "Next page" button when there are more items to show
            next_page_item = self._create_next_page_item(
                total=int(response["total"]),
                current_index=start,
                url=kodi.build_kodi_url(
                    {
                        "action": "browse_videos",
                        "start": start + self.items_per_page
                    }
                )
            )

            if next_page_item:
                yield next_page_item

    def _create_next_page_item(self, total, current_index, url):
        """Return the info required to create an item to go to the next page

        :param int total: total number of elements
        :param int current_index: index of the first element currently used
        :param str url: URL to reach when the "Next page" item is run
        :return: yield the info to create a "Next page" item in Kodi UI if
        there are more items to show
        :rtype: dict
        """
        next_index = current_index + self.items_per_page
        if total > next_index:
            next_page = (next_index / self.items_per_page) + 1
            total_pages = (total / self.items_per_page) + 1

            next_page_item = kodi.generate_item_info(
                name="Next page ({}/{})".format(next_page, total_pages),
                url=url
            )

            return next_page_item

    def _get_video_url(self, video_id, instance=None):
        """Find the URL of the video with the best possible quality matching
        user's preferences.

        :param str video_id: ID of the torrent linked with the video
        :param str instance: PeerTube instance hosting the video (optional)
        :return: URL of the video containing the resolution
        :rtype: str
        """
        # Retrieve the information about the video including the different
        # resolutions available
        video_files = self.peertube.get_video_urls(video_id, instance=instance)

        # Find the best resolution matching user's preferences
        current_resolution = 0
        higher_resolution = -1
        url = ""
        for video in video_files:
            # Get the resolution
            resolution = video["resolution"]
            if resolution == self.preferred_resolution:
                # Stop directly when we find the exact same resolution as the
                # user's preferred one
                kodi.debug("Found video with preferred resolution ({})"
                           .format(self.preferred_resolution))
                url = video["url"]
                break
            elif (resolution < self.preferred_resolution
                    and resolution > current_resolution):
                # Otherwise, try to find the best one just below the user's
                # preferred one
                kodi.debug("Found video with good lower resolution ({})"
                            .format(resolution))
                url = video["url"]
                current_resolution = resolution
            elif (resolution > self.preferred_resolution and
                    (resolution < higher_resolution or
                     higher_resolution == -1)):
                # In the worst case, we'll take the one just above the user's
                # preferred one
                kodi.debug("Saving video with higher resolution ({}) as a"
                           " possible alternative".format(resolution))
                backup_url = video["url"]
                higher_resolution = resolution
            else:
                kodi.debug("Ignoring the resolution '{}'".format(resolution))

        # When we didn't find a resolution equal or lower than the user's
        # preferred one, use the resolution just above the preferred one
        if not url:
            kodi.debug("Using video with higher resolution as alternative ({})"
                        .format(higher_resolution))
            url = backup_url

        return url

    def _home_page(self):
        """Display the items of the home page of the add-on"""

        home_page_items = [
            kodi.generate_item_info(
                name="Browse videos on the selected instance",
                url=kodi.build_kodi_url({"action": "browse_videos","start": 0})
            ),
            kodi.generate_item_info(
                name="Search videos on the selected instance",
                url=kodi.build_kodi_url({"action": "search_videos","start": 0})
            ),
            kodi.generate_item_info(
                name="Browse videos on the selected instance",
                url=kodi.build_kodi_url({
                    "action": "browse_instances",
                    "start": 0
                    }
                )
            )
        ]

        kodi.create_items_in_ui(home_page_items)

    def _search_videos(self, start):
        """
        Function to search for videos on a PeerTube instance

        :param str start: index of the first video to display (pagination)
        """

        # Ask the user which keywords must be searched for
        keywords = kodi.open_input_box(
            title="Search videos on {}".format(self.peertube.instance))

        # Go back to the home page when the user cancels or didn't enter any
        # string
        if not keywords:
            return

        # Use the API to search for videos
        results = self.peertube.search_videos(keywords, start)

        # Exit directly when no result is found
        if not results:
            kodi.notif_warning(
                title="No videos found",
                message="No videos found matching the keywords.")
            return

        # Extract the information of each video from the API response
        list_of_videos = self._create_list_of_videos(results, start)

        # Create the associated items in Kodi
        kodi.create_items_in_ui(list_of_videos)

    def _play_video(self, torrent_url):
        """
        Start the torrent's download and play it while being downloaded

        :param str torrent_url: URL of the torrent file to download and play
        """
        # If libtorrent could not be imported, display a message and do not try
        # download nor play the video as it will fail.
        if not self.libtorrent_imported:
            kodi.open_dialog(
                title="Error: libtorrent could not be imported",
                message="PeerTube cannot play videos without libtorrent\n"
                        "Please follow the instructions at {}"
                        .format(self.HELP_URL))
            return

        kodi.debug("Starting torrent download ({})".format(torrent_url))
        kodi.notif_info(title="Download started",
                        message="The video will be played soon.")

        # Start a downloader thread
        AddonSignals.sendSignal("start_download", {"url": torrent_url})

        # Wait until the PeerTubeDownloader has downloaded all the torrent's
        # metadata
        AddonSignals.registerSlot(kodi.addon_id,
                                  "metadata_downloaded",
                                  self._play_video_continue)
        timeout = 0
        while not self.play and timeout < 10:
            kodi.sleep(1000)
            timeout += 1

        # Abort in case of timeout
        if timeout == 10:
            kodi.notif_error(
                title="Download timeout",
                message="Timeout fetching {}".format(torrent_url))
            return
        else:
            # Wait a little before starting playing the torrent
            kodi.sleep(3000)

        # Pass the item to the Kodi player for actual playback.
        kodi.debug("Starting video playback ({})".format(self.torrent_file))
        kodi.play(self.torrent_file)

    def _play_video_continue(self, data):
        """
        Callback function to let the _play_video method resume when the
        PeertubeDownloader has downloaded all the torrent's metadata

        :param data: dict of information sent from PeertubeDownloader
        """

        kodi.debug(
            "Received metadata_downloaded signal, will start playing media")
        self.play = True
        self.torrent_file = data["file"]

    def _select_instance(self, instance):
        """
        Change currently selected instance to "instance" parameter

        :param str instance: URL of the new instance
        """

        # Update the PeerTube object attribute even though it is not used
        # currently (because the value will be retrieved from the settings on
        # the next run of the add-on but it may be useful in case
        # reuselanguageinvoker is enabled)
        self.peertube.set_instance(instance)

        # Update the preferred instance in the settings so that this choice is
        # reused on the next runs and the next calls of the add-on
        kodi.set_setting("preferred_instance", instance)

        # Notify the user and log the event
        message = \
            "{} is now the selected instance".format(self.peertube.instance)
        kodi.notif_info(title="Current instance changed", message=message)
        kodi.debug(message)

    def router(self, params):
        """Route the add-on to the requested actions

        :param dict params: Parameters the add-on was called with
        """

        # Check the parameters passed to the plugin
        if params:
            action = params["action"]
            if action == "browse_videos":
                # Browse videos on the selected instance
                self._browse_videos(int(params["start"]))
            elif action == "search_videos":
                # Search for videos on the selected instance
                self._search_videos(int(params["start"]))
            elif action == "browse_instances":
                # Browse PeerTube instances
                self._browse_instances(int(params["start"]))
            elif action == "play_video":
                # This action comes with the id of the video to play as
                # parameter. The instance may also be in the parameters. Use
                # these parameters to retrieve the complete URL (containing the
                # resolution).
                url = self._get_video_url(instance=params.get("instance"),
                                          video_id=params.get("id"))
                # Play the video using the URL
                self._play_video(url)
            elif action == "select_instance":
                # Set the selected instance as the preferred instance
                self._select_instance(params["url"])
        else:
            # Display the addon's main menu when the plugin is called from
            # Kodi UI without any parameters
            self._home_page()

            # Display a warning if libtorrent could not be imported
            if not self.libtorrent_imported:
                kodi.open_dialog(
                    title="Error: libtorrent could not be imported",
                    message="You can still browse and search videos but you"
                            " will not be able to play them.\n"
                            "Please follow the instructions at {}"
                            .format(self.HELP_URL))
