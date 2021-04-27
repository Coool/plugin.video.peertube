# -*- coding: utf-8 -*-
"""
    PeerTube related classes and functions

    Copyright (C) 2018 Cyrille Bollu
    Copyright (C) 2021 Thomas Bétous

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSE.txt for more information.
"""
import requests
from requests.compat import urljoin

from resources.lib.kodi_utils import kodi


class PeerTube:
    """A class to interact easily with PeerTube instances using REST APIs"""

    def __init__(self, instance, count):
        """Initialize the parameters that will be used in the requests

        Some values are retrieved directly from the settings, others come as
        arguments because they are used somewhere else in the add-on.

        :param str instance: URL of the PeerTube instance
        :param int count: number of items to display
        """
        self.set_instance(instance)

        self.list_settings = {
            "sort": self._get_sort_method(),
            "count": count
        }

        self.filter = self._get_video_filter()

    def _request(self, method, url, params=None, data=None, instance=None):
        """Call a REST API on the instance

        :param str method: REST API method (get, post, put, delete, etc.)
        :param str url: URL of the REST API endpoint relative to the PeerTube
                        instance
        :param dict params: dict of the parameters to send in the request
        :param dict data: dict of the data to send with the request
        :param str instance: URL of the instance hosting the video. The
        configured instance will be used if empty.
        :return: the response as JSON data
        :rtype: dict
        """
        # If no instance was provided, use the one from the settings (which was
        # used when instantianting this object)
        if instance is None:
            instance = self.instance
        else:
            # If an instance was provided ensure the URL is prefixed with HTTPS
            if not instance.startswith("https://"):
                instance = "https://{}".format(instance)

        # Build the URL of the REST API
        api_url = urljoin("{}/api/v1/".format(instance), url)

        # Send a request with a time-out of 5 seconds
        response = requests.request(method=method,
                                    url=api_url,
                                    timeout=5,
                                    params=params,
                                    data=data)

        json = response.json()

        # Use Request.raise_for_status() to raise an exception if the HTTP
        # request didn't succeed
        try:
            response.raise_for_status()
        except requests.HTTPError as exception:
            # Print in Kodi's log some information about the request
            kodi.debug("Error when sending a {} request to {} with params={}"
                       " and data={}".format(method, url, params, data))

            # Report the error to the user with a notification: if the response
            # contains an "error" attribute, use it as error message, otherwise
            # use a default message.
            if "error" in json:
                message = json["error"]
                kodi.debug(message)
            else:
                message = ("No details returned by the server. Check the log"
                           " for more information.")
            kodi.notif_error(title="Request error", message=message)
            raise exception

        return json

    def _build_params(self, **kwargs):
        """Build the parameters to send with a request from the common settings

        This method returns a dictionnary containing the common settings from
        self.list_settings plus the arguments passed to this function. The keys
        in the dictionnary will have the same name as the arguments passed to
        this function.

        :return: the common settings plus other parameters
        :rtype: dict
        """
        # Initialize the dict from the common settings (the common settings are
        # copied otherwise any modification will also impact the attribute).
        params = self.list_settings.copy()

        # Add all the arguments to the dict
        for param in kwargs:
            params[param] = kwargs[param]

        return params

    def _get_video_filter(self):
        """Get the video filter from the settings

        The value of the associated setting is localized so a list is used to
        get the value expected by the API based on the index of the value used.

        :return: value of the video_filter setting
        :rtype: str
        """

        filters = ["local", "all-local"]
        return filters[int(kodi.get_setting("video_filter"))]

    def _get_sort_method(self):
        """Get the sort method from the settings

        The value of the associated setting is localized so a list is used to
        get the value expected by the API based on the index of the value used.

        :return: value of the video_sort_method setting
        :rtype: str
        """

        sort_methods = ["likes", "views"]
        return sort_methods[int(kodi.get_setting("video_sort_method"))]

    def get_video_urls(self, video_id, instance=None):
        """Return the URLs of a video

        PeerTube creates 1 URL for each resolution of a video so this method
        returns a list of URL/resolution pairs. In the case of a live video,
        only an URL will be returned (no resolution).

        :param str video_id: ID or UUID of the video
        :param str instance: URL of the instance hosting the video. The
        configured instance will be used if empty.
        :return: pair(s) of URL/resolution
        :rtype: generator
        """
        # Get the information about the video
        metadata = self._request(method="GET",
                                 url="videos/{}".format(video_id),
                                 instance=instance)

        if metadata["isLive"]:
            # When the video is a live, yield the unique playlist URL (there is
            # no resolution in this case)
            yield {
                "url": metadata['streamingPlaylists'][0]['playlistUrl'],
            }
        else:
            # For non live videos, the files corresponding to different
            # resolutions available for a video may be stored in "files" or
            # "streamingPlaylists[].files" depending if WebTorrent is enabled
            # or not. Note that "files" will always exist in the response but
            # may be empty so len() must be used.
            if len(metadata["files"]) != 0:
                files = metadata["files"]
            else:
                files = metadata["streamingPlaylists"][0]["files"]

            for file in files:
                yield {
                    "resolution": int(file["resolution"]["id"]),
                    "url": file["torrentUrl"],
                }

    def list_videos(self, start):
        """List the videos in the instance

        :param int start: index of the first video to display
        :return: the list of videos as returned by the REST API
        :rtype: dict
        """
        # Build the parameters that will be sent in the request
        params = self._build_params(filter=self.filter, start=start)

        return self._request(method="GET", url="videos", params=params)

    def search_videos(self, keywords, start):
        """Search for videos on the instance and beyond.

        :param str keywords: keywords to seach for
        :param int start: index of the first video to display
        :return: the videos matching the keywords as returned by the REST API
        :rtype: dict
        """
        # Build the parameters that will be send in the request
        params = self._build_params(search=keywords,
                                    filter=self.filter,
                                    start=start)

        return self._request(method="GET", url="search/videos", params=params)

    def set_instance(self, instance):
        """Set the URL of the current instance with the right format

        The URL of the instance may not be prefixed with HTTPS, for instance:
        * in the settings the URL does not use this prefix to allow the user to
          change it easily
        * the URL from the list of instances is not prefixed
        This method is used to ensure the URL is correctly prefixed with HTTPS

        :param str instance: URL of the instance
        """
        if not instance.startswith("https://"):
                instance = "https://{}".format(instance)

        self.instance = instance


