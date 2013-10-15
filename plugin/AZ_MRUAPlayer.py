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
from MC_Menus import IniciaSelListMC, IniciaSelListEntryMC, Scalingmode_Menu, ScalingmodeEntryComponent, SubOptionsEntryComponent

#Load C++ parts of Mrua player and DVD player
import servicemrua
import serviceazdvd


config.plugins.mc_mrua = ConfigSubsection()
config.plugins.mc_mrua.subenc = ConfigSelection(default="43", choices = [("42", _("Latin")), ("43", _("Utf-8"))])
config.plugins.mc_mrua.subpos = ConfigInteger(default=40, limits=(0, 100))
config.plugins.mc_mrua.subcolorname = ConfigText("White", fixed_size=False)
config.plugins.mc_mrua.subcolorinside = ConfigText("FFFFFFFF", fixed_size=False)
config.plugins.mc_mrua.subcoloroutside = ConfigText("FF000000", fixed_size=False)
config.plugins.mc_mrua.subsize = ConfigInteger(default=30, limits=(5, 100))
config.plugins.mc_mrua.subdelay = ConfigInteger(default=0, limits=(-999999, 999999))
config.plugins.mc_mrua.screenres = ConfigInteger(default=0, limits=(-999999, 999999))

class MRUASummary(Screen):
	skin = """
	<screen name="MRUASummary" position="0,0" size="90,64" id="3">
		<widget source="session.CurrentService" render="Label" position="0,0" size="120,25" font="Display;16" halign="center" valign="center">
			<convert type="ServicePosition">Position,ShowHours</convert>
		</widget>
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session)

class MRUAPlayer(Screen, InfoBarBase, InfoBarNotifications, InfoBarSeek, InfoBarPVRState, InfoBarShowHide, HelpableScreen, InfoBarCueSheetSupport, InfoBarAudioSelection, InfoBarSubtitleSupport):
	ALLOW_SUSPEND = Screen.SUSPEND_PAUSES
	ENABLE_RESUME_SUPPORT = True

	def save_infobar_seek_config(self):
		self.saved_config_speeds_forward = config.seek.speeds_forward.value
		self.saved_config_speeds_backward = config.seek.speeds_backward.value
		self.saved_config_enter_forward = config.seek.enter_forward.value
		self.saved_config_enter_backward = config.seek.enter_backward.value
		self.saved_config_seek_on_pause = config.seek.on_pause.value
		self.saved_config_seek_speeds_slowmotion = config.seek.speeds_slowmotion.value
		self.saved_config_subenc = config.plugins.mc_mrua.subenc.value
		self.saved_config_subpos = config.plugins.mc_mrua.subpos.value
		self.saved_config_subcolorname = config.plugins.mc_mrua.subcolorname.value
		self.saved_config_subsize = config.plugins.mc_mrua.subsize.value
		self.saved_config_subdelay = config.plugins.mc_mrua.subdelay.value

	def change_infobar_seek_config(self):
		config.seek.speeds_forward.value = [2, 4]
		config.seek.speeds_backward.value = [2, 4]
		config.seek.speeds_slowmotion.value = [ ]
		config.seek.enter_forward.value = "2"
		config.seek.enter_backward.value = "2"
		config.seek.on_pause.value = "play"

	def restore_infobar_seek_config(self):
		config.seek.speeds_forward.value = self.saved_config_speeds_forward
		config.seek.speeds_backward.value = self.saved_config_speeds_backward
		config.seek.speeds_slowmotion.value = self.saved_config_seek_speeds_slowmotion
		config.seek.enter_forward.value = self.saved_config_enter_forward
		config.seek.enter_backward.value = self.saved_config_enter_backward
		config.seek.on_pause.value = self.saved_config_seek_on_pause
		config.plugins.mc_mrua.subenc.value = self.saved_config_subenc
		config.plugins.mc_mrua.subpos.value = self.saved_config_subpos 
		config.plugins.mc_mrua.subcolorname.value = self.saved_config_subcolorname
		config.plugins.mc_mrua.subsize.value = self.saved_config_subsize 
		config.plugins.mc_mrua.subdelay.value = self.saved_config_subdelay 

	def __init__(self, session, ref = "", args = None):

		Screen.__init__(self, session)
		InfoBarBase.__init__(self)
		InfoBarNotifications.__init__(self)
		InfoBarCueSheetSupport.__init__(self, actionmap = "MediaPlayerCueSheetActions")
		InfoBarShowHide.__init__(self)
		InfoBarAudioSelection.__init__(self)
		InfoBarSubtitleSupport.__init__(self)
		HelpableScreen.__init__(self)
		self.save_infobar_seek_config()
		self.change_infobar_seek_config()
		InfoBarSeek.__init__(self)
		InfoBarPVRState.__init__(self)

		self.skinName = ["MRUAPlayer", "DVDPlayer" ]

		self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.stopService()
		self["audioLabel"] = Label("n/a")
		self["subtitleLabel"] = Label("")
		self["angleLabel"] = Label("")
		self["chapterLabel"] = Label("")
		self["anglePix"] = Pixmap()
		self["anglePix"].hide()
		self.last_audioTuple = None
		self.last_subtitleTuple = None
		self.last_angleTuple = None
		self.totalChapters = 0
		self.currentChapter = 0
		self.totalTitles = 0
		self.currentTitle = 0

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evStopped: self.__serviceStopped,
				iPlayableService.evStart: self.__serviceStarted,
				iPlayableService.evUser+1: self.__statePlay,
				iPlayableService.evUser+2: self.__statePause,
				iPlayableService.evUser+3: self.__osdStringAvail,
				iPlayableService.evUser+4: self.__osdAudioInfoAvail,
				iPlayableService.evUser+5: self.__osdSubtitleInfoAvail
			})

		self["MRUAPlayerDirectionActions"] = ActionMap(["DirectionActions"],
			{
				#MENU KEY DOWN ACTIONS
				"left": self.keyLeft,
				"right": self.keyRight,
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

		self["DVDPlayerPlaybackActions"] = HelpableActionMap(self, "MRUAPlayerActions",
			{
				#MRUAPLAYER'S OWN ACTIONS
				"stop": (self.stop, _("Stop Playback")),
				"keyMenu": (self.menu, _("Show menu options")),
				"seekTotime": (self.seekTotime, _("switch to the next angle")),
				"seekFwdinput": (self.seekFwdInput, _("Seek forward with input box")),
				"seekBwdinput": (self.seekBwdInput, _("Seek backward with input box")),
				"subtitles": (self.subtitleSelection, _("Subtitle selection")),
				
				#Actions linked to inforbarseek
				"playpause": (self.playpauseService, _("Pause / Resume")),
				"toggleInfo": (self.toggleShow, _("toggle time, chapter, audio, subtitle info")),
				#"seekFwd": (self.seekFwd, _("Seek forward")),
				#"seekBwd": (self.seekBack, _("Seek backward")),
				
				#Actions from Inforbaraudioselection
				"AudioSelection": (self.audioSelection, _("Select audio track")),
			}, -2)

		self["NumberActions"] = NumberActionMap( [ "NumberActions"],
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

		config.plugins.mc_mrua.screenres.value = str(config.av.videomode[config.av.videoport.value].value)[:-1]
		#print config.plugins.mc_mrua.sreenres.value

		#Tmp Hack added to disable RTC while playing through mrua
		os.system("echo 0 > /tmp/zerortc")
		os.system("mount -o bind /tmp/zerortc /proc/stb/fp/rtc")

		self.ref = ref
		self.onFirstExecBegin.append(self.Start)
		self.service = None
		self.in_menu = False

	def __serviceStopped(self):
		self.exit()

	def __serviceStarted(self):
		self["SeekActions"].setEnabled(False)

	def __statePlay(self):
		print "statePlay"

	def __statePause(self):
		print "statePause"

	def __osdStringAvail(self):
		print "StringAvail"

	def __osdAudioInfoAvail(self):
		info = self.getServiceInterface("info")
		audioTuple = info and info.getInfoObject(iServiceInformation.sUser+6)
		print "AudioInfoAvail ", repr(audioTuple)
		if audioTuple:
			audioString = "%d: %s (%s)" % (audioTuple[0],audioTuple[1],audioTuple[2])
			self["audioLabel"].setText(audioString)
			if audioTuple != self.last_audioTuple and not self.in_menu:
				self.doShow()
		self.last_audioTuple = audioTuple

	def __osdSubtitleInfoAvail(self):
		info = self.getServiceInterface("info")
		subtitleTuple = info and info.getInfoObject(iServiceInformation.sUser+7)
		print "SubtitleInfoAvail ", repr(subtitleTuple)
		if subtitleTuple:
			subtitleString = ""
			if subtitleTuple[0] is not 0:
				subtitleString = "%d: %s" % (subtitleTuple[0],subtitleTuple[1])
			self["subtitleLabel"].setText(subtitleString)
			if subtitleTuple != self.last_subtitleTuple and not self.in_menu:
				self.doShow()
		self.last_subtitleTuple = subtitleTuple

	def keyNumberGlobal(self, number):
		#print "You pressed number " + str(number)
		if number == 1:
			self.quickSeek(-config.seek.selfdefined_13.value)
		elif number == 3:
			self.quickSeek(config.seek.selfdefined_13.value)
		elif number == 4:
			self.quickSeek(-config.seek.selfdefined_46.value)
		elif number == 6:
			self.quickSeek(config.seek.selfdefined_46.value)
		elif number == 7:
			self.quickSeek(-config.seek.selfdefined_79.value)
		elif number == 9:
			self.quickSeek(config.seek.selfdefined_79.value)

	def quickSeek(self, dt):
		service = self.session.nav.getCurrentService()
		if service:
			self.seek = service.seek()
			if self.seek:
				self.lengthpts = self.seek.getLength()
				self.positionpts = self.seek.getPlayPosition()
				self.length = int(self.lengthpts[1]) / 90000
				self.position = int(self.positionpts[1]) / 90000
				if self.length and self.position:
					self.seekProcess((self.position + dt) * 90000)
					self.show()

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
		print "test seek to time"
		if pts is not -1:
			if self.service:
				seekable = self.getSeek()
				if seekable:
					seekable.seekTo(pts)

	def stop(self):
		self.exit()

	def keyRight(self):
		self.sendKey(iServiceKeys.keyRight)

	def keyLeft(self):
		self.sendKey(iServiceKeys.keyLeft)

	def keyOk(self):
		 self.toggleShow()
 
	def keyCancel(self):
		self.exit()

	def menu(self):
		self.session.openWithCallback(self.menuCallback, MRUAPlayer_Menu)

	def menuCallback(self, value):
		if value == 0:
			self.session.openWithCallback(self.subOptionsCallback, MRUAPlayer_Suboptions2)
		if value == 1:
			self.session.open(Scalingmode_Menu)
		elif value == 2:
			self.subtitleSelection()
		elif value == 3:
			self.audioSelection()
		elif value == 4:
			self.seekTotime()
	
	def subOptionsCallback(self, value):
		if value == 1:
			self.saved_config_subenc = config.plugins.mc_mrua.subenc.value
			self.saved_config_subpos = config.plugins.mc_mrua.subpos.value
			self.saved_config_subcolorname = config.plugins.mc_mrua.subcolorname.value
			self.saved_config_subsize = config.plugins.mc_mrua.subsize.value
			self.saved_config_subdelay = config.plugins.mc_mrua.subdelay.value
			config.plugins.mc_mrua.save()
			configfile.save()

	def Start(self):
		print "Mrua Starting Playback", self.ref
		if self.ref is None:
			self.exit()
		else:
			newref = eServiceReference(4370, 0, self.ref)
			print "play", newref.toString()
			############# spaze team added for fix filenames ANSI to utf8
			name = str(self.ref)
			try:
				name = name.decode("utf-8").encode("utf-8")
			except:
				try:
					name = name.decode("windows-1252").encode("utf-8")
				except:
					pass
			############################################################# 
			self["chapterLabel"].setText(self.ref)
			self.session.nav.playService(newref)
			self.service = self.session.nav.getCurrentService()
			print "self.service", self.service
			print "cur_dlg", self.session.current_dialog

	def exit(self):
		if self.service:
			self.session.nav.stopService()
			self.service = None
		self.close()

	def __onClose(self):
		#tmp HACK enable rtc again
		os.system("umount /proc/stb/fp/rtc")
		self.restore_infobar_seek_config()

	def createSummary(self):
		return MRUASummary

#override some InfoBarSeek functions
	def playLastCB(self, answer): # overwrite infobar cuesheet function
		print "playLastCB", answer, self.resume_point
		if self.service:
			if answer == True:
				seekable = self.getSeek()
				if seekable:
					seekable.seekTo(self.resume_point)
		self.hideAfterResume()

	def showAfterCuesheetOperation(self):
		if not self.in_menu:
			self.show()

	def doEof(self):
		self.setSeekState(self.SEEK_STATE_PLAY)

	def calcRemainingTime(self):
		return 0

	def hotplugCB(self, dev, media_state):
		print "[hotplugCB]", dev, media_state
		if dev == harddiskmanager.getCD():
			if media_state == "1":
				self.scanHotplug()
			else:
				self.physicalDVD = False

	def scanHotplug(self):
		devicepath = harddiskmanager.getAutofsMountpoint(harddiskmanager.getCD())
		if pathExists(devicepath):
			from Components.Scanner import scanDevice
			res = scanDevice(devicepath)
			list = [ (r.description, r, res[r], self.session) for r in res ]
			if list:
				(desc, scanner, files, session) = list[0]
				for file in files:
					print file
					if file.mimetype == "video/x-dvd":
						print "physical dvd found:", devicepath
						self.physicalDVD = True
						return
		self.physicalDVD = False

#--------------------------------------------------------------------------------------

class MRUAPlayer_Menu(Screen):
	skin = """
	<screen name="MRUAPlayer_Menu" position="30,55" size="350,240" title="%s" >
	<widget name="pathlabel" transparent="1" zPosition="2" position="0,170" size="380,20" font="Regular;16" />
	<widget name="list" zPosition="5" transparent="1" position="10,10" size="330,200" scrollbarMode="showOnDemand" />
	</screen>""" % _("VideoPlayer - Menu")

	def __init__(self, session):
		
		Screen.__init__(self, session)
		self["list"] = IniciaSelListMC([])
		self.list = []
		
		self.list.append(_("Subtitle Options"))
		self.list.append(_("Scaling Mode"))
		self.list.append(_("Subtitle Selection"))
		self.list.append(_("Audio Selection"))
		self.list.append(_("Go to Position"))
		
		self["pathlabel"] = Label(_("Select option"))
		
		self["actions"] = ActionMap(["OkCancelActions","ColorActions"],
		{
			"yellow":self.setaudio,
			"red":self.setsubtitle,
			"cancel": self.Exit,
			"ok": self.okbuttonClick
		}, -1)
		self.onLayoutFinish.append(self.buildList)

	def buildList(self):
		list = []
		for i in range(0,len(self.list)):
			texto=""+self.list[i]
			list.append(IniciaSelListEntryMC(texto, str(i)))
		self["list"].setList(list)

	def setaudio(self):
		self.close(2)

	def setsubtitle(self):
		self.close(3)

	def okbuttonClick(self):
		selection = self["list"].getSelectionIndex()
		self.close(selection)

	def Exit(self):
		self.close(None)

#-----------------------------------------------------------------------------------------------------------------------
class MRUAPlayer_Suboptions2(Screen):
	skin = """
	<screen name="MRUAPlayer_Suboptions2" position="30,55" size="600,250" title="%s" >
	<widget name="list" zPosition="2" transparent="1" position="10,10" size="600,250" scrollbarMode="showOnDemand" />
	<widget name="sizeval" position="300,10" zPosition="3" size="250,40" font="Regular;20" valign="top" halign="left" transparent="1" />
	<widget name="posval" position="300,40" zPosition="3" size="250,40" font="Regular;20" valign="top" halign="left" transparent="1" />
	<widget name="colorval" position="300,70" zPosition="3" size="250,40" font="Regular;20" valign="top" halign="left" transparent="1" />
	<widget name="encval" position="300,100" zPosition="3" size="250,40" font="Regular;20" valign="top" halign="left" transparent="1" />
	<widget name="delayval" position="300,130" zPosition="3" size="250,40" font="Regular;20" valign="top" halign="left" transparent="1" />
	<widget name="note" position="0,170" zPosition="3" size="600,30" font="Regular;18" valign="top" halign="center" transparent="1" />
	<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/skins/default/images/icons/key-red.png" position="400,210" zPosition="2" size="150,30" transparent="1" alphatest="on" />
	<widget name="key_red" position="400,210" zPosition="3" size="150,30" font="Regular;16" valign="center" halign="center" transparent="1" />
	</screen>""" % _("VideoPlayer - Menu")

	def __init__(self, session):
		
		Screen.__init__(self, session)
		self.save = False
		self["sizeval"] = Label()
		self["posval"] = Label()
		self["colorval"] = Label()
		self["encval"] = Label()
		self["delayval"] = Label()
		self["note"] = Label()
		self["key_red"] = Button(_("Save as Defaults"))
		self["list"] = IniciaSelListMC([])
		self.list = []
		self.list.append(_("Subtitle Size"))
		self.list.append(_("Subtitle Position"))
		self.list.append(_("Subtitle Color"))
		self.list.append(_("Subtitle Encoding"))
		self.list.append(_("Subtitle Delay (in seconds)"))
		
		self.colorindex = -1
		self.colorcount = -1
		
		from xml.dom.minidom import parse
		self.dom = parse("/usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/subcolors.xml")
		self.colors = self.dom.getElementsByTagName('color')
		
		#self.colorlist = []
		#list.append(("Titel", "nothing", "entryID", "weight"))
		#self.colorlist.append(("12", "13", "44", "46"))
		#self.colorlist.append(("11", "14", "42", "45"))

		self["actions"] = ActionMap(["MC_AudioPlayerActions"],
		{
			"cancel": self.Exit,
			"ok": self.okbuttonClick,
			"right": self.right,
			"left": self.left,
			"blue": self.setcolor,
			"red": self.Dosave
		}, -1)
		self.onLayoutFinish.append(self.buildList)

	def getServiceInterface(self, iface):
		service = self.session.nav.getCurrentService()
		if service:
			attr = getattr(service, iface, None)
			if callable(attr):
				return attr()
		return None
		
	def getInfo(self):
		info = self.getServiceInterface("info")
		infoTuple = info and info.getInfoObject(iServiceInformation.sUser+9)
		print "Getting Subtitle Info ", repr(infoTuple)
		if infoTuple:
			self.size = infoTuple[0]
			self.pos = infoTuple[1]
			self.color = infoTuple[2]
			self.enc = infoTuple[3]
			self.delay = infoTuple[4]
			self.enctype = infoTuple[5]
		#Size
		if self.size == 1:
			self["sizeval"].setText(("%02d") % (config.plugins.mc_mrua.subsize.value))
		else:
			self["sizeval"].setText(_("Fixed"))
		#Position
		if self.pos == 1:
			self["posval"].setText(("%02d") % (config.plugins.mc_mrua.subpos.value))
		else:
			self["posval"].setText(_("Fixed"))
		#Color
		if self.color == 1:
			self["colorval"].setText(("%s") % (config.plugins.mc_mrua.subcolorname.value))
			for entry in self.colors:
				self.colorcount = self.colorcount + 1
				color=entry.getElementsByTagName('Name')[0].childNodes[0].nodeValue
				if color == config.plugins.mc_mrua.subcolorname.value:
					self.colorindex = self.colorcount
		else:
			self["colorval"].setText(_("Fixed"))
		#Encoding
		if self.enc == 1:
			if self.enctype == 1:
				self["encval"].setText(_("Latin-1"))
				config.plugins.mc_mrua.subenc.value = "42"
			elif self.enctype == 2:
				self["encval"].setText(_("UTF-8"))
				config.plugins.mc_mrua.subenc.value = "43"
			elif self.enctype == 0:
				if config.plugins.mc_mrua.subenc.value == 42:
					self["encval"].setText(_("Latin-1"))
				else:
					self["encval"].setText(_("UTF-8"))
		else:
			self["encval"].setText(_("Fixed"))
		#Delay
		if self.delay == 1:
			self["delayval"].setText(("%.1f") % (config.plugins.mc_mrua.subdelay.value))
		else:
			self["delayval"].setText(_("Fixed"))

	def buildList(self):
		list = []
		for i in range(0,len(self.list)):
			text=""+self.list[i]
			list.append(SubOptionsEntryComponent(text))
		self["list"].setList(list)
		self.getInfo()
		self["note"].setText(_("Please use left/right keys to change settings"))

	def right(self):
		selection = self["list"].getSelectionIndex()
		keys = self.getServiceInterface("keys")
		#Size
		if selection == 0 and self.size == 1:
			val = config.plugins.mc_mrua.subsize.value + 5
			if val <= 100:
				config.plugins.mc_mrua.subsize.setValue(val)
				self["sizeval"].setText(("%02d") % (config.plugins.mc_mrua.subsize.value))
			keys.keyPressed(iServiceKeys.keyUser)
		#Position
		if selection == 1 and self.pos == 1:
			val = config.plugins.mc_mrua.subpos.value + 5
			if val <= 100:
				config.plugins.mc_mrua.subpos.setValue(val)
				self["posval"].setText(("%02d") % (config.plugins.mc_mrua.subpos.value))
			keys.keyPressed(iServiceKeys.keyUser+1)
		#Color
		if selection == 2 and self.color == 1:
			if self.colorindex < self.colorcount:
				self.colorindex = self.colorindex + 1
			else:
				self.colorindex = 0
			color = self.colors[self.colorindex].getElementsByTagName('Name')[0].childNodes[0].nodeValue
			print color
			config.plugins.mc_mrua.subcolorname.value = self.colors[self.colorindex].getElementsByTagName('Name')[0].childNodes[0].nodeValue
			config.plugins.mc_mrua.subcolorinside.value = self.colors[self.colorindex].getElementsByTagName('inside')[0].childNodes[0].nodeValue 
			config.plugins.mc_mrua.subcoloroutside.value = self.colors[self.colorindex].getElementsByTagName('outside')[0].childNodes[0].nodeValue
			self["colorval"].setText(("%s") % (config.plugins.mc_mrua.subcolorname.value))
			keys.keyPressed(iServiceKeys.keyUser+5)
		#Encoding
		if selection == 3 and self.enc == 1:
			config.plugins.mc_mrua.subenc.handleKey(KEY_RIGHT)
			print config.plugins.mc_mrua.subenc.value
			if config.plugins.mc_mrua.subenc.value == "42":
				self["encval"].setText(_("Latin-1"))
			else:
				self["encval"].setText(_("UTF-8"))
			keys.keyPressed(iServiceKeys.keyUser+3)
		#Delay
		if selection == 4 and self.delay == 1:
			val = config.plugins.mc_mrua.subdelay.value + 1
			if val <= 90:
				config.plugins.mc_mrua.subdelay.setValue(val)
				self["delayval"].setText(("%.1f") % (config.plugins.mc_mrua.subdelay.value))
			keys.keyPressed(iServiceKeys.keyUser+4)

	def left(self):
		selection = self["list"].getSelectionIndex()
		keys = self.getServiceInterface("keys")
		#Size
		if selection == 0 and self.size == 1:
			val = config.plugins.mc_mrua.subsize.value - 5
			if val >= 5:
				config.plugins.mc_mrua.subsize.setValue(val)
				self["sizeval"].setText(("%02d") % (config.plugins.mc_mrua.subsize.value))
			keys.keyPressed(iServiceKeys.keyUser)
		#Position
		if selection == 1 and self.pos == 1:
			val = config.plugins.mc_mrua.subpos.value - 5
			if val >= 0:
				config.plugins.mc_mrua.subpos.setValue(val)
				self["posval"].setText(("%02d") % (config.plugins.mc_mrua.subpos.value))
			keys.keyPressed(iServiceKeys.keyUser+1)
		#Color
		if selection == 2 and self.color == 1:
			if self.colorindex > 0:
				self.colorindex = self.colorindex - 1
			else:
				self.colorindex = self.colorcount
			color = self.colors[self.colorindex].getElementsByTagName('Name')[0].childNodes[0].nodeValue
			print color
			config.plugins.mc_mrua.subcolorname.value = self.colors[self.colorindex].getElementsByTagName('Name')[0].childNodes[0].nodeValue
			config.plugins.mc_mrua.subcolorinside.value = self.colors[self.colorindex].getElementsByTagName('inside')[0].childNodes[0].nodeValue 
			config.plugins.mc_mrua.subcoloroutside.value = self.colors[self.colorindex].getElementsByTagName('outside')[0].childNodes[0].nodeValue
			self["colorval"].setText(("%s") % (config.plugins.mc_mrua.subcolorname.value))
			keys.keyPressed(iServiceKeys.keyUser+5)
		#Encoding
		if selection == 3 and self.enc == 1:
			config.plugins.mc_mrua.subenc.handleKey(KEY_LEFT)
			print config.plugins.mc_mrua.subenc.value
			if config.plugins.mc_mrua.subenc.value == "42":
				self["encval"].setText(_("Latin-1"))
			else:
				self["encval"].setText(_("UTF-8"))
			keys.keyPressed(iServiceKeys.keyUser+3)
		#Delay
		if selection == 4 and self.delay == 1:
			val = config.plugins.mc_mrua.subdelay.value - 1
			if val >= -90:
				config.plugins.mc_mrua.subdelay.setValue(val)
				self["delayval"].setText(("%.1f") % (config.plugins.mc_mrua.subdelay.value))
			keys.keyPressed(iServiceKeys.keyUser+4)

	def Dosave(self):
		print "Saving settings as default"
		self["note"].setText(_("Please use left/right keys to change settings...SAVED"))
		self.save = True

	def setcolor(self):
		keys = self.getServiceInterface("keys")
		keys.keyPressed(iServiceKeys.keyUser+5)

	def okbuttonClick(self):
		self.Exit()

	def Exit(self):
		if self.save == True:
			val = 1
		else:
			val = 0
		self.close(val)

#-----------------------------------------------------------------------------------------------------------------------
#Depreciated - Not used anymore
class MRUAPlayer_SubOptions(Screen):
	skin = """
		<screen position="80,80" size="600,220" title="Subtitle Options" >
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/skins/default/images/icons/key-yellow.png" position="360,30" zPosition="2" size="150,30" transparent="1" alphatest="on" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/skins/default/images/icons/key-blue.png" position="360,90" zPosition="2" size="150,30" transparent="1" alphatest="on" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/skins/default/images/icons/key-red.png" position="360,150" zPosition="2" size="150,30" transparent="1" alphatest="on" />
			<widget name="key_yellow" position="360,30" zPosition="3" size="150,30" font="Regular;20" valign="center" halign="center" transparent="1" />
			<widget name="key_blue" position="360,90" zPosition="3" size="150,30" font="Regular;20" valign="center" halign="center" transparent="1" />
			<widget name="key_red" position="360,150" zPosition="3" size="150,30" font="Regular;20" valign="center" halign="center" transparent="1" />
			<widget name="navigation" position="40,30" zPosition="3" size="200,200" font="Regular;20" valign="top" halign="left" transparent="1" />
		</screen>"""
		
	def __init__(self, session):
		self.skin = MRUAPlayer_SubOptions.skin
		Screen.__init__(self, session)
		
		self["DVDPlayerPlaybackActions"] = HelpableActionMap(self, "MC_AudioPlayerActions",
		{
			"ok": (self.close, _("Play selected file")),
			"cancel": (self.close, _("Exit Video Player")),
			"left": (self.left, _("Move left")),
			"right": (self.right, _("Move right")),
			"up": (self.up, _("Move up")),
			"down": (self.down, _("Move down")),
			"nextBouquet": (self.increase, _("Increase Size")),
			"prevBouquet": (self.decrease, _("Decrease Size")),
			"red": (self.reset, _("Reset to defaults")),
			"yellow": (self.encoding, _("Change Subtitle Encoding")),
			"blue": (self.color, _("Change Subtitle Color")),
		}, -2)
		
		self["key_red"] = Button(_("Reset"))
		self["key_yellow"] = Button(_("Encoding"))
		self["key_blue"] = Button(_("Color"))
		self["navigation"] = Button(_("Use the navigation buttons on the remote to move the subtitles around"))
		
		self.service = self.session.nav.getCurrentService()

	def getServiceInterface(self, iface):
		service = self.service
		if service:
			attr = getattr(service, iface, None)
			if callable(attr):
				return attr()
			return None	

	def up(self):
		keys = self.getServiceInterface("keys")
		keys.keyPressed(iServiceKeys.keyUp)

	def down(self):
		keys = self.getServiceInterface("keys")
		keys.keyPressed(iServiceKeys.keyDown)

	def left(self):
		keys = self.getServiceInterface("keys")
		keys.keyPressed(iServiceKeys.keyLeft)

	def right(self):
		keys = self.getServiceInterface("keys")
		keys.keyPressed(iServiceKeys.keyRight)

	def increase(self):
		keys = self.getServiceInterface("keys")
		keys.keyPressed(iServiceKeys.keyUser)

	def decrease(self):
		keys = self.getServiceInterface("keys")
		keys.keyPressed(iServiceKeys.keyUser+1)

	def reset(self):
		keys = self.getServiceInterface("keys")
		keys.keyPressed(iServiceKeys.keyUser+4)

	def encoding(self):
		keys = self.getServiceInterface("keys")
		keys.keyPressed(iServiceKeys.keyUser+2)

	def color(self):
		keys = self.getServiceInterface("keys")
		keys.keyPressed(iServiceKeys.keyUser+3)
