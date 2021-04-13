from enigma import eTimer, eWidget, eRect, eServiceReference, iServiceInformation, iPlayableService, ePicLoad
from enigma import RT_VALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, gFont, eListbox,ePoint, eListboxPythonMultiContent, eServiceCenter
from Components.MenuList import MenuList

from Components.GUIComponent import GUIComponent
from Screens.Screen import Screen
from Screens.ServiceInfo import ServiceInfoList, ServiceInfoListEntry
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Components.Pixmap import Pixmap, MovingPixmap
from Components.Label import Label
from Screens.ChoiceBox import ChoiceBox
from Screens.InputBox import InputBox

from ServiceReference import ServiceReference

from Components.Button import Button
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from Screens.MessageBox import MessageBox
from Screens.HelpMenu import HelpableScreen

from Components.ServicePosition import ServicePositionGauge
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Playlist import PlaylistIOInternal, PlaylistIOM3U, PlaylistIOPLS

from Components.ConfigList import ConfigList, ConfigListScreen
from Components.config import *

from Tools.Directories import resolveFilename, fileExists, pathExists, createDir, SCOPE_MEDIA, SCOPE_PLAYLIST, SCOPE_SKIN_IMAGE
from Components.AVSwitch import AVSwitch
from Screens.InfoBar import MoviePlayer
from Plugins.Plugin import PluginDescriptor

from MC_Filelist import FileList

import os
from os import path as os_path, remove as os_remove, listdir as os_listdir

from enigma import eListboxPythonStringContent, eListbox

config.plugins.mc_ap = ConfigSubsection()
config.plugins.mc_ap.showMvi = ConfigYesNo(default=True)
config.plugins.mc_ap.mvi_delay = ConfigInteger(default=10, limits=(5, 999))
config.plugins.mc_ap.showPreview = ConfigYesNo(default=False)
config.plugins.mc_ap.preview_delay = ConfigInteger(default=5, limits=(1, 30))
config.plugins.mc_ap.lastDir = ConfigText(default='mountpoint')

playlist = []

def getAspect():
	val = AVSwitch().getAspectRatioSetting()
	return val/2
	
#------------------------------------------------------------------------------------------

def PlaylistEntryComponent(serviceref):
        res = [ serviceref ]
        text = serviceref.getName()
        if text is "":
                text = os_path.split(serviceref.getPath().split('/')[-1])[1]
        res.append((eListboxPythonMultiContent.TYPE_TEXT,25, 1, 470, 22, 0, RT_VALIGN_CENTER, text))

        return res

class PlayList(MenuList):
        def __init__(self, enableWrapAround=False):
                MenuList.__init__(self, playlist, enableWrapAround, eListboxPythonMultiContent)
                self.l.setFont(0, gFont("Regular", 18))
                self.l.setItemHeight(23)
                MC_AudioPlayer.currPlaying = -1
                self.oldCurrPlaying = -1
                self.serviceHandler = eServiceCenter.getInstance()

        def clear(self):
                del self.list[:]
                self.l.setList(self.list)
                MC_AudioPlayer.currPlaying = -1
                self.oldCurrPlaying = -1

        def getSelection(self):
                return self.l.getCurrentSelection()[0]

        def addFile(self, serviceref):
                self.list.append(PlaylistEntryComponent(serviceref))

        def updateFile(self, index, newserviceref):
                if index < len(self.list):
                    self.list[index] = PlaylistEntryComponent(newserviceref, STATE_NONE)

        def deleteFile(self, index):
                if MC_AudioPlayer.currPlaying >= index:
                        MC_AudioPlayer.currPlaying -= 1
                del self.list[index]

        def setCurrentPlaying(self, index):
                self.oldCurrPlaying = MC_AudioPlayer.currPlaying
                MC_AudioPlayer.currPlaying = index
                self.moveToIndex(index)

        def updateState(self, state):
                if len(self.list) > self.oldCurrPlaying and self.oldCurrPlaying != -1:
                        self.list[self.oldCurrPlaying] = PlaylistEntryComponent(self.list[self.oldCurrPlaying][0], STATE_NONE)
                if MC_AudioPlayer.currPlaying != -1 and MC_AudioPlayer.currPlaying < len(self.list):
                        self.list[MC_AudioPlayer.currPlaying] = PlaylistEntryComponent(self.list[MC_AudioPlayer.currPlaying][0], state)
                self.updateList()

        def playFile(self):
                self.updateState(STATE_PLAY)

        def pauseFile(self):
                self.updateState(STATE_PAUSE)

        def stopFile(self):
                self.updateState(STATE_STOP)

        def rewindFile(self):
                self.updateState(STATE_REWIND)

        def forwardFile(self):
                self.updateState(STATE_FORWARD)

        GUI_WIDGET = eListbox
		
        def updateList(self):
                self.l.setList(self.list)

        def getCurrentIndex(self):
                return MC_AudioPlayer.currPlaying

        def getCurrentEvent(self):
                l = self.l.getCurrentSelection()
                return l and self.serviceHandler.info(l[0]).getEvent(l[0])

        def getCurrent(self):
                l = self.l.getCurrentSelection()
                return l and l[0]

        def getServiceRefList(self):
                return [ x[0] for x in self.list ]

        def __len__(self):
                return len(self.list)


