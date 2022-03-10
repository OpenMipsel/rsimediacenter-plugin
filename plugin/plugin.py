from Components.ActionMap import HelpableActionMap, ActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.config import *
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor
from Screens.InfoBar import InfoBar
from Components.NimManager import nimmanager, getConfigSatlist
from enigma import eDVBResourceManager, eTimer
from Components.VolumeControl import VolumeControl
import os
import time

from Components.Label import Label
from Tools.Directories import fileExists

# MC Plugins
from MC_AudioPlayer import MC_AudioPlayer
from MC_VideoPlayer import MC_VideoPlayer
from MC_PictureViewer import MC_PictureViewer

#------------------------------------------------------------------------------------------


class DMC_MainMenu(Screen):

	def __init__(self, session, args=0):
		self.session = session
		Screen.__init__(self, session)

		self.skinName = ["DMC_MainMenu", "menu_mainmenu"]

		self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.stopService()

		self["HomeActions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"cancel": self.Exit,
			"red": self.startMC_VideoPlayer,
			"green": self.startRecordings,
			"yellow": self.startMC_AudioPlayer,
			"blue": self.startMC_PictureViewer,
		}, -1)

		#Check if AzBox because of using MRUA
		self.procstarted = False
		if os.path.exists("/proc/player"):
			self.azbox = True
			azplay_vctrl = VolumeControl.instance
			self.azplay_currebtvol = azplay_vctrl.volctrl.getVolume()
			self.azplay_ismute = azplay_vctrl.volctrl.isMuted()
			#Preparing system for playback and starting rmfp_player
			self.session.nav.playService(None)
		else:
			self.azbox = False

		list = []
		list.append((_("My Videos"), "videos", "", "50"))
		list.append((_("My Recordings"), "recordings", "", "50"))
		list.append((_("My Music"), "music", "", "50"))
		list.append((_("My Pictures"), "pictures", "", "50"))
		self["menu"] = List(list)

# BUTTON MAINMENU MRUAPLAYER - VIDEOPLAYER
	def startMC_VideoPlayer(self):
		selection = self["menu"].getCurrent()
		if selection is not None:
			x = self.procservice()
			if x == 1:
				self.session.openWithCallback(self.tmpcallback, MC_VideoPlayer)
			#self.procservice();
			#self.session.openWithCallback(self.tmpcallback, MC_VideoPlayer)
		else:
			self.session.open(MessageBox, _("Error: Something is wrong, cannot find") + " %s\n" % (selection[1]), MessageBox.TYPE_INFO)

# BUTTON MAINMENU MRUAPLAYER - RECORDINGS
	def startRecordings(self):
		selection = self["menu"].getCurrent()
		if selection is not None:
			InfoBar.showMovies(InfoBar.instance)
		else:
			self.session.open(MessageBox, _("Error: Something is wrong, cannot find") + " %s\n" % (selection[1]), MessageBox.TYPE_INFO)


# BUTTON MAINMENU MRUAPLAYER - AUDIOPLAYER

	def startMC_AudioPlayer(self):
		selection = self["menu"].getCurrent()
		if selection is not None:
			self.session.openWithCallback(self.tmpcallback, MC_AudioPlayer)
		else:
			self.session.open(MessageBox, _("Error: Something is wrong, cannot find") + " %s\n" % (selection[1]), MessageBox.TYPE_INFO)

# BUTTON MAINMENU MRUAPLAYER - PICTUREVIEWER
	def startMC_PictureViewer(self):
		selection = self["menu"].getCurrent()
		if selection is not None:
			self.session.openWithCallback(self.tmpcallback, MC_PictureViewer)
		else:
			self.session.open(MessageBox, _("Error: Something is wrong, cannot find") + " %s\n" % (selection[1]), MessageBox.TYPE_INFO)

	def procservice(self):
		if self.azbox == True:
			print("Setting Proc Player")
			tmpfile = open('/proc/player', 'rb')
			line = tmpfile.readline()
			tmpfile.close()
			print(line)
			if int(line[:-1]) == 1:
				print('Everything is freed up we can write to /proc/player')
				open('/proc/player', 'w').write('2')
				self.procstarted = True
				return 1
			elif int(line[:-1]) != 1:
				print("Proc was not freed up yet so we can't continue")
				return 2
		else:
			return 1

	def okbuttonClick(self):
		print("okbuttonClick")
		selection = self["menu"].getCurrent()
		if selection is not None:
			if selection[1] == "videos":
				x = self.procservice()
				if x == 1:
					self.session.openWithCallback(self.tmpcallback, MC_VideoPlayer)
			elif selection[1] == "recordings":
				InfoBar.showMovies(InfoBar.instance)
			elif selection[1] == "music":
			#	x = self.procservice()
			#	if x == 1:
				self.session.openWithCallback(self.tmpcallback, MC_AudioPlayer)
			elif selection[1] == "pictures":
				self.session.openWithCallback(self.tmpcallback, MC_PictureViewer)
			else:
				self.session.open(MessageBox, _("Error: Something is wrong, cannot find") + " %s\n" % (selection[1]), MessageBox.TYPE_INFO)

	def tmpcallback(self):
		if self.procstarted == True:
			#Now we should return /proc/player
			hdparm = os.popen('killall rmfp_player')
			time.sleep(0.1)
			open('/proc/player', 'w').write('1')
			time.sleep(0.1)
			self.procstarted = False
			azplay_vctrl = VolumeControl.instance
			value = self.azplay_currebtvol
			azplay_vctrl.volctrl.setVolume(value, value)
			azplay_vctrl.volSave()
			azplay_vctrl.volumeDialog.setValue(value)

	def Exit(self):
		print("Playing old service")
		self.session.nav.playService(self.oldService)
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
			PluginDescriptor(name=_("Media Center"), description=_("Media Center Plugin"), icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main),
			PluginDescriptor(name=_("Media Center"), description=_("Media Center Plugin"), where=PluginDescriptor.WHERE_MENU, fnc=menu)]
	else:
		return [
			PluginDescriptor(name=_("Media Center"), description=_("Media Center Plugin"), icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]
