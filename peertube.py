# A Kodi Addon to play video hosted on the peertube service (http://joinpeertube.org/)
#
# This is just a Proof-Of-Concept atm but I hope I will be able to make it evolve to
# something worth using.
#
# TODO: - Delete downloaded files by default
#       - Allow people to choose if they want to keep their download after watching?
#       - Make sure we are seeding when downloading and watching
#       - When downloaded torrents are kept, do we want to seed them all the time,
#         or only when the addon is running, or only when kodi is playing one,...?

import libtorrent
import time, sys
import urllib2, json
from urlparse import parse_qsl
import xbmcgui, xbmcplugin

# Get the plugin url in plugin:// notation.
__url__ = sys.argv[0]
# Get the plugin handle as an integer number.
__handle__ = int(sys.argv[1])

def list_videos():
    """
    Create the list of playable videos in the Kodi interface.
    :param: None
    :return: None
    """

    # List of videos.
    # TODO: Get this list from an instance, several instances, or the result from a search
    videos = ['https://peertube.cpy.re/api/v1/videos/5a6133b8-3e0c-40dc-b859-69d0540c3fe5',
             'https://peertube.cpy.re/api/v1/videos/a8ea95b8-0396-49a6-8f30-e25e25fb2828']

    # Create a list for our items.
    listing = []
    for video in videos:
        # Get video metadata
        resp = urllib2.urlopen(video)
        metadata = json.load(resp)

        # Create a list item with a text label
        # TODO: Get video thumbnail and add it to list_item
        list_item = xbmcgui.ListItem(label=metadata['name'])
        # list_item = xbmcgui.ListItem(label=metadata['name'], thumbnailImage=video['thumb'])

        # Set a fanart image for the list item.
        #list_item.setProperty('fanart_image', video['thumb'])

        # Set additional info for the list item.
        # TODO: Manage multiple tags
        # TODO: Add video's description to the list_item's info
        list_item.setInfo('video', {'title': metadata['name'], 'tags': metadata['tags'][0]})

        # Set 'IsPlayable' property to 'true'.
        # This is mandatory for playable items!
        list_item.setProperty('IsPlayable', 'true')


        # Find smallest file's torrentUrl
        # TODO: Get the best quality torrent given settings and/or available bandwidth
        #       See how they do that in the peerTube client's code 
        min_size = -1
        for f in metadata['files']:
          if f['size'] < min_size or min_size == -1:
            # TODO: See if using magnet wouldn't be better
            #       Atm, files are saved by their filename (<uuid>.mp4) while I think
            #       that they are saved by their (dn) name when using magnet links 
            #magnet = f['magnetUri']
            magnet = f['torrentUrl']

        # Add our item to the listing as a 3-element tuple.
        url = '{0}?action=play&url={1}'.format(__url__, magnet)
        listing.append((url, list_item, False))

    # Add our listing to Kodi.
    xbmcplugin.addDirectoryItems(__handle__, listing, len(listing))
    xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    xbmcplugin.endOfDirectory(__handle__)

def play_video(url):
    """
    Play the video at the provided url
    :param url: str
    :return: None
    """

    # Open bitTorrent session
    ses = libtorrent.session()
    ses.listen_on(6881, 6891)

    # Add torrent
    fpath = xbmc.translatePath('special://temp')
    h = ses.add_torrent({'url': url, 'save_path': fpath})

    # Set sequential mode to allow watching while downloading
    h.set_sequential_download(True)
 
    # Wait a little so that file is already partialy downloaded
    # TODO: The download should be run in the background
    #       because at the moment it stops when kodi starts playing the video
    #       This will probably need a service add on
    while True:
      time.sleep(1)
      s = h.status()
      if (s.state >= 3):
        break
    time.sleep(10)

    # Pass the item to the Kodi player.
    path = fpath + h.name()
    play_item = xbmcgui.ListItem(path=path)
    xbmcplugin.setResolvedUrl(__handle__, True, listitem=play_item)

def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring
    :param paramstring:
    :return:
    """
    # Parse a URL-encoded paramstring to the dictionary of
    # {<parameter>: <value>} elements
    params = dict(parse_qsl(paramstring[1:]))
    # Check the parameters passed to the plugin
    if params:
        # Play a video from a provided URL.
        play_video(params['url'])
    else:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of videos
        list_videos()

if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    router(sys.argv[2])