class MC_AudioPlayer(Screen, HelpableScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		
		self.isVisible = True

		self.coverArtFileName = ""
		
		self["key_red"] = Button(_(" "))
		self["key_green"] = Button(_(" "))
		self["key_yellow"] = Button(_("Add to Playlist"))
		self["key_blue"] = Button(_("Go to Playlist"))
		
		self["fileinfo"] = Label()
		self["coverArt"] = MediaPixmap()
		
		self["currentfolder"] = Label()

		self["play"] = Pixmap()
		self["stop"] = Pixmap()

		self["curplayingtitle"] = Label()
		
		self.PlaySingle = 0
		
		MC_AudioPlayer.STATE = "NONE"
		
		self.playlist = PlayList()
		self["playlist"] = self.playlist
		MC_AudioPlayer.playlistplay = 0
		MC_AudioPlayer.currPlaying = -1
		
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evStopped: self.doEOF,
				iPlayableService.evEOF: self.doEOF,
				iPlayableService.evUpdatedInfo: self.__evUpdatedInfo,
				iPlayableService.evUser+11: self.__evDecodeError,
				iPlayableService.evUser+12: self.__evPluginError,
				iPlayableService.evUser+13: self["coverArt"].embeddedCoverArt
			})
			
		self["actions"] = HelpableActionMap(self, "MC_AudioPlayerActions", 
			{
				"ok": (self.KeyOK, _("Play selected file")),
				"cancel": (self.Exit, _("Exit Audio Player")),
				"left": (self.leftUp, _("List Top")),
				"right": (self.rightDown, _("List Bottom")),
				"up": (self.up, _("List up")),
				"down": (self.down, _("List down")),
				"menu": (self.showMenu, _("File / Folder Options")),
				"video": (self.visibility, _("Show / Hide Player")),
				"info": (self.showFileInfo, _("Show File Info")),
				"stop": (self.StopPlayback, _("Stop Playback")),
				#"red": (self.Exit, _("Exit Music")),
				#"green": (self.KeyPlayAll, _("Play All")),
				"yellow": (self.addFiletoPls, _("Add file to playlist")),
				"blue": (self.Playlists, _("Playlists")),
				"next": (self.KeyNext, _("Next song")),
				"previous": (self.KeyPrevious, _("Previous song")),
				"playpause": (self.PlayPause, _("Play / Pause")),
				"stop": (self.StopPlayback, _("Stop")),
				"seekFwd": (self.seekFwd, _("skip forward")),
				"seekBwd": (self.seekBwd, _("skip backward")),
			}, -2)

		self.playlistparsers = {}
		self.addPlaylistParser(PlaylistIOM3U, "m3u")
		self.addPlaylistParser(PlaylistIOPLS, "pls")
		self.addPlaylistParser(PlaylistIOInternal, "e2pls")
		
		currDir = config.plugins.mc_ap.lastDir.value
		if not pathExists(currDir):
			currDir = None

		self["currentfolder"].setText(str(currDir))
		
		self.filelist = FileList(currDir, showMountpoints=True, useServiceRef=True, showDirectories=True, showFiles=True, matchingPattern="(?i)^.*\.(mp3|ogg|wav|wave|flac|m4a|m3u|pls|e2pls)", additionalExtensions="4098:m3u 4098:e2pls 4098:pls")
		self["filelist"] = self.filelist
		self["thumbnail"] = Pixmap()
		
	def up(self):
		self["filelist"].up()

	def down(self):
		self["filelist"].down()
		
	def leftUp(self):
		self["filelist"].pageUp()
		
	def rightDown(self):
		self["filelist"].pageDown()

	def KeyOK(self):
		if self["filelist"].canDescent():
			self.filelist.descent()
			self["currentfolder"].setText(str(self.filelist.getCurrentDirectory()))
		else:
			if self.filelist.getServiceRef().type == 4098: # playlist
				ServiceRef = self.filelist.getServiceRef()
				extension = ServiceRef.getPath()[ServiceRef.getPath().rfind('.') + 1:]
				if self.playlistparsers.has_key(extension):
					self.playlist.clear()
					playlist = self.playlistparsers[extension]()
					list = playlist.open(ServiceRef.getPath())
					for x in list:
						self.playlist.addFile(x.ref)
				self.playlist.updateList()
				MC_AudioPlayer.currPlaying = 0
				self.PlayServicepls()
			else:
				self.PlaySingle = 0
				self.PlayService()

	def PlayPause(self):
		if MC_AudioPlayer.STATE == "PLAY":
			service = self.session.nav.getCurrentService()
			pausable = service.pause()
			pausable.pause()
			MC_AudioPlayer.STATE = "PAUSED"
		elif MC_AudioPlayer.STATE == "PAUSED" or MC_AudioPlayer.STATE == "SEEKBWD" or MC_AudioPlayer.STATE == "SEEKFWD":
			service = self.session.nav.getCurrentService()
			pausable = service.pause()
			pausable.unpause()
			MC_AudioPlayer.STATE = "PLAY"
		else:
			self.KeyOK()
			
	def seekFwd(self):
		if MC_AudioPlayer.STATE == "PLAY" or MC_AudioPlayer.STATE == "SEEKBWD":
			service = self.session.nav.getCurrentService()
			pausable = service.pause()
			pausable.setFastForward(4)
			MC_AudioPlayer.STATE = "SEEKFWD"

	def seekBwd(self):
		if MC_AudioPlayer.STATE == "PLAY" or MC_AudioPlayer.STATE == "SEEKFWD":
			service = self.session.nav.getCurrentService()
			pausable = service.pause()
			pausable.setFastForward(-4)
			MC_AudioPlayer.STATE = "SEEKBWD"

	def KeyNext(self):
		if MC_AudioPlayer.STATE != "NONE":
			if MC_AudioPlayer.playlistplay == 1:
				next = self.playlist.getCurrentIndex() + 1
				if next < len(self.playlist):
					MC_AudioPlayer.currPlaying = MC_AudioPlayer.currPlaying + 1
				else:
					MC_AudioPlayer.currPlaying = 0
				self.PlayServicepls()
			
			else:
				print "Play Next File ..."
				self.down()
				self.PlayService()
		
	def KeyPrevious(self):
		if MC_AudioPlayer.STATE != "NONE":
			if MC_AudioPlayer.playlistplay == 1:
				next = self.playlist.getCurrentIndex() - 1
				if next != -1:
					MC_AudioPlayer.currPlaying = MC_AudioPlayer.currPlaying - 1
				else:
					MC_AudioPlayer.currPlaying = 0
				self.PlayServicepls()
			
			else:
				print "Play previous File ..."
				self.up()
				self.PlayService()

	def KeyPlayAll(self):
		if not self["filelist"].canDescent():
			self.PlaySingle = 0
			self.PlayService()

	def KeyExit(self):
		self.filelist.gotoParent()

	def KeyYellow(self):
		print "yellow"
			
	def visibility(self, force=1):
		if self.isVisible == True:
			self.isVisible = False
			self.hide()
		else:
			self.isVisible = True
			self.show()
	
	def Playlists(self):
		self.session.openWithCallback(self.updateFileInfo, MC_AudioPlaylist)
		
	def PlayService(self):
		playlistplay = 0
		self.session.nav.playService(self["filelist"].getServiceRef())
		MC_AudioPlayer.STATE = "PLAY"
		self.updateFileInfo()
		
		path = self["filelist"].getCurrentDirectory() + self["filelist"].getFilename()
		self["coverArt"].updateCoverArt(path)

	def PlayServicepls(self):
		MC_AudioPlayer.playlistplay = 1
		
		x = self.playlist.getCurrentIndex()
		print "x is %s" % (x)
		x = len(self.playlist)
		print "x is %s" % (x)
		ref = self.playlist.getServiceRefList()[self.playlist.getCurrentIndex()]
		self.session.nav.playService(ref)
		MC_AudioPlayer.STATE = "PLAY"
		self.updateFileInfo()
		
		#path = self["filelist"].getCurrentDirectory() + self["filelist"].getFilename()
		#self["coverArt"].updateCoverArt(path)

	def StopPlayback(self):
		if self.isVisible == False:
			self.show()
			self.isVisible = True
		
		if self.session.nav.getCurrentService() is None:
			return
		else:
			self.session.nav.stopService()
			MC_AudioPlayer.STATE = "NONE"

	def showFileInfo(self):
		if self["filelist"].canDescent():
			return
		else:
			self.session.open(MC_AudioInfoView, self["filelist"].getCurrentDirectory() + self["filelist"].getFilename() , self["filelist"].getFilename(), self["filelist"].getServiceRef())			

	def JumpToFolder(self, jumpto=None):
		if jumpto is None:
			return
		else:
			self["filelist"].changeDir(jumpto)
			self["currentfolder"].setText(("%s") % (jumpto))

	def updateFileInfo(self):
		currPlay = self.session.nav.getCurrentService()
		if currPlay is not None:
			sTitle = currPlay.info().getInfoString(iServiceInformation.sTagTitle)
			sArtist = currPlay.info().getInfoString(iServiceInformation.sTagArtist)
			sAlbum = currPlay.info().getInfoString(iServiceInformation.sTagAlbum)
			sGenre = currPlay.info().getInfoString(iServiceInformation.sTagGenre)
			sComment = currPlay.info().getInfoString(iServiceInformation.sTagComment)
			sYear = currPlay.info().getInfoString(iServiceInformation.sTagDate)
			
			if sTitle == "":
				sTitle = currPlay.info().getName().split('/')[-1]
					
			self["fileinfo"].setText(_("Title:") + " " + sTitle + "\n" + _("Artist:") + " " +  sArtist + "\n" + _("Album:") + " " + sAlbum + "\n" + _("Genre:") + " " + sGenre + "\n" + _("Comment:") + " " + sComment)
			self["curplayingtitle"].setText(_("Now Playing:") + " " + sArtist + " - " + sTitle)

	def addFiletoPls(self):
		if self.filelist.getServiceRef().type == 4098: # playlist
			ServiceRef = self.filelist.getServiceRef()
			extension = ServiceRef.getPath()[ServiceRef.getPath().rfind('.') + 1:]
			if self.playlistparsers.has_key(extension):
				playlist = self.playlistparsers[extension]()
				list = playlist.open(ServiceRef.getPath())
				for x in list:
					self.playlist.addFile(x.ref)
				self.playlist.updateList()
		else:
			self.playlist.addFile(self.filelist.getServiceRef())
			self.playlist.updateList()

	def addDirtoPls(self, directory, recursive=True):
		print "copyDirectory", directory
		if directory == '/':
			print "refusing to operate on /"
			return
		filelist = FileList(directory, useServiceRef=True, showMountpoints=False, isTop=True)

		for x in filelist.getFileList():
			if x[0][1] == True: #isDir
				if recursive:
					if x[0][0] != directory:
						self.copyDirectory(x[0][0])
			elif filelist.getServiceRef() and filelist.getServiceRef().type == 4097:
				self.playlist.addFile(x[0][0])
		self.playlist.updateList()

	def deleteFile(self):
		self.service = self.filelist.getServiceRef()
		if self.service.type != 4098 and self.session.nav.getCurrentlyPlayingServiceReference() is not None:
			if self.service == self.session.nav.getCurrentlyPlayingServiceReference():
				self.StopPlayback()
		
		self.session.openWithCallback(self.deleteFileConfirmed, MessageBox, _("Do you really want to delete this file ?"))

	def deleteFileConfirmed(self, confirmed):
		if confirmed:
			delfile = self["filelist"].getFilename()
			os.remove(delfile)
	
	def deleteDir(self):
		self.session.openWithCallback(self.deleteDirConfirmed, MessageBox, _("Do you really want to delete this directory and it's content ?"))
		
	def deleteDirConfirmed(self, confirmed):
		if confirmed:
			import shutil
			deldir = self.filelist.getSelection()[0]
			shutil.rmtree(deldir)
	
	def addPlaylistParser(self, parser, extension):
		self.playlistparsers[extension] = parser

	def Exit(self):
		if self.isVisible == False:
			self.visibility()
			return
		
		try:
			config.plugins.mc_ap.lastDir.value = self.filelist.getCurrentDirectory()
		except:
			config.plugins.mc_ap.lastDir.value = 'mountpoint'
		config.plugins.mc_ap.save()
		configfile.save()
		
		del self["coverArt"].picload
		self.session.nav.stopService()
		MC_AudioPlayer.STATE = "NONE"
		self.close()

	def showMenu(self):
		menu = []
		if self.filelist.canDescent():
			x = self.filelist.getName()
			if x == "..":
				return
			menu.append((_("add directory to playlist"), "copydir"))
			menu.append((_("delete directory"), "deletedir"))
		else:
			menu.append((_("add file to playlist"), "copyfile"))
			menu.append((_("add file to playlist and play"), "copyandplay"))
			menu.append((_("add all files in directory to playlist"), "copyfiles"))
			menu.append((_("delete file"), "deletefile"))
		self.session.openWithCallback(self.menuCallback, ChoiceBox, title="", list=menu)

	def menuCallback(self, choice):
		if choice is None:
			return

		if choice[1] == "copydir":
			self.addDirtoPls(self.filelist.getSelection()[0])
		elif choice[1] == "deletedir":
			self.deleteDir()
		elif choice[1] == "copyfile":
			self.addFiletoPls()
		elif choice[1] == "copyandplay":
			self.addFiletoPls()
			MC_AudioPlayer.currPlaying = len(self.playlist) - 1
			print "curplay is %s" % (MC_AudioPlayer.currPlaying)
			self.PlayServicepls()
		elif choice[1] == "copyfiles":
			self.addDirtoPls(os_path.dirname(self.filelist.getSelection()[0].getPath()) + "/", recursive=False)
		elif choice[1] == "deletefile":
			self.deleteFile()
		
	def doEOF(self):
		print "MediaCenter: EOF Event AUDIO..."
		if MC_AudioPlayer.playlistplay == 1:
			next = self.playlist.getCurrentIndex() + 1
			if next < len(self.playlist):
				MC_AudioPlayer.currPlaying = MC_AudioPlayer.currPlaying + 1
				self.PlayServicepls()
		
		elif self.PlaySingle == 0:
			print "Play Next File ..."
			self.down()
			if not self["filelist"].canDescent():
				self.PlayService()
			else:
				self.StopPlayback()
		else:
			print "Stop Playback ..."
			self.StopPlayback()

	def __evUpdatedInfo(self):
		self.updateFileInfo()

	def __evDecodeError(self):
		currPlay = self.session.nav.getCurrentService()
		sVideoType = currPlay.info().getInfoString(iServiceInformation.sVideoType)
		print "[__evDecodeError] video-codec %s can't be decoded by hardware" % (sVideoType)
		self.session.open(MessageBox, _("This Dreambox can't decode %s video streams!") % sVideoType, type=MessageBox.TYPE_INFO,timeout=20 )

	def __evPluginError(self):
		currPlay = self.session.nav.getCurrentService()
		message = currPlay.info().getInfoString(iServiceInformation.sUser+12)
		print "[__evPluginError]" , message
		self.session.open(MessageBox, message, type=MessageBox.TYPE_INFO,timeout=20 )		


