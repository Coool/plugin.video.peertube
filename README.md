A Kodi add-on for watching content hosted on [PeerTube](http://joinpeertube.org/).

This add-on is under development so only basic features work, and you're
welcome to improve it.  
See [contribution guidelines](contributing.md) and
[pending issues](https://framagit.org/StCyr/plugin.video.peertube/-/issues) to
start.

[[_TOC_]]

# Features

* Browse all videos on a PeerTube instance 
* Search for videos on a PeerTube instance
* Select the PeerTube instance to use
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
  from/to regular PeerTube clients.
* The add-on doesn't delete the downloaded files at the moment. So, it may fill
  up your disk.

# Installation and prerequisites

Please read the
[wiki](https://framagit.org/StCyr/plugin.video.peertube/-/wikis/home)
for more information.
