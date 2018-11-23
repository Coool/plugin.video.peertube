#!/bin/bash

echo "Create a zip package to be able to install it in kodi as external source"

package=plugin.video.peertube

# very lazzy pattern extraction from addon.xml
version=$(grep "name=\"PeerTube\" version=" addon.xml | sed 's/^.*version="\([^"]*\).*$/\1/g')

zip_package=$package-$version.zip

if [[ -d $package ]]
then
    echo "[ERROR] '$package' directory does already exists, please remove it or move it away" >&2
    exit 1
fi

if [[ -e $zip_package ]]
then
    echo "[WARNING] '$zip_package' zip already exists, it will be updated. Please remove it or move it away or change version in addon.xml next time..." >&2
fi

mkdir $package

cp -r addon.xml icon.png fanart.jpg peertube.py LICENSE.txt resources/ service.py $package
zip -r $zip_package $package

echo
echo "[INFO] '$(pwd)/$zip_package' created. You can import it in kodi"