class MC_AudioPlaylist(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["PositionGauge"] = ServicePositionGauge(self.session.nav)
		
		self["key_red"] = Button(_(" "))
		self["key_green"] = Button(" ")
		self["key_yellow"] = Button(" ")
		self["key_blue"] = Button(_("File Browser"))
		
		self["fileinfo"] = Label()
		self["coverArt"] = MediaPixmap()
		
		self["currentfolder"] = Label()
		self["currentfavname"] = Label()
		self.curfavfolder = -1

		self["play"] = Pixmap()
		self["stop"] = Pixmap()

		self["curplayingtitle"] = Label()
		self.updateFileInfo()
		self.PlaySingle = 0
		
		self.isVisible = True
		
		self.playlist = PlayList()
		self["playlist"] = self.playlist
		
		self.playlistIOInternal = PlaylistIOInternal()
		self.playlistparsers = {}
		self.addPlaylistParser(PlaylistIOM3U, "m3u")
		self.addPlaylistParser(PlaylistIOPLS, "pls")
		self.addPlaylistParser(PlaylistIOInternal, "e2pls")
		
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evEOF: self.updateFileInfo,
				#iPlayableService.evStopped: self.StopPlayback,
				#iPlayableService.evUser+11: self.__evDecodeError,
				#iPlayableService.evUser+12: self.__evPluginError,
				iPlayableService.evUser+13: self["coverArt"].embeddedCoverArt
			})
		
		self["actions"] = HelpableActionMap(self, "MC_AudioPlayerActions", 
			{
				"ok": (self.KeyOK, _("Play from selected file")),
				"cancel": (self.Exit, _("Exit Audio Player")),
				"left": (self.leftUp, _("List Top")),
				"right": (self.rightDown, _("List Bottom")),
				"up": (self.up, _("List up")),
				"down": (self.down, _("List down")),
				"menu": (self.showMenu, _("File / Folder Options")),
				"video": (self.visibility, _("Show / Hide Player")),
				"info": (self.showFileInfo, _("Show File Info")),
				"stop": (self.StopPlayback, _("Stop Playback")),
				#"red": (self.Exit, _("Close Playlist")),
				#"green": (self.close, _("Play All")),
				#"yellow": (self.Exit, _("Playlists")),
				"blue": (self.Exit, _("Close Playlist")),
				"next": (self.KeyNext, _("Next song")),
				"previous": (self.KeyPrevious, _("Previous song")),
				"playpause": (self.PlayPause, _("Play / Pause")),
				"stop": (self.StopPlayback, _("Stop")),
			}, -2)
		
	def up(self):
		self["playlist"].up()

	def down(self):
		self["playlist"].down()
		
	def leftUp(self):
		self["playlist"].pageUp()
		
	def rightDown(self):
		self["playlist"].pageDown()

	def KeyOK(self):
		if len(self.playlist.getServiceRefList()):
			x = self.playlist.getSelectionIndex()
			print "x is %s" % (x)
			self.playlist.setCurrentPlaying(self.playlist.getSelectionIndex())
			x = self.playlist.getCurrentIndex()
			print "x is %s" % (x)
			x = len(self.playlist)
			print "x is %s" % (x)
			self.PlayService()

	def PlayPause(self):
		if MC_AudioPlayer.STATE != "NONE":
			if MC_AudioPlayer.STATE == "PLAY":
				service = self.session.nav.getCurrentService()
				pausable = service.pause()
				pausable.pause()
				MC_AudioPlayer.STATE = "PAUSED"
			elif MC_AudioPlayer.STATE == "PAUSED":
				service = self.session.nav.getCurrentService()
				pausable = service.pause()
				pausable.unpause()
				MC_AudioPlayer.STATE = "PLAY"
			else:
				self.KeyOK()

	def KeyNext(self):
		if MC_AudioPlayer.STATE != "NONE":
			if MC_AudioPlayer.playlistplay == 1:
				next = self.playlist.getCurrentIndex() + 1
				if next < len(self.playlist):
					MC_AudioPlayer.currPlaying = MC_AudioPlayer.currPlaying + 1
				else:
					MC_AudioPlayer.currPlaying = 0
				self.PlayService()
			
			else:
				self.session.open(MessageBox, _("You have to close playlist before you can go to the next song while playing from file browser."), MessageBox.TYPE_ERROR)
		
	def KeyPrevious(self):
		if MC_AudioPlayer.playlistplay == 1:
			next = self.playlist.getCurrentIndex() - 1
			if next != -1:
				MC_AudioPlayer.currPlaying = MC_AudioPlayer.currPlaying - 1
			else:
				MC_AudioPlayer.currPlaying = 0
			self.PlayService()
		
		else:
			self.session.open(MessageBox, _("You have to close playlist before you can go to the previous song while playing from file browser."), MessageBox.TYPE_ERROR)
			
	def PlayService(self):
		MC_AudioPlayer.playlistplay = 1
		
		ref = self.playlist.getServiceRefList()[self.playlist.getCurrentIndex()]
		#newref = eServiceReference(4370, 0, ref.getPath())
		self.session.nav.playService(ref)
		MC_AudioPlayer.STATE = "PLAY"
		self.updateFileInfo()
			
		#self["play"].instance.setPixmapFromFile("/usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/icons/play_enabled.png")
		#self["stop"].instance.setPixmapFromFile("/usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/icons/stop_disabled.png")

		#path = self["filelist"].getCurrentDirectory() + self["filelist"].getFilename()
		#self["coverArt"].updateCoverArt(path)
				
	def StopPlayback(self):

		if self.isVisible == False:
			self.show()
			self.isVisible = True
		
		if self.session.nav.getCurrentService() is None:
			return
		
		else:
			self.session.nav.stopService()
			MC_AudioPlayer.STATE = "NONE"
			
			#self["play"].instance.setPixmapFromFile("/usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/icons/play_disabled.png")
			#self["stop"].instance.setPixmapFromFile("/usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/icons/stop_enabled.png")

	def visibility(self, force=1):
		if self.isVisible == True:
			self.isVisible = False
			self.hide()
		else:
			self.isVisible = True
			self.show()
			#self["list"].refresh()

	def showFileInfo(self):
		if self["filelist"].canDescent():
			return
		else:
			self.session.open(MC_AudioInfoView, self["filelist"].getCurrentDirectory() + self["filelist"].getFilename() , self["filelist"].getFilename(), self["filelist"].getServiceRef())
	
	def Settings(self):
		self.session.open(AudioPlayerSettings)

	def Exit(self):
		self.close()

	def updateFileInfo(self):
		print "DOING EOF FOR 2"
		currPlay = self.session.nav.getCurrentService()
		if currPlay is not None:
			sTitle = currPlay.info().getInfoString(iServiceInformation.sTagTitle)
			sArtist = currPlay.info().getInfoString(iServiceInformation.sTagArtist)
			sAlbum = currPlay.info().getInfoString(iServiceInformation.sTagAlbum)
			sGenre = currPlay.info().getInfoString(iServiceInformation.sTagGenre)
			sComment = currPlay.info().getInfoString(iServiceInformation.sTagComment)
			sYear = currPlay.info().getInfoString(iServiceInformation.sTagDate)
			
			if sTitle == "":
				sTitle = currPlay.info().getName().split('/')[-1]
					
			self["fileinfo"].setText(_("Title:") + " " + sTitle + "\n" + _("Artist:") + " " +  sArtist + "\n" + _("Album:") + " " + sAlbum + "\n" + _("Genre:") + " " + sGenre + "\n" + _("Comment:") + " " + sComment)
			self["curplayingtitle"].setText(_("Now Playing:") + " " + sArtist + " - " + sTitle)

	def save_playlist(self):
		self.session.openWithCallback(self.save_pls,InputBox, title=_("Please enter filename (empty = use current date)"),windowTitle=_("Save Playlist"))

	def save_pls(self, name):
		if name is not None:
			name = name.strip()
			if name == "":
				name = strftime("%y%m%d_%H%M%S")
			name += ".e2pls"
			self.playlistIOInternal.clear()
			for x in self.playlist.list:
				self.playlistIOInternal.addService(ServiceReference(x[0]))
			self.playlistIOInternal.save(resolveFilename(SCOPE_PLAYLIST) + name)

	def load_playlist(self):
		listpath = []
		playlistdir = resolveFilename(SCOPE_PLAYLIST)
		try:
			for i in os_listdir(playlistdir):
				listpath.append((i,playlistdir + i))
		except IOError,e:
			print "Error while scanning subdirs ",e
		self.session.openWithCallback(self.load_pls, ChoiceBox, title=_("Please select a playlist..."), list=listpath)

	def load_pls(self,path):
		if path is not None:
			self.playlist.clear()
			extension = path[0].rsplit('.',1)[-1]
			if self.playlistparsers.has_key(extension):
				playlist = self.playlistparsers[extension]()
				list = playlist.open(path[1])
				for x in list:
					self.playlist.addFile(x.ref)
			self.playlist.updateList()

	def delete_saved_playlist(self):
		listpath = []
		playlistdir = resolveFilename(SCOPE_PLAYLIST)
		try:
			for i in os_listdir(playlistdir):
				listpath.append((i,playlistdir + i))
		except IOError,e:
			print "Error while scanning subdirs ",e
		self.session.openWithCallback(self.delete_saved_pls, ChoiceBox, title=_("Please select a playlist to delete..."), list=listpath)

	def delete_saved_pls(self,path):
		if path is not None:
			self.delname = path[1]
			self.session.openWithCallback(self.delete_saved_pls_conf, MessageBox, _("Do you really want to delete %s?") % (path[1]))

	def delete_saved_pls_conf(self, confirmed):
		if confirmed:
			try:
				os_remove(self.delname)
			except OSError,e:
				print "delete failed:", e
				self.session.open(MessageBox, _("Delete failed!"), MessageBox.TYPE_ERROR)

	def addPlaylistParser(self, parser, extension):
		self.playlistparsers[extension] = parser


	def showMenu(self):
		menu = []
		menu.append((_("delete from playlist"), "deleteentry"))
		menu.append((_("clear playlist"), "clear"))
		menu.append((_("load playlist"), "loadplaylist"))
		menu.append((_("save playlist"), "saveplaylist"))
		menu.append((_("delete saved playlist"), "deleteplaylist"))
		self.session.openWithCallback(self.menuCallback, ChoiceBox, title="", list=menu)

	def menuCallback(self, choice):
		if choice is None:
			return

		if choice[1] == "deleteentry":
			self.playlist.deleteFile(self.playlist.getSelectionIndex())
			self.playlist.updateList()
		elif choice[1] == "clear":
			self.playlist.clear()
		elif choice[1] == "loadplaylist":
			self.load_playlist()
		elif choice[1] == "saveplaylist":
			self.save_playlist()
		elif choice[1] == "deleteplaylist":
			self.delete_saved_playlist()
			
