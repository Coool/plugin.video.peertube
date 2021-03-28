# A Kodi Addon to play video hosted on the peertube service (http://joinpeertube.org/)
#
# TODO: - Delete downloaded files by default
#       - Allow people to choose if they want to keep their download after watching?
#       - Do sanity checks on received data
#       - Handle languages better (with .po files)
#       - Get the best quality torrent given settings and/or available bandwidth
#         See how they do that in the peerTube client's code
import sys

try:
    # Python 3.x
    from urllib.parse import parse_qsl
except ImportError:
    # Python 2.x
    from urlparse import parse_qsl

import AddonSignals
import requests
from requests.compat import urljoin, urlencode
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs


class PeertubeAddon():
    """
    Main class of the addon
    """

    def __init__(self, plugin, plugin_id):
        """
        Initialisation of the PeertubeAddon class
        :param plugin, plugin_id: str, int
        :return: None
        """

        # These 2 steps must be done first since the logging function requires
        # the add-on name
        # Get an Addon instance
        addon = xbmcaddon.Addon()
        # Get the add-on name
        self.addon_name = addon.getAddonInfo('name')

        self.debug('Initialising')

        # Save addon URL and ID
        self.plugin_url = plugin
        self.plugin_id = plugin_id

        # Select preferred instance by default
        self.selected_inst = addon.getSetting('preferred_instance')

        # Get the number of videos to show per page
        self.items_per_page = int(addon.getSetting('items_per_page'))

        # Get the video sort method
        self.sort_method = addon.getSetting('video_sort_method')

        # Get the preferred resolution for video
        self.preferred_resolution = addon.getSetting('preferred_resolution')

        # Nothing to play at initialisation
        self.play = 0
        self.torrent_name = ''

        # Get the video filter from the settings that will be used when
        # browsing the videos. The value from the settings is converted into
        # one of the expected values by the REST APIs ("local" or "all-local")
        if 'all-local' in addon.getSetting('video_filter'):
            self.video_filter = 'all-local'
        else:
            self.video_filter = 'local'

        return None

    def debug(self, message):
        """Log a message in Kodi's log with the level xbmc.LOGDEBUG

        :param message: Message to log
        :type message: str
        """
        xbmc.log('{0}: {1}'.format(self.addon_name, message), xbmc.LOGDEBUG)

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
            xbmcgui.Dialog().notification('Communication error',
                                          'Error during request on {0}'
                                          .format(self.selected_inst),
                                          xbmcgui.NOTIFICATION_ERROR)
            # Print the JSON as it may contain an 'error' key with the details
            # of the error
            self.debug('Error => "{}"'.format(data['error']))
            raise e

        # Return when no results are found
        if data['total'] == 0:
            self.debug('No result found')
            return None
        else:
            self.debug('Found {0} results'.format(data['total']))

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
                list_item.setArt({'thumb': self.selected_inst + '/' + data['thumbnailPath']})

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
                    info['rating'] = data['likes']/(data['likes'] + data['dislikes'])

                # Set additional info for the list item.
                list_item.setInfo('video', info)

                # Videos are playable
                list_item.setProperty('IsPlayable', 'true')

                # Find the URL of the best possible video matching user's preferences
                # TODO: Error handling
                current_res = 0
                higher_res = -1
                torrent_url = ''
                response = requests.get(self.selected_inst + '/api/v1/videos/'
                                        + data['uuid'])
                metadata = response.json()
                self.debug('Looking for the best possible video quality matching user preferences')
                for f in metadata['files']:
                    # Get file resolution
                    res = f['resolution']['id']
                    if res == self.preferred_resolution:
                        # Stop directly, when we find the exact same resolution as the user's preferred one
                        self.debug('Found video with preferred resolution')
                        torrent_url = f['torrentUrl']
                        break
                    elif res < self.preferred_resolution and res > current_res:
                        # Else, try to find the best one just below the user's preferred one
                        self.debug('Found video with good lower resolution'
                                   '({0})'.format(f['resolution']['label']))
                        torrent_url = f['torrentUrl']
                        current_res = res
                    elif res > self.preferred_resolution and (res < higher_res or higher_res == -1):
                        # In the worst case, we'll take the one just above the user's preferred one
                        self.debug('Saving video with higher resolution ({0})'
                                   'as a possible alternative'
                                   .format(f['resolution']['label']))
                        backup_url = f['torrentUrl']
                        higher_res = res

                # Use smallest file with an higher resolution, when we didn't find a resolution equal or
                # lower than the user's preferred one
                if not torrent_url:
                    self.debug('Using video with higher resolution as alternative')
                    torrent_url = backup_url

                # Compose the correct URL for Kodi
                url = self.build_kodi_url({
                        'action': 'play_video',
                        'url': torrent_url
                        })

            elif data_type == 'instances':
                # TODO: Add a context menu to select instance as preferred instance
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
        req = '{0}?{1}'.format('https://instances.joinpeertube.org/api/v1/instances',
                               urlencode(params))

        return req

    def search_videos(self, start):
        """
        Function to search for videos on a PeerTube instance and navigate in the results
        :param start: string
        :result: None
        """

        # Show a 'Search videos' dialog
        search = xbmcgui.Dialog().input(heading='Search videos on ' + self.selected_inst, type=xbmcgui.INPUT_ALPHANUM)

        # Go back to main menu when user cancels
        if not search:
            return None

        # Create the PeerTube REST API request for searching videos
        req = self.build_video_rest_api_request(search, start)

        # Send the query
        results = self.query_peertube(req)

        # Exit directly when no result is found
        if not results:
            xbmcgui.Dialog().notification('No videos found', 'No videos found matching query', xbmcgui.NOTIFICATION_WARNING)
            return None

        # Create array of xmbcgui.ListItem's
        listing = self.create_list(results, 'videos', start)

        # Add our listing to Kodi.
        xbmcplugin.addDirectoryItems(self.plugin_id, listing, len(listing))
        xbmcplugin.endOfDirectory(self.plugin_id)

        return None

    def browse_videos(self, start):
        """
        Function to navigate through all the video published by a PeerTube instance
        :param start: string
        :return: None
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

        return None

    def browse_instances(self, start):
        """
        Function to navigate through all PeerTube instances
        :param start: str
        :return: None
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

        return None

    def play_video_continue(self, data):
        """
        Callback function to let the play_video function resume when the PeertubeDownloader
            has downloaded all the torrent's metadata
        :param data: dict
        :return: None
        """

        self.debug('Received metadata_downloaded signal, will start playing media')
        self.play = 1
        self.torrent_f = data['file']

        return None

    def play_video(self, torrent_url):
        """
        Start the torrent's download and play it while being downloaded
        :param torrent_url: str
        :return: None
        """

        self.debug('Starting torrent download ({0})'.format(torrent_url))

        # Start a downloader thread
        AddonSignals.sendSignal('start_download', {'url': torrent_url})

        # Wait until the PeerTubeDownloader has downloaded all the torrent's metadata
        AddonSignals.registerSlot('plugin.video.peertube', 'metadata_downloaded', self.play_video_continue)
        timeout = 0
        while self.play == 0 and timeout < 10:
            xbmc.sleep(1000)
            timeout += 1

        # Abort in case of timeout
        if timeout == 10:
            xbmcgui.Dialog().notification('Download timeout', 'Timeout fetching ' + torrent_url, xbmcgui.NOTIFICATION_ERROR)
            return None
        else:
            # Wait a little before starting playing the torrent
            xbmc.sleep(3000)

        # Pass the item to the Kodi player for actual playback.
        self.debug('Starting video playback ({0})'.format(torrent_url))
        play_item = xbmcgui.ListItem(path=self.torrent_f)
        xbmcplugin.setResolvedUrl(self.plugin_id, True, listitem=play_item)

        return None

    def select_instance(self, instance):
        """
        Change currently selected instance to 'instance' parameter
        :param instance: str
        :return: None
        """

        self.selected_inst = 'https://' + instance
        xbmcgui.Dialog().notification('Current instance changed', 'Changed current instance to {0}'.format(self.selected_inst), xbmcgui.NOTIFICATION_INFO)
        self.debug('Changing currently selected instance to {0}'
                   .format(self.selected_inst))

        return None

    def build_kodi_url(self, parameters):
        """Build a Kodi URL based on the parameters.

        :param parameters: dict containing all the parameters that will be
        encoded in the URL
        """

        return '{0}?{1}'.format(self.plugin_url, urlencode(parameters))

    def main_menu(self):
        """
        Addon's main menu
        :param: None
        :return: None
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

        return None

    def router(self, paramstring):
        """
        Router function that calls other functions
        depending on the provided paramstring
        :param paramstring: dict
        :return: None
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
                # Play video from provided URL.
                self.play_video(params['url'])
            elif action == 'select_instance':
                self.select_instance(params['url'])
        else:
            # Display the addon's main menu when the plugin is called from Kodi UI without any parameters
            self.main_menu()

        return None


if __name__ == '__main__':

    # Initialise addon
    addon = PeertubeAddon(sys.argv[0], int(sys.argv[1]))
    # Call the router function and pass the plugin call parameters to it.
    addon.router(sys.argv[2])
