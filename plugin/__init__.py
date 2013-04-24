import Plugins.Plugin
from Components.config import config
from Components.config import ConfigSubsection
from Components.config import ConfigSelection
from Components.config import ConfigInteger
from Components.config import ConfigSubList
from Components.config import ConfigSubDict
from Components.config import ConfigText
from Components.config import configfile
from Components.config import ConfigYesNo
from skin import loadSkin

# Load Skin
try:
	loadSkin("../../../usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/skins/default/skin.xml")
except Exception, e:
	loadSkin("../../../usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/skins/default/skin.xml")