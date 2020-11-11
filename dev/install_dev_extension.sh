#/bin/bash

set -e

EXTENSION_ID=com.github.kbialek.ulauncher-bitwarden
ULAUNCHER_EXT_DIR=~/.local/share/ulauncher/extensions/

# Remove whatever version of this extension is installed
rm -rf ${ULAUNCHER_EXT_DIR:?}/${EXTENSION_ID}

# Symlink current dir if extension is here
if [ -e "manifest.json" ]
then
	ln -s "$(pwd)" ${ULAUNCHER_EXT_DIR}/${EXTENSION_ID}
	echo "Done"
else
	echo "Please run this script from the root directory of the extension"
fi
