A Kodi add-on for watching content hosted on [Peertube](http://joinpeertube.org/).

This code is still proof-of-concept but it works, and you're welcome to improve
it.

# Features

* Browse all videos on a PeerTube instance 
* Search for videos on a PeerTube instance
* Select Peertube instance to use (Doesn't work yet)
* Select the preferred video resolution: the plugin will try to play the select
  video resolution.
  If it's not available, it will play the lower resolution that is the closest
  from your preference.
  If not available, it will play the higher resolution that is the closest from
  your preference.

# User settings

* Preferred PeerTube instance 
* Preferred video resolution
* Number of videos to display per page
* Sort method to be used when listing videos (Currently, only 'views' and
  'likes')
* Select the filter to use when browsing the videos on an instance:
  * local will only display the videos which are local to the selected instance
  * all-local will only display the videos which are local to the selected
    instance plus the private and unlisted videos **(requires admin privileges)**

# API

This add-on can be called from other add-ons in Kodi to play videos thanks to
the following API:

`plugin://plugin.video.peertube/?action=play_video&instance=<instance>&id=<id>`

where:
* `<instance>` is the base URL of the instance hosting the video
* `<id>` is the ID or the UUID of the video on the instance server

For instance to play the video behind the URL
`https://framatube.org/videos/watch/9c9de5e8-0a1e-484a-b099-e80766180a6d` call
the add-on with:

`plugin://plugin.video.peertube/?action=play_video&instance=framatube.org&id=9c9de5e8-0a1e-484a-b099-e80766180a6d`

# Limitations

* This add-on doesn't support Webtorrent yet. So, it cannot download/share
  from/to regular PeerTube clients. The reason is that it uses the libtorrent
  python library which doesn't support it yet (see
  https://github.com/arvidn/libtorrent/issues/223)
* The add-on doesn't delete the downloaded files at the moment. So, it may fill
  up your disk.

# Requirements

* Kodi 17 (Krypton) or above
* [libtorrent](https://libtorrent.org/) python bindings must be installed on
  your machine (on Debian type `apt install python-libtorrent` as root).
