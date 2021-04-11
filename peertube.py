# -*- coding: utf-8 -*-
"""
    A Kodi add-on to play video hosted on the PeerTube service
    (http://joinpeertube.org/)

    Copyright (C) 2018 Cyrille Bollu
    Copyright (C) 2021 Thomas Bétous

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSE.txt for more information.
"""
import sys

try:
    # Python 3.x
    from urllib.parse import parse_qsl
except ImportError:
    # Python 2.x
    from urlparse import parse_qsl

import AddonSignals # Module exists only in Kodi - pylint: disable=import-error
import requests
from requests.compat import urljoin, urlencode
import xbmc # Kodistubs for Leia is not compatible with python3 / pylint: disable=syntax-error
import xbmcaddon
import xbmcgui # Kodistubs for Leia is not compatible with python3 / pylint: disable=syntax-error
import xbmcplugin

from resources.lib.kodi_utils import (
    debug, get_property, get_setting, notif_error, notif_info, notif_warning,
    open_dialog, set_setting)


class PeertubeAddon():
    """
    Main class of the addon
    """

    # URL of the page which explains how to install libtorrent
    HELP_URL = 'https://link.infini.fr/libtorrent-peertube-kodi'

    def __init__(self, plugin, plugin_id):
        """
        Initialisation of the PeertubeAddon class
        :param plugin, plugin_id: str, int
        """

        # This step must be done first because the logging function requires
        # the name of the add-on
        self.addon_name = xbmcaddon.Addon().getAddonInfo('name')

        # Save addon URL and ID
        self.plugin_url = plugin
        self.plugin_id = plugin_id

        # Select preferred instance by default
        self.selected_inst ='https://{}'\
            .format(get_setting('preferred_instance'))

        # Get the number of videos to show per page
        self.items_per_page = int(get_setting('items_per_page'))

        # Get the video sort method
        self.sort_method = get_setting('video_sort_method')

        # Get the preferred resolution for video
        self.preferred_resolution = get_setting('preferred_resolution')

        # Nothing to play at initialisation
        self.play = 0
        self.torrent_name = ''
        self.torrent_f = ''

        # Get the video filter from the settings that will be used when
        # browsing the videos. The value from the settings is converted into
        # one of the expected values by the REST APIs ("local" or "all-local")
        if 'all-local' in get_setting('video_filter'):
            self.video_filter = 'all-local'
        else:
            self.video_filter = 'local'

        # Check whether libtorrent could be imported by the service. The value
        # of the associated property is retrieved only once and stored in an
        # attribute because libtorrent is imported only once at the beginning
        # of the service (we assume it is not possible to start the add-on
        # before the service)
        self.libtorrent_imported = \
            get_property('libtorrent_imported') == 'True'

    def debug(self, message):
        """Log a debug message

        :param str message: Message to log (will be prefixed with the add-on
        name)
        """
        debug('{0}: {1}'.format(self.addon_name, message))

    def query_peertube(self, req):
        """
        Issue a PeerTube API request and return the results
        :param req: str
        :result data: dict
        """

        # Send the PeerTube REST API request
        self.debug('Issuing request {0}'.format(req))
        response = requests.get(url=req)
        data = response.json()

        # Use Request.raise_for_status() to raise an exception if the HTTP
        # request returned an unsuccessful status code.
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            notif_error(title='Communication error',
                        message='Error when sending request {}'.format(req))
            # If the JSON contains an 'error' key, print it
            error_details = data.get('error')
            if error_details is not None:
                self.debug('Error => "{}"'.format(data['error']))
            raise e

        # Try to get the number of elements in the response
        results_found = data.get('total', None)
        # If the information is available in the response, use it
        if results_found is not None:
            # Return when no results are found
            if results_found == 0:
                self.debug('No result found')
                return None
            else:
                self.debug('Found {0} results'.format(results_found))

        return data

    def create_list(self, lst, data_type, start):
        """
        Create an array of xmbcgui.ListItem's from the lst parameter
        :param lst, data_type, start: dict, str, str
        :result listing: array
        """
        # Create a list for our items.
        listing = []
        for data in lst['data']:

            # Create a list item with a text label
            list_item = xbmcgui.ListItem(label=data['name'])

            if data_type == 'videos':
                # Add thumbnail
                list_item.setArt({
                    'thumb': '{0}/{1}'.format(self.selected_inst,
                                              data['thumbnailPath'])})

                # Set a fanart image for the list item.
                # list_item.setProperty('fanart_image', data['thumb'])

                # Compute media info from item's metadata
                info = {'title': data['name'],
                        'playcount': data['views'],
                        'plotoutline': data['description'],
                        'duration': data['duration']
                        }

                # For videos, add a rating based on likes and dislikes
                if data['likes'] > 0 or data['dislikes'] > 0:
                    info['rating'] = data['likes'] / (
                        data['likes'] + data['dislikes'])

                # Set additional info for the list item.
                list_item.setInfo('video', info)

                # Videos are playable
                list_item.setProperty('IsPlayable', 'true')

                # Build the Kodi URL to play the associated video only with the
                # id of the video. The instance is omitted because the
                # currently selected instance will be used automatically.
                url = self.build_kodi_url({
                        'action': 'play_video',
                        'id': data['uuid']
                        })

            elif data_type == 'instances':
                # TODO: Add a context menu to select instance as preferred
                # Instances are not playable
                list_item.setProperty('IsPlayable', 'false')

                # Set URL to select this instance
                url = self.build_kodi_url({
                        'action': 'select_instance',
                        'url': data['host']
                        })

            # Add our item to the listing as a 3-element tuple.
            listing.append((url, list_item, False))

        # Add a 'Next page' button when there are more data to show
        start = int(start) + self.items_per_page
        if lst['total'] > start:
            list_item = xbmcgui.ListItem(label='Next page ({0})'
                                         .format(start/self.items_per_page))
            url = self.build_kodi_url({
                'action': 'browse_{0}'.format(data_type),
                'start': start})
            listing.append((url, list_item, True))

        return listing

    def get_video_url(self, video_id, instance=None):
        """Find the URL of the video with the best possible quality matching
        user's preferences.

        :param video_id: ID of the torrent linked to the video
        :type video_id: str
        :param instance: PeerTube instance hosting the video (optional)
        :type instance: str
        """

        # If no instance was provided, use the selected one (internal call)
        if instance is None:
            instance = self.selected_inst
        else:
            # If an instance was provided (external call), ensure the URL is
            # prefixed with HTTPS
            if not instance.startswith('https://'):
                instance = 'https://{}'.format(instance)

        # Retrieve the information about the video
        metadata = self.query_peertube(urljoin(instance,
                                               '/api/v1/videos/{}'
                                               .format(video_id)))

        # Depending if WebTorrent is enabled or not, the files corresponding to
        # different resolutions available for a video may be stored in "files"
        # or "streamingPlaylists[].files". Note that "files" will always exist
        # in the response but may be empty.
        if len(metadata['files']) != 0:
            files = metadata['files']
        else:
            files = metadata['streamingPlaylists'][0]['files']

        self.debug(
            'Looking for the best resolution matching the user preferences')

        current_res = 0
        higher_res = -1
        torrent_url = ''

        for f in files:
            # Get the resolution
            res = f['resolution']['id']
            if res == self.preferred_resolution:
                # Stop directly when we find the exact same resolution as the
                # user's preferred one
                self.debug('Found video with preferred resolution')
                torrent_url = f['torrentUrl']
                break
            elif res < self.preferred_resolution and res > current_res:
                # Otherwise, try to find the best one just below the user's
                # preferred one
                self.debug('Found video with good lower resolution'
                           '({0})'.format(f['resolution']['label']))
                torrent_url = f['torrentUrl']
                current_res = res
            elif (res > self.preferred_resolution
                    and (res < higher_res or higher_res == -1)):
                # In the worst case, we'll take the one just above the user's
                # preferred one
                self.debug('Saving video with higher resolution ({0})'
                           'as a possible alternative'
                           .format(f['resolution']['label']))
                backup_url = f['torrentUrl']
                higher_res = res

        # When we didn't find a resolution equal or lower than the user's
        # preferred one, use the resolution just above the preferred one
        if not torrent_url:
            self.debug('Using video with higher resolution as alternative')
            torrent_url = backup_url

        return torrent_url

    def build_video_rest_api_request(self, search, start):
        """Build the URL of an HTTP request using the PeerTube videos REST API.

        The same function is used for browsing and searching videos.

        :param search: keywords to search
        :type search: string
        :param start: offset
        :type start: int
        :return: the URL of the request
        :rtype: str

        Didn't yet find a correct way to do a search with a filter set to
        local. Then if a search value is given it won't filter on local
        """

        # Common parameters of the request
        params = {
            'count': self.items_per_page,
            'start': start,
            'sort': self.sort_method
        }

        # Depending on the type of request (search or list videos), add
        # specific parameters and define the API to use
        if search is None:
            # Video API does not provide "search" but provides "filter" so add
            # it to the parameters
            params.update({'filter': self.video_filter})
            api_url = '/api/v1/videos'
        else:
            # Search API does not provide "filter" but provides "search" so add
            # it to the parameters
            params.update({'search': search})
            api_url = '/api/v1/search/videos'

        # Build the full URL of the request (instance + API + parameters)
        req = '{0}?{1}'.format(urljoin(self.selected_inst, api_url),
                               urlencode(params))

        return req

    def build_browse_instances_rest_api_request(self, start):
        """Build the URL of an HTTP request using the PeerTube REST API to
        browse the PeerTube instances.

        :param start: offset
        :type start: int
        :return: the URL of the request
        :rtype: str
        """

        # Create the parameters of the request
        params = {
            'count': self.items_per_page,
            'start': start
        }

        # Join the base URL with the REST API and the parameters
        req = 'https://instances.joinpeertube.org/api/v1/instances?{0}'\
            .format(urlencode(params))

        return req

    def search_videos(self, start):
        """
        Function to search for videos on a PeerTube instance and navigate
        in the results

        :param start: string
        """

        # Show a 'Search videos' dialog
        search = xbmcgui.Dialog().input(
            heading='Search videos on {}'.format(self.selected_inst),
            type=xbmcgui.INPUT_ALPHANUM)

        # Go back to main menu when user cancels
        if not search:
            return

        # Create the PeerTube REST API request for searching videos
        req = self.build_video_rest_api_request(search, start)

        # Send the query
        results = self.query_peertube(req)

        # Exit directly when no result is found
        if not results:
            notif_warning(title='No videos found',
                          message='No videos found matching the query.')
            return

        # Create array of xmbcgui.ListItem's
        listing = self.create_list(results, 'videos', start)

        # Add our listing to Kodi.
        xbmcplugin.addDirectoryItems(self.plugin_id, listing, len(listing))
        xbmcplugin.endOfDirectory(self.plugin_id)

    def browse_videos(self, start):
        """
        Function to navigate through all the video published by a PeerTube
        instance

        :param start: string
        """

        # Create the PeerTube REST API request for listing videos
        req = self.build_video_rest_api_request(None, start)

        # Send the query
        results = self.query_peertube(req)

        # Create array of xmbcgui.ListItem's
        listing = self.create_list(results, 'videos', start)

        # Add our listing to Kodi.
        xbmcplugin.addDirectoryItems(self.plugin_id, listing, len(listing))
        xbmcplugin.endOfDirectory(self.plugin_id)

    def browse_instances(self, start):
        """
        Function to navigate through all PeerTube instances
        :param start: str
        """

        # Create the PeerTube REST API request for browsing PeerTube instances
        req = self.build_browse_instances_rest_api_request(start)

        # Send the query
        results = self.query_peertube(req)

        # Create array of xmbcgui.ListItem's
        listing = self.create_list(results, 'instances', start)

        # Add our listing to Kodi.
        xbmcplugin.addDirectoryItems(self.plugin_id, listing, len(listing))
        xbmcplugin.endOfDirectory(self.plugin_id)

    def play_video_continue(self, data):
        """
        Callback function to let the play_video function resume when the
        PeertubeDownloader has downloaded all the torrent's metadata

        :param data: dict
        """

        self.debug(
            'Received metadata_downloaded signal, will start playing media')
        self.play = 1
        self.torrent_f = data['file']

    def play_video(self, torrent_url):
        """
        Start the torrent's download and play it while being downloaded
        :param torrent_url: str
        """
        # If libtorrent could not be imported, display a message and do not try
        # download nor play the video as it will fail.
        if not self.libtorrent_imported:
            open_dialog(title='Error: libtorrent could not be imported',
                        message='PeerTube cannot play videos without'
                                ' libtorrent.\nPlease follow the instructions'
                                ' at {}'.format(self.HELP_URL))
            return

        self.debug('Starting torrent download ({0})'.format(torrent_url))

        # Start a downloader thread
        AddonSignals.sendSignal('start_download', {'url': torrent_url})

        # Wait until the PeerTubeDownloader has downloaded all the torrent's
        # metadata
        AddonSignals.registerSlot('plugin.video.peertube',
                                  'metadata_downloaded',
                                  self.play_video_continue)
        timeout = 0
        while self.play == 0 and timeout < 10:
            xbmc.sleep(1000)
            timeout += 1

        # Abort in case of timeout
        if timeout == 10:
            notif_error(title='Download timeout',
                        message='Timeout fetching {}'.format(torrent_url))
            return
        else:
            # Wait a little before starting playing the torrent
            xbmc.sleep(3000)

        # Pass the item to the Kodi player for actual playback.
        self.debug('Starting video playback ({0})'.format(torrent_url))
        play_item = xbmcgui.ListItem(path=self.torrent_f)
        xbmcplugin.setResolvedUrl(self.plugin_id, True, listitem=play_item)

    def select_instance(self, instance):
        """
        Change currently selected instance to 'instance' parameter
        :param instance: str
        """

        # Update the object attribute even though it is not used currently but
        # it may be useful in case reuselanguageinvoker is enabled.
        self.selected_inst = 'https://{}'.format(instance)

        # Update the preferred instance in the settings so that this choice is
        # reused on the next run and the next call of the add-on
        set_setting('preferred_instance', instance)

        # Notify the user and log the event
        message = '{0} is now the selected instance'.format(self.selected_inst)
        notif_info(title='Current instance changed',
                   message=message)
        self.debug(message)

    def build_kodi_url(self, parameters):
        """Build a Kodi URL based on the parameters.

        :param parameters: dict containing all the parameters that will be
        encoded in the URL
        """

        return '{0}?{1}'.format(self.plugin_url, urlencode(parameters))

    def main_menu(self):
        """
        Addon's main menu
        """

        # Create a list for our items.
        listing = []

        # 1st menu entry
        list_item = xbmcgui.ListItem(label='Browse selected instance')
        url = self.build_kodi_url({'action': 'browse_videos', 'start': 0})
        listing.append((url, list_item, True))

        # 2nd menu entry
        list_item = xbmcgui.ListItem(label='Search on selected instance')
        url = self.build_kodi_url({'action': 'search_videos', 'start': 0})
        listing.append((url, list_item, True))

        # 3rd menu entry
        list_item = xbmcgui.ListItem(label='Select other instance')
        url = self.build_kodi_url({'action': 'browse_instances', 'start': 0})
        listing.append((url, list_item, True))

        # Add our listing to Kodi.
        xbmcplugin.addDirectoryItems(self.plugin_id, listing, len(listing))

        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self.plugin_id)

    def router(self, paramstring):
        """
        Router function that calls other functions
        depending on the provided paramstring
        :param paramstring: dict
        """

        # Parse a URL-encoded paramstring to the dictionary of
        # {<parameter>: <value>} elements
        params = dict(parse_qsl(paramstring[1:]))

        # Check the parameters passed to the plugin
        if params:
            action = params['action']
            if action == 'browse_videos':
                # Browse videos on selected instance
                self.browse_videos(params['start'])
            elif action == 'search_videos':
                # Search for videos on selected instance
                self.search_videos(params['start'])
            elif action == 'browse_instances':
                # Browse peerTube instances
                self.browse_instances(params['start'])
            elif action == 'play_video':
                # This action comes with the id of the video to play as
                # parameter. The instance may also be in the parameters. Use
                # these parameters to retrieve the complete URL (containing the
                # resolution).
                url = self.get_video_url(instance=params.get('instance'),
                                         video_id=params.get('id'))
                # Play the video using the URL
                self.play_video(url)
            elif action == 'select_instance':
                self.select_instance(params['url'])
        else:
            # Display the addon's main menu when the plugin is called from
            # Kodi UI without any parameters
            self.main_menu()

            # Display a warning if libtorrent could not be imported
            if not self.libtorrent_imported:
                open_dialog(title='Error: libtorrent could not be imported',
                            message='You can still browse and search videos'
                                    ' but you will not be able to play them.\n'
                                    'Please follow the instructions at {}'
                                    .format(self.HELP_URL))

if __name__ == '__main__':

    # Initialise addon
    addon = PeertubeAddon(sys.argv[0], int(sys.argv[1]))
    # Call the router function and pass the plugin call parameters to it.
    addon.router(sys.argv[2])
