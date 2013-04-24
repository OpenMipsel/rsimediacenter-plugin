from Components.ActionMap import HelpableActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.config import *
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor
from Screens.InfoBar import InfoBar
import os
import time

# MC Plugins
from MC_AudioPlayer import MC_AudioPlayer
from MC_VideoPlayer import MC_VideoPlayer
from MC_PictureViewer import MC_PictureViewer

#------------------------------------------------------------------------------------------

class DMC_MainMenu(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self.skinName = ["DMC_MainMenu", "menu_mainmenu" ]
		
		self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
		#self.session.nav.stopService()
		
		self["HomeActions"] = HelpableActionMap(self, "MC_Home",
		{
			"cancel": (self.Exit, _("Exit")),
			"ok": (self.okbuttonClick, _("Ok")),
		}, -2)
		
		list = []
		list.append((_("My Videos"), "videos", "", "50"))
		list.append((_("My Recordings"), "recordings", "", "50"))
		list.append((_("My Music"), "music", "", "50"))
		list.append((_("My Pictures"), "pictures", "", "50"))
		self["menu"] = List(list)

	def okbuttonClick(self):
		print "okbuttonClick"
		selection = self["menu"].getCurrent()
		if selection is not None:
			if selection[1] == "videos":
				self.session.nav.stopService()
				self.session.openWithCallback(self.tmpcallback, MC_VideoPlayer)
			elif selection[1] == "recordings":
				InfoBar.showMovies(InfoBar.instance)
			elif selection[1] == "music":
				self.session.nav.stopService()
				self.session.openWithCallback(self.tmpcallback, MC_AudioPlayer)
			elif selection[1] == "pictures":
				self.session.nav.stopService()
				self.session.openWithCallback(self.tmpcallback, MC_PictureViewer)
			else:
				self.session.open(MessageBox,_("Error: Something is wrong, cannot find") + " %s\n" % (selection[1]),  MessageBox.TYPE_INFO)

	def tmpcallback(self):
		self.session.nav.playService(self.oldService)
		
	def Exit(self):
		self.close()

#------------------------------------------------------------------------------------------

def main(session, **kwargs):
	session.open(DMC_MainMenu)

def menu(menuid, **kwargs):
	if menuid == "mainmenu":
		return [(_("Media Center"), main, "dmc_mainmenu", 40)]
	return []

def Plugins(**kwargs):
	if True:
		return [
			PluginDescriptor(name = _("Media Center"), description = _("Media Center Plugin"), icon="plugin.png", where = PluginDescriptor.WHERE_PLUGINMENU, fnc = main),
			PluginDescriptor(name = _("Media Center"), description = _("Media Center Plugin"), where = PluginDescriptor.WHERE_MENU, fnc = menu)]
	else:
		return [
			PluginDescriptor(name = _("Media Center"), description = _("Media Center Plugin"), icon="plugin.png", where = PluginDescriptor.WHERE_PLUGINMENU, fnc = main)]
