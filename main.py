# -*- coding: utf-8 -*-
"""
    Entry point of the add-on

    Copyright (C) 2018 Cyrille Bollu
    Copyright (C) 2021 Thomas Bétous

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSE.txt for more information.
"""
import sys

from resources.lib.addon import PeerTubeAddon
from resources.lib.kodi_utils import kodi

def main(argv):
    """First function called by the add-on

    This function is created to be able to test the code in this module easily.
    """
    # Update the kodi object with the system arguments of this call
    kodi.update_call_info(argv)
    # Initialize the main class of the add-on
    addon = PeerTubeAddon()
    # Call the router function to execute the requested action
    addon.router(kodi.get_run_parameters())

if __name__ == "__main__":
    main(sys.argv)
