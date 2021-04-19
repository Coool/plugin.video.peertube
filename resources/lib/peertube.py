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

from resources.lib.kodi_utils import debug, get_setting, notif_error


class PeerTube:
    """A class to interact easily with PeerTube instances using REST APIs"""

    def __init__(self, instance, sort, count, video_filter):
        """Constructor

        :param str instance: URL of the PeerTube instance
        :param str sort: sort method to use when listing items
        :param int count: number of items to display
        :param str sort: filter to apply when listing/searching videos
        """
        self.instance = instance

        self.list_settings = {
            "sort": sort,
            "count": count
        }

        # The value "video_filter" is directly retrieved from the settings so
        # it must be converted into one of the expected values by the REST APIs
        if "all-local" in video_filter:
            self.filter = "all-local"
        else:
            self.filter = "local"

    def _request(self, method, url, params=None, data=None):
        """Call a REST API on the instance

        :param str method: REST API method (get, post, put, delete, etc.)
        :param str url: URL of the REST API endpoint relative to the PeerTube
                        instance
        :param dict params: dict of the parameters to send in the request
        :param dict data: dict of the data to send with the request
        :return: the response as JSON data
        :rtype: dict
        """

        # Build the URL of the REST API
        api_url = urljoin("{}/api/v1/".format(self.instance), url)

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
            debug("Error when sending a {} request to {} with params={} and"
                  " data={}".format(method, url, params, data))

            # Report the error to the user with a notification: if the response
            # contains an "error" attribute, use it as error message, otherwise
            # use a default message.
            if "error" in json:
                message = json["error"]
                debug(message)
            else:
                message = ("No details returned by the server. Check the log"
                           " for more information.")
            notif_error(title="Request error", message=message)
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

    def get_video(self, video_id):
        """Get the information of a video

        :param str video_id: ID or UUID of the video
        :return: the information of the video as returned by the REST API
        :rtype: dict
        """

        return self._request(method="GET", url="videos/{}".format(video_id))

    def list_videos(self, start):
        """List the videos in the instance

        :param str start: index of the first video to display
        :return: the list of videos as returned by the REST API
        :rtype: dict
        """
        # Build the parameters that will be sent in the request
        params = self._build_params(filter=self.filter, start=start)

        return self._request(method="GET", url="videos", params=params)

    def search_videos(self, keywords, start):
        """Search for videos on the instance and beyond.

        :param str keywords: keywords to seach for
        :param str start: index of the first video to display
        :return: the videos matching the keywords as returned by the REST API
        :rtype: dict
        """
        # Build the parameters that will be send in the request
        params = self._build_params(search=keywords,
                                    filter=self.filter,
                                    start=start)

        return self._request(method="GET", url="search/videos", params=params)


def list_instances(start):
    """List all the peertube instances from joinpeertube.org

    :param str start: index of the first instance to display
    :return: the list of instances as returned by the REST API
    :rtype: dict
    """
    # URL of the REST API
    api_url = "https://instances.joinpeertube.org/api/v1/instances"
    # Build the parameters that will be sent in the request from the settings
    params = {
        "count": get_setting("items_per_page"),
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
        debug("Error when getting the list of instances with params={}"
              .format(params))

        # Report the error to the user with a notification: use the details of
        # the error if it exists in the response, otherwise use a default
        # message.
        try:
            # Convert the reponse to a list to get the first error whatever its
            # name. Then get the second element in the sublist which contains
            # the details of the error.
            message = list(json["errors"].items())[0][1]["msg"]
            debug(message)
        except KeyError:
            message = ("No details returned by the server. Check the log"
                        " for more information.")
        notif_error(title="Request error", message=message)
        raise exception

    return json