def list_instances(start):
    """List all the peertube instances from joinpeertube.org

    :param int start: index of the first instance to display
    :return: the list of instances as returned by the REST API
    :rtype: dict
    """
    # URL of the REST API
    api_url = "https://instances.joinpeertube.org/api/v1/instances"
    # Build the parameters that will be sent in the request from the settings
    params = {
        "count": kodi.get_setting("items_per_page"),
        "start": start
    }

    # Send a request with a time-out of 5 seconds
    response = requests.get(url=api_url, timeout=5, params=params)

    json = response.json()

    # Use Request.raise_for_status() to raise an exception if the HTTP
    # request didn't succeed
    try:
        response.raise_for_status()
    except requests.HTTPError as exception:
        # Print in Kodi's log some information about the request
        kodi.debug("Error when getting the list of instances with params={}"
                   .format(params))

        # Report the error to the user with a notification: use the details of
        # the error if it exists in the response, otherwise use a default
        # message.
        try:
            # Convert the reponse to a list to get the first error whatever its
            # name. Then get the second element in the sublist which contains
            # the details of the error.
            message = list(json["errors"].items())[0][1]["msg"]
            kodi.debug(message)
        except KeyError:
            message = ("No details returned by the server. Check the log"
                        " for more information.")
        kodi.notif_error(title="Request error", message=message)
        raise exception

    return json
