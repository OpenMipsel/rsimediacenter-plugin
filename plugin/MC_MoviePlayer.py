from enigma import iPlayableService, eTimer, eWidget, eRect, eServiceReference, iServiceInformation, iServiceKeys, getDesktop
from Screens.Screen import Screen
from Screens.MinuteInput import MinuteInput
from Screens.ServiceInfo import ServiceInfoList, ServiceInfoListEntry
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.InfoBarGenerics import InfoBarSeek, InfoBarPVRState, InfoBarCueSheetSupport, InfoBarShowHide, InfoBarNotifications, InfoBarAudioSelection, InfoBarSubtitleSupport

from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Components.Pixmap import Pixmap, MovingPixmap
from Components.Label import Label
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.Button import Button
from Components.ServiceEventTracker import ServiceEventTracker
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.config import *
from Components.Harddisk import harddiskmanager
from Tools.Directories import resolveFilename, fileExists, pathExists, createDir, SCOPE_MEDIA
from Components.Sources.StaticText import StaticText
from Components.MenuList import MenuList
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase

import os
from os import path as os_path, remove as os_remove, listdir as os_listdir, system

from MC_SeekInput import SeekInput

class MC_MoviePlayerSummary(Screen):
	skin = """
	<screen name="MoviePlayerSummary" position="0,0" size="90,64" id="3">
		<widget source="session.CurrentService" render="Label" position="0,0" size="120,25" halign="center" valign="center">
			<convert type="ServicePosition">Position,ShowHours</convert>
		</widget>
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session)

class MC_MoviePlayer(Screen, InfoBarBase, InfoBarNotifications, InfoBarSeek, InfoBarPVRState, InfoBarShowHide, HelpableScreen, InfoBarCueSheetSupport, InfoBarAudioSelection, InfoBarSubtitleSupport):
	ALLOW_SUSPEND = True
	ENABLE_RESUME_SUPPORT = False

	def __init__(self, session, ref="", args=None):

		Screen.__init__(self, session)
		InfoBarBase.__init__(self)
		InfoBarNotifications.__init__(self)
		InfoBarCueSheetSupport.__init__(self, actionmap="MediaPlayerCueSheetActions")
		InfoBarShowHide.__init__(self)
		InfoBarAudioSelection.__init__(self)
		InfoBarSubtitleSupport.__init__(self)
		HelpableScreen.__init__(self)
		InfoBarSeek.__init__(self)
		InfoBarPVRState.__init__(self)

		self.skinName = ["MC_MoviePlayer", "DVDPlayer"]

		self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.stopService()
		self["audioLabel"] = Label("n/a")
		self["subtitleLabel"] = Label("None")

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evStopped: self.__serviceStopped,
				iPlayableService.evStart: self.__serviceStarted,
				iPlayableService.evUpdatedInfo: self.__UpdatedInfo,
			})

		self["MoviePlayerDirectionActions"] = ActionMap(["DirectionActions"],
			{
				#MENU KEY DOWN ACTIONS
				#"left": self.keyLeft,
				#"right": self.keyRight,
				#"up": self.keyUp,
				#"down": self.keyDown,
				
				#MENU KEY REPEATED ACTIONS
				"leftRepeated": self.doNothing,
				"rightRepeated": self.doNothing,
				"upRepeated": self.doNothing,
				"downRepeated": self.doNothing,
				
				#MENU KEY UP ACTIONS
				"leftUp": self.doNothing,
				"rightUp": self.doNothing,
				"upUp": self.doNothing,
				"downUp": self.doNothing,
			})

		self["OkCancelActions"] = ActionMap(["OkCancelActions"],
			{
				"ok": self.keyOk,
				"cancel": self.keyCancel,
			})

		self["MC_MoviePlayerActions"] = HelpableActionMap(self, "MC_MoviePlayerActions",
			{
				#OWN ACTIONS
				"ok": (self.keyOk, _("Toggle info")),
				"stop": (self.stop, _("Stop Playback")),
				"keyMenu": (self.menu, _("Show menu options")),
				"seekTotime": (self.seekTotime, _("switch to the next angle")),
				"seekFwdinput": (self.seekFwdInput, _("Seek forward with input box")),
				"seekBwdinput": (self.seekBwdInput, _("Seek backward with input box")),
				"subtitles": (self.subtitleSelection, _("Subtitle selection")),
				
				#Actions linked to inforbarseek
				"playpause": (self.playpauseService, _("Pause / Resume")),
				"toggleInfo": (self.toggleShow, _("toggle time, chapter, audio, subtitle info")),
				"seekFwd": (self.seekFwd, _("Seek forward")),
				"seekBwd": (self.seekBack, _("Seek backward")),
				
				#Actions from Inforbaraudioselection
				"AudioSelection": (self.audioSelection, _("Select audio track")),
			}, -2)

		self["NumberActions"] = NumberActionMap(["NumberActions"],
			{
				"1": self.keyNumberGlobal,
				"2": self.keyNumberGlobal,
				"3": self.keyNumberGlobal,
				"4": self.keyNumberGlobal,
				"5": self.keyNumberGlobal,
				"6": self.keyNumberGlobal,
				"7": self.keyNumberGlobal,
				"8": self.keyNumberGlobal,
				"9": self.keyNumberGlobal,
				"0": self.keyNumberGlobal,
			})

		self.onClose.append(self.__onClose)

		self.ref = ref
		self.onFirstExecBegin.append(self.Start)
		self.service = None

	def __serviceStopped(self):
		print "Received __serviceStopped"
		self.exit()

	def __serviceStarted(self):
		print "Received __serviceStarted"
		resfile = str(self.ref.getPath() + ".res")
		try:
			f = open(resfile, "r")
			self.resumepos = int(f.readline())
			f.close()
			if self.resumepos:
				print "Found Resume Position", self.resumepos
				self.session.openWithCallback(self.resume, MessageBox, _("Resuming playback"), timeout=2, type=MessageBox.TYPE_INFO)
		except:
			pass

	def resume(self, answer):
		print self.resumepos
		self.seekProcess(self.resumepos)

	def __UpdatedInfo(self):
		print "Received __UpdatedInfo"
		service = self.session.nav.getCurrentService()
		audio = service.audioTracks()
		if audio:
			n = audio.getNumberOfTracks()
			currentTrack = audio.getCurrentTrack()
			if currentTrack > -1:
				i = audio.getTrackInfo(currentTrack)
				description = i.getDescription()
				language = i.getLanguage()
				self["audioLabel"].setText(language + "  ( " + description + " )")
		subtitle = service.subtitle()
#		if subtitle:
#			subtitlelist = subtitle.getSubtitleList()
#			self.session.infobar = self
#			if self.session.infobar.subtitles_enabled and self.session.infobar.selected_subtitle:
#				for x in subtitlelist:
#					if self.session.infobar.selected_subtitle[:4] == x[:4]:
#						self["subtitleLabel"].setText(x[4])

	def keyNumberGlobal(self, number):
		#print "You pressed number " + str(number)
		pass

	def getServiceInterface(self, iface):
		service = self.service
		if service:
			attr = getattr(service, iface, None)
			if callable(attr):
				return attr()
		return None

	def doNothing(self):
		pass

	def sendKey(self, key):
		keys = self.getServiceInterface("keys")
		if keys:
			keys.keyPressed(key)
		return keys

	def subtitleSelection(self):
		from Screens.AudioSelection import SubtitleSelection
		self.session.open(SubtitleSelection, self)

	def seekFwdInput(self):
		self.session.openWithCallback(self.seekProcess, SeekInput, "fwd")

	def seekBwdInput(self):
		self.session.openWithCallback(self.seekProcess, SeekInput, "bwd")

	def seekTotime(self):
		self.session.openWithCallback(self.seekProcess, SeekInput, "totime")

	def seekProcess(self, pts):
		if pts is not -1:
			service = self.session.nav.getCurrentService()
			if service:
				seekable = self.getSeek()
				if seekable:
					seekable.seekTo(pts)

	def stop(self):
		self.exit()

	def keyOk(self):
		print "pressed ok"
		self.toggleShow()
 
	def keyCancel(self):
		self.exit()

	def menu(self):
		self.session.openWithCallback(self.menuCallback, MC_MoviePlayer_Menu)

	def menuCallback(self, value):
		if value == 0:
			self.subtitleSelection()
		elif value == 1:
			self.audioSelection()
		elif value == 2:
			self.seekTotime()

	def Start(self):
		print "Starting Playback of file:", self.ref
		if self.ref is None:
			self.exit()
		else:
			self.session.nav.playService(self.ref)
			self.service = self.session.nav.getCurrentService()

	def exit(self):
		if self.service:
			self.session.nav.stopService()
			self.service = None
		self.close()

	def __onClose(self):
		pass

	def createSummary(self):
		return MC_MoviePlayerSummary

class MC_MoviePlayer_Menu(Screen):
	skin = """
	<screen name="MC_MoviePlayer_Menu" position="30,55" size="270,140" title="%s" >
	<widget name="pathlabel" transparent="1" zPosition="2" position="0,120" size="380,20" font="Regular;16" />
	<widget name="list" zPosition="5" transparent="1" position="10,10" size="330,200" scrollbarMode="showOnDemand" />
	</screen>""" % _("MoviePlayer - Menu")

	def __init__(self, session):
		Screen.__init__(self, session)
		self["list"] = MenuList([])
		self.list = []
		self.list.append(_("Subtitle Selection"))
		self.list.append(_("Audio Selection"))
		self.list.append(_("Go to Position"))

		self["pathlabel"] = Label(_("Select option"))

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"cancel": self.Exit,
			"ok": self.okbuttonClick
		}, -1)
		self.onLayoutFinish.append(self.buildList)

	def buildList(self):
		list = []
		for i in range(0, len(self.list)):
			text = "" + self.list[i]
			list.append(text)
		self["list"].setList(list)

	def okbuttonClick(self):
		selection = self["list"].getSelectionIndex()
		self.close(selection)

	def Exit(self):
		self.close(None)