#-----------------------------------------------------------------------------------------------------------------------------

class MediaPixmap(Pixmap):
	def __init__(self):
		Pixmap.__init__(self)
		self.coverArtFileName = ""
		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.paintCoverArtPixmapCB)
		self.coverFileNames = ["folder.png", "folder.jpg"]

	def applySkin(self, desktop, screen):
		from Tools.LoadPixmap import LoadPixmap
		noCoverFile = None
		if self.skinAttributes is not None:
			for (attrib, value) in self.skinAttributes:
				if attrib == "pixmap":
					noCoverFile = value
					break
		if noCoverFile is None:
			noCoverFile = resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/no_coverArt.png")
		self.noCoverPixmap = LoadPixmap(noCoverFile)
		return Pixmap.applySkin(self, desktop, screen)

	def onShow(self):
		Pixmap.onShow(self)
		sc = AVSwitch().getFramebufferScale()
		#0=Width 1=Height 2=Aspect 3=use_cache 4=resize_type 5=Background(#AARRGGBB)
		self.picload.setPara((self.instance.size().width(), self.instance.size().height(), sc[0], sc[1], False, 1, "#00000000"))

	def paintCoverArtPixmapCB(self, picInfo=None):
		ptr = self.picload.getData()
		if ptr != None:
			self.instance.setPixmap(ptr.__deref__())

	def updateCoverArt(self, path):
		while not path.endswith("/"):
			path = path[:-1]
		new_coverArtFileName = None
		for filename in self.coverFileNames:
			if fileExists(path + filename):
				new_coverArtFileName = path + filename
		if self.coverArtFileName != new_coverArtFileName:
			self.coverArtFileName = new_coverArtFileName
			if new_coverArtFileName:
				self.picload.startDecode(self.coverArtFileName)
			else:
				self.showDefaultCover()

	def showDefaultCover(self):
		self.instance.setPixmap(self.noCoverPixmap)

	def embeddedCoverArt(self):
		print "[embeddedCoverArt] found"
		self.coverArtFileName = "/tmp/.id3coverart"
		self.picload.startDecode(self.coverArtFileName)



#------------------------------------------------------------------------------------------

class AudioPlayerSettings(Screen):
	skin = """
		<screen position="160,220" size="400,120" title="Audioplayer Settings" >
			<widget name="configlist" position="10,10" size="380,100" />
		</screen>"""
	
	def __init__(self, session):
		self.skin = AudioPlayerSettings.skin
		Screen.__init__(self, session)

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.close,
			"cancel": self.close,
			"left": self.keyLeft,
			"right": self.keyRight,
			"0": self.keyNumber,
			"1": self.keyNumber,
			"2": self.keyNumber,
			"3": self.keyNumber,
			"4": self.keyNumber,
			"5": self.keyNumber,
			"6": self.keyNumber,
			"7": self.keyNumber,
			"8": self.keyNumber,
			"9": self.keyNumber
		}, -1)
				
		self.list = []
		self["configlist"] = ConfigList(self.list)
		self.list.append(getConfigListEntry(_("Screensaver Enable"), config.plugins.mc_ap.showMvi))
		self.list.append(getConfigListEntry(_("Screensaver Interval"), config.plugins.mc_ap.mvi_delay))

	def keyLeft(self):
		self["configlist"].handleKey(KEY_LEFT)

	def keyRight(self):
		self["configlist"].handleKey(KEY_RIGHT)
		
	def keyNumber(self, number):
		self["configlist"].handleKey(KEY_0 + number)


#-------------------------------------------------------------------------------------------------
		
#--------------------------------------------------------------------------------------------------

class MC_AudioInfoView(Screen):
	skin = """
		<screen position="80,130" size="560,320" title="View Audio Info" >
			<widget name="infolist" position="5,5" size="550,310" selectionDisabled="1" />
		</screen>"""
	
	def __init__(self, session, fullname, name, ref):
		self.skin = MC_AudioInfoView.skin
		Screen.__init__(self, session)
		
		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"cancel": self.close,
			"ok": self.close
		}, -1)
		
		tlist = [ ]
		self["infolist"] = ServiceInfoList(tlist)

		currPlay = self.session.nav.getCurrentService()
		if currPlay is not None:
			stitle = currPlay.info().getInfoString(iServiceInformation.sTagTitle)
			
			if stitle == "":
				stitle = currPlay.info().getName().split('/')[-1]

			tlist.append(ServiceInfoListEntry(_("Title:") + " ", stitle))
			tlist.append(ServiceInfoListEntry(_("Artist:") + " ", currPlay.info().getInfoString(iServiceInformation.sTagArtist)))
			tlist.append(ServiceInfoListEntry(_("Album:") + " ", currPlay.info().getInfoString(iServiceInformation.sTagAlbum)))
			tlist.append(ServiceInfoListEntry(_("Genre:") + " ", currPlay.info().getInfoString(iServiceInformation.sTagGenre)))
			tlist.append(ServiceInfoListEntry(_("Year:") + " ", currPlay.info().getInfoString(iServiceInformation.sTagDate)))
			tlist.append(ServiceInfoListEntry(_("Comment:") + " ", currPlay.info().getInfoString(iServiceInformation.sTagComment)))
