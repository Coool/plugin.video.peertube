A Kodi add-on for watching content hosted on [PeerTube](http://joinpeertube.org/).

This add-on is under development so only basic features work, and you're
welcome to improve it.  
If you want to contribute, please start with the
[contribution guidelines](contributing.md) and the
[pending issues](https://framagit.org/StCyr/plugin.video.peertube/-/issues).

---

[[_TOC_]]

# Installation and prerequisites

Please read the
[wiki](https://framagit.org/StCyr/plugin.video.peertube/-/wikis/home)
for more information.

# Features

* Play videos (including live videos)
* Browse the videos on a PeerTube instance 
* Search for videos on a PeerTube instance
* Select the PeerTube instance to use
* Select the preferred video resolution: the plugin will try to play the
  preferred video resolution.  
  If it's not available, it will play the lower resolution that is the closest
  to your preference.  
  If not available, it will play the higher resolution that is the closest from
  your preference.

The following languages are available: English and French.  
If you want to help translating the add-on in your language, check
[here](contributing.md#translation).

# Limitations

* This add-on doesn't support Webtorrent yet. So, it cannot download/share
  from/to regular PeerTube clients.
* The add-on doesn't delete the downloaded files at the moment so it may fill
  up your disk. You may delete manually the downloaded files in the folder
  `<kodi_home>/temp/plugin.video.peertube/` (more information about
  `<kodi_home>` [here](https://kodi.wiki/view/Kodi_data_folder#Location)).

# User settings

* Preferred PeerTube instance
* Display (or not) a notification when the service starts: the notification
  lets the user know that the videos can be played which may be useful on slow
  devices (when the service takes some time to start)
* Browsing/Searching:
  * Number of items to show per page (max 100)
  * Field used to sort items when listing/searching videos:
    * `views`: sort by number of views (ascending only)
    * `likes`: sort by number of likes (ascending only)
  * Select the filter to use when browsing and searching the videos on an instance:
    * `local` will only display the videos which are local to the selected
      instance
    * `all-local` will only display the videos which are local to the selected
      instance **plus** the private and unlisted videos
      **(requires admin privileges)**
* Video playback:
  * Preferred video resolution

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
