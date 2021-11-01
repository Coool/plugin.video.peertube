# -*- coding: utf-8 -*-
"""
    Main class used by the add-on

    Copyright (C) 2018 Cyrille Bollu
    Copyright (C) 2021 Thomas Bétous

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSE.txt for more information.
"""
import json
import os.path
from urllib.parse import quote_plus

from resources.lib.kodi_utils import kodi
from resources.lib.peertube import PeerTube, list_instances

import AddonSignals
import xbmcvfs

class PeerTubeAddon():
    """
    Main class used by the add-on
    """

    def __init__(self):
        """Initialize parameters and create a PeerTube instance"""

        # Get the number of items to show per page
        self.items_per_page = int(kodi.get_setting("items_per_page"))

        # Get the preferred resolution for video
        self.preferred_resolution = \
            int(kodi.get_setting("preferred_resolution"))

        # Create a PeerTube object to send requests: settings which are used
        # only by this object are directly retrieved from the settings
        self.peertube = PeerTube(
            instance=kodi.get_setting("preferred_instance"),
            count=self.items_per_page)

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
            description = kodi.get_string(30404).format(
                data["shortDescription"],
                data["totalLocalVideos"],
                data["totalUsers"]
            )

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
            # Note: the type of video (live or not) is available in "response"
            # but this information is ignored here so that the "play_video"
            # action is the same whatever the type of the video. The goal is to
            # allow external users of the API to play a video only with its ID
            # without knowing its type.
            # The information about the type of the video will anyway be
            # available in the response used to get the URL of a video so this
            # solution does not impact the performance.

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
            next_page = (next_index // self.items_per_page) + 1
            total_pages = (total // self.items_per_page) + 1

            next_page_item = kodi.generate_item_info(
                name="{} ({}/{})".format(kodi.get_string(30405),
                                         next_page,
                                         total_pages),
                url=url
            )

            return next_page_item

    def _get_url_with_resolution(self, list_of_url_and_resolutions):
        """
        Build the URL of the video 

        PeerTube creates 1 URL for each resolution so we browse all the
        available resolutions and select the best possible quality matching
        user's preferences.
        If the preferred resolution cannot be found, the one just below will
        be used. If it is not possible the one just above we will be used.

        :param list list_of_url_and_resolutions: list of dict containing 2 keys:
        the resolution and the associated URL.
        :return: the URL matching the selected resolution
        :rtype: str
        """

        # Find the best resolution matching user's preferences
        current_resolution = 0
        higher_resolution = -1
        url = None
        for video in list_of_url_and_resolutions:
            # Get the resolution
            resolution = video.get("resolution")
            if resolution == self.preferred_resolution:
                # Stop directly when we find the exact same resolution as the
                # user's preferred one
                kodi.debug("Found video with preferred resolution ({})"
                           .format(self.preferred_resolution))
                return video["url"]
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
        if url is None:
            kodi.debug("Using video with higher resolution as alternative ({})"
                        .format(higher_resolution))
            url = backup_url

        return url

    def _home_page(self):
        """Display the items of the home page of the add-on"""

        home_page_items = [
            kodi.generate_item_info(
                name=kodi.get_string(30406),
                url=kodi.build_kodi_url({"action": "browse_videos","start": 0})
            ),
            kodi.generate_item_info(
                name=kodi.get_string(30407),
                url=kodi.build_kodi_url({"action": "search_videos","start": 0})
            ),
            kodi.generate_item_info(
                name=kodi.get_string(30408),
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
            title=kodi.get_string(30409).format(self.peertube.instance))

        # Go back to the home page when the user cancels or didn't enter any
        # string
        if not keywords:
            return

        # Use the API to search for videos
        results = self.peertube.search_videos(keywords, start)

        # Exit directly when no result is found
        if not results:
            kodi.notif_warning(
                title=kodi.get_string(30410),
                message=kodi.get_string(30411).format(keywords))
            return

        # Extract the information of each video from the API response
        list_of_videos = self._create_list_of_videos(results, start)

        # Create the associated items in Kodi
        kodi.create_items_in_ui(list_of_videos)

    def _play_video(self, video_id, instance):
        """
        Get the required information and play the video

        :param str video_id: ID of the torrent linked with the video
        :param str instance: PeerTube instance hosting the video
        """

        # Get the information of the video including the different resolutions
        # available
        video_info = self.peertube.get_video_info(video_id, instance)

        # Check if the video is a live (Kodi can play live videos (.m3u8) out of
        # the box whereas torrents must first be downloaded)
        if video_info["is_live"]:
            kodi.play(video_info["files"][0]["url"])
        else:
            # Get the URL of the file which resolution is the closest to the
            # user's preferences
            url = self._get_url_with_resolution(video_info["files"])

            self._download_and_play(url, int(video_info["duration"]))

    def _download_and_play(self, torrent_url, duration):
        """
        Start the torrent's download and play it while being downloaded

        The user configures in the settings the number of seconds of the file
        that must be downloaded before the playback starts.

        :param str torrent_url: URL of the torrent file to download and play
        :param int duration: duration of the video behind the URL in seconds
        """

        kodi.debug("Starting torrent download ({})".format(torrent_url))

        # Download the torrent using vfs.libtorrent: the torrent URL must be
        # URL-encoded to be correctly read by vfs.libtorrent
        vfs_url = "torrent://{}".format(quote_plus(torrent_url))
        torrent = xbmcvfs.File(vfs_url)

        # Get information about the torrent
        torrent_info = json.loads(torrent.read())

        if torrent_info["nb_files"] > 1:
            kodi.warning("There are more than 1 file in {} but only the"
                         " first one will be played.".format(torrent_url))

        # Compute the amount of the file that we want to wait to be downloaded
        # before playing the video. It is based on the number of seconds
        # configured by the user and the total duration of the video.
        initial_chunk_proportion = (int(kodi.get_setting("initial_wait_time"))
                                    * 100. / duration)
        # TODO: Remove the dot in 100. in python 3? Or keep it to suport both
        #       python2 and python3

        # Download the file, waiting for "initial_chunk_proportion" % of the
        # file to be downloaded (seek() takes only integers so the proportion
        # is multiplied to have more granularity.)
        if(torrent.seek(initial_chunk_proportion*100, 0) != -1):

            # Build the path of the downloaded file
            torrent_file = os.path.join(torrent_info["save_path"],
                                             torrent_info["files"][0]["path"])

            # Send information about the torrent to the service so that it can
            # control the torrent later(e.g. pause the download when the
            # playback stops)
            AddonSignals.sendSignal("torrent_information",
                {
                    "run_url": kodi.build_kodi_url(kodi.get_run_parameters()),
                    "torrent_url": vfs_url
                }
            )

            # Play the file
            kodi.debug("Starting video playback of {}".format(torrent_file))
            kodi.play(torrent_file)

        else:
            kodi.notif_error(title=kodi.get_string(30421),
                             message=kodi.get_string(30422))

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
        kodi.notif_info(
            title=kodi.get_string(30418),
            message=kodi.get_string(30419).format(self.peertube.instance))

        kodi.debug("{} is now the selected instance"
                   .format(self.peertube.instance))

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
                self._play_video(instance=params.get("instance"),
                                 video_id=params.get("id"))
            elif action == "select_instance":
                # Set the selected instance as the preferred instance
                self._select_instance(params["url"])
        else:
            # Display the addon's main menu when the plugin is called from
            # Kodi UI without any parameters
            self._home_page()