from enigma import eTimer, eWidget, eRect, eServiceReference, iServiceInformation
from Screens.Screen import Screen
from Screens.ServiceInfo import ServiceInfoList, ServiceInfoListEntry
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Pixmap import Pixmap, MovingPixmap
from Components.Label import Label
from Components.Button import Button

from Screens.MessageBox import MessageBox

from Components.ConfigList import ConfigList
from Components.config import *

from Tools.Directories import resolveFilename, fileExists, pathExists, createDir, SCOPE_MEDIA, SCOPE_SKIN_IMAGE
from Components.FileList import FileList
from Components.AVSwitch import AVSwitch
from Screens.InfoBar import MoviePlayer
from Plugins.Plugin import PluginDescriptor

import os

def getAspect():
	val = AVSwitch().getAspectRatioSetting()
	return val/2

#------------------------------------------------------------------------------------------

class MC_RSSReader(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions", "MovieSelectionActions", "MenuActions", "MoviePlayerActions", "ChannelSelectBaseActions"],
		{
			"ok": self.Exit,
			"cancel": self.Exit
		}, -1)
		
		self.aspect = getAspect()

	def Exit(self):
		self.close()
