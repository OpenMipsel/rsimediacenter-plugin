from enigma import ePicLoad, eTimer, getDesktop, eServiceReference
from Screens.Screen import Screen
from Screens.ServiceInfo import ServiceInfoList, ServiceInfoListEntry
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Components.Pixmap import Pixmap, MovingPixmap
from Components.Label import Label
from Components.Button import Button
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.HelpMenu import HelpableScreen

from Components.ConfigList import ConfigList
from Components.config import *

from Tools.Directories import resolveFilename, fileExists, pathExists, createDir, SCOPE_MEDIA
from Components.AVSwitch import AVSwitch

from Plugins.Plugin import PluginDescriptor

from MC_Filelist import FileList

import os
from os import path as os_path

config.plugins.mc_pp = ConfigSubsection()
config.plugins.mc_pp.slidetime = ConfigInteger(default=10, limits=(5, 60))
config.plugins.mc_pp.resize = ConfigSelection(default="0", choices=[("0", _("simple")), ("1", _("better"))])
config.plugins.mc_pp.cache = ConfigEnableDisable(default=True)
config.plugins.mc_pp.lastDir = ConfigText(default='mountpoint')
config.plugins.mc_pp.rotate = ConfigSelection(default="0", choices=[("0", _("none")), ("1", _("manual")), ("2", _("by Exif"))])
config.plugins.mc_pp.ThumbWidth = ConfigInteger(default=145, limits=(1, 999))
config.plugins.mc_pp.ThumbHeight = ConfigInteger(default=120, limits=(1, 999))
config.plugins.mc_pp.bgcolor = ConfigSelection(default="#00000000", choices=[("#00000000", _("black")), ("#009eb9ff", _("blue")), ("#00ff5a51", _("red")), ("#00ffe875", _("yellow")), ("#0038FF48", _("green"))])
config.plugins.mc_pp.framesize = ConfigSlider(default=30, increment=5, limits=(5, 99))
config.plugins.mc_pp.loop = ConfigEnableDisable(default=True)


def getAspect():
	val = AVSwitch().getAspectRatioSetting()
	return val / 2


def getScale():
	return AVSwitch().getFramebufferScale()

#------------------------------------------------------------------------------------------


class MC_PictureViewer(Screen, HelpableScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)

		self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.stopService()

		# Show Background MVI
		os.system("/usr/bin/showiframe /usr/share/enigma2/black.mvi &")

		self["key_red"] = Button(_(" "))
		self["key_green"] = Button(_("Slide Show"))
		self["key_yellow"] = Button(_("Thumb View"))
		self["key_blue"] = Button(_("Settings"))

		self["currentfolder"] = Label("")
		self["currentfavname"] = Label("")
		self.curfavfolder = -1

		self["actions"] = HelpableActionMap(self, "MC_PictureViewerActions",
			{
				"ok": (self.KeyOk, _("Show Picture")),
				"cancel": (self.Exit, _("Directory Up")),
				"left": (self.leftUp, _("List Top")),
				"right": (self.rightDown, _("List Bottom")),
				"up": (self.up, _("List up")),
				"down": (self.down, _("List down")),
				"menu": (self.KeyMenu, _("File / Folder Options")),
				"info": (self.StartExif, _("Show File Info")),
				#"red": (self.Exit, _("Exit Pictures")),
				"green": (self.startslideshow, _("Start Slideshow")),
				"yellow": (self.StartThumb, _("Thumb View")),
				"blue": (self.Settings, _("Settings")),
			}, -2)

		currDir = config.plugins.mc_pp.lastDir.value
		if not pathExists(currDir):
			currDir = None

		self["currentfolder"].setText(str(currDir))

		self.filelist = FileList(currDir, showMountpoints=True, matchingPattern="(?i)^.*\.(jpeg|jpg|jpe|png|bmp)")
		self["filelist"] = self.filelist
		self["filelist"].onSelectionChanged.append(self.selectionChanged)
		self["thumbnail"] = Pixmap()
		self["datelabel"] = StaticText("")
		self["cameralabel"] = StaticText("")
		self["sizelabel"] = StaticText("")
		self["date"] = StaticText("")
		self["camera"] = StaticText("")
		self["size"] = StaticText("")
		list = []
		self["fileinfo"] = List(list, enableWrapAround=False)

		self.ThumbTimer = eTimer()
		self.ThumbTimer.callback.append(self.showThumb)

		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.showPic)

		self.onLayoutFinish.append(self.setConf)

	def startslideshow(self):
		self.session.openWithCallback(self.returnVal, MC_PicView, self.filelist.getFileList(), self.filelist.getSelectionIndex(), self.filelist.getCurrentDirectory(), True)

	def up(self):
		self["filelist"].up()

	def down(self):
		self["filelist"].down()

	def leftUp(self):
		self["filelist"].pageUp()

	def rightDown(self):
		self["filelist"].pageDown()

	def showPic(self, picInfo=""):
		ptr = self.picload.getData()
		if ptr != None:
			self["thumbnail"].instance.setPixmap(ptr.__deref__())
			self["thumbnail"].show()
		exiflist = self.picload.getInfo(self.filelist.getCurrentDirectory() + self.filelist.getFilename())
		self["datelabel"].setText("Date/Time:")
		self["cameralabel"].setText("Camera:")
		self["sizelabel"].setText("Width/Heigth:")
		try:
			self["date"].setText(exiflist[4])
		except:
			pass
		try:
			self["camera"].setText(exiflist[3])
		except:
			pass
		try:
			self["size"].setText(exiflist[5])
		except:
			pass

	def showThumb(self):
		if not self.filelist.canDescent():
			if self.filelist.getCurrentDirectory() and self.filelist.getFilename():
				if self.picload.getThumbnail(self.filelist.getCurrentDirectory() + self.filelist.getFilename()) == 1:
					self.ThumbTimer.start(500, True)

	def selectionChanged(self):
		if not self.filelist.canDescent():
			self.ThumbTimer.start(500, True)
		else:
			self["thumbnail"].hide()
			self["datelabel"].setText("")
			self["cameralabel"].setText("")
			self["sizelabel"].setText("")
			self["date"].setText("")
			self["camera"].setText("")
			self["size"].setText("")

	def KeyOk(self):
		if self.filelist.canDescent():
			self.filelist.descent()
		else:
			self.session.openWithCallback(self.returnVal, MC_PicView, self.filelist.getFileList(), self.filelist.getSelectionIndex(), self.filelist.getCurrentDirectory(), False)

	def KeyExit(self):
		self.filelist.gotoParent()

	def KeyMenu(self):
		self.ThumbTimer.stop()
		if self["filelist"].canDescent():
			if self.filelist.getCurrent()[0][1]:
				self.currentDirectory = self.filelist.getCurrent()[0][0]
				if self.currentDirectory is not None:
					foldername = self.currentDirectory.split('/')
					foldername = foldername[-2]
					self.session.open(MC_FolderOptions, self.currentDirectory, foldername)

	def StartThumb(self):
		self.session.openWithCallback(self.returnVal, MC_PicThumbViewer, self.filelist.getFileList(), self.filelist.getSelectionIndex(), self.filelist.getCurrentDirectory())

	def returnVal(self, val=0, home=False):
		if home:
			self.Exit()
		else:
			if val > 0:
				for x in self.filelist.getFileList():
					if x[0][1] == True:
						val += 1
				self.filelist.moveToIndex(val)

	def StartExif(self):
		if not self.filelist.canDescent():
			self.session.open(Pic_Exif, self.picload.getInfo(self.filelist.getCurrentDirectory() + self.filelist.getFilename()))

	def Settings(self):
		self.session.open(MC_PicSetup)

	def setConf(self):
		sc = getScale()
		self.picload.setPara((self["thumbnail"].instance.size().width(), self["thumbnail"].instance.size().height(), sc[0], sc[1], config.plugins.mc_pp.cache.value, int(config.plugins.mc_pp.resize.value), "#00000000"))

	def Exit(self):
		try:
			config.plugins.mc_pp.lastDir.value = self.filelist.getCurrentDirectory()
		except:
			config.plugins.mc_pp.lastDir.value = 'mountpoint'
		config.plugins.mc_pp.save()
		configfile.save()
		self.session.nav.playService(self.oldService)
		self.close()


#------------------------------------------------------------------------------------------
T_INDEX = 0
T_FRAME_POS = 1
T_PAGE = 2
T_NAME = 3
T_FULL = 4


class MC_PicThumbViewer(Screen, HelpableScreen):
	def __init__(self, session, piclist, lastindex, path):

		Screen.__init__(self, session)

		self["actions"] = HelpableActionMap(self, "MC_PictureViewerActions",
		{
			"ok": (self.KeyOk, _("Show Picture")),
			"cancel": (self.Exit, _("Exit Picture Viewer")),
			"left": (self.key_left, _("List Top")),
			"right": (self.key_right, _("List Bottom")),
			"up": (self.key_up, _("List up")),
			"down": (self.key_down, _("List down")),
			"info": (self.StartExif, _("Show File Info")),
			"green": (self.startslideshow, _("Start Slideshow")),
			"yellow": (self.close, _("File View")),
			"blue": (self.Settings, _("Settings")),
			#"red": (self.Home, _("Go to Home Screen")),
		}, -2)

		self["key_red"] = Button(_(" "))
		self["key_green"] = Button(_("Slide Show"))
		self["key_yellow"] = Button(_("File View"))
		self["key_blue"] = Button(_("Settings"))
		self["frame"] = MovingPixmap()

		self.thumbsC = 8
		self.thumbsX = 4

		for x in range(self.thumbsC):
			self["label" + str(x)] = Button("")
			self["thumb" + str(x)] = Pixmap()

		self.positionlist = []
		#Need to make this read from skin?
		self.positionlist.append((170, 160))
		self.positionlist.append((420, 160))
		self.positionlist.append((670, 160))
		self.positionlist.append((920, 160))
		self.positionlist.append((170, 375))
		self.positionlist.append((420, 375))
		self.positionlist.append((670, 375))
		self.positionlist.append((920, 375))

		self.Thumbnaillist = []
		self.filelist = []
		self.currPage = -1
		self.dirlistcount = 0
		self.path = path

		index = 0
		framePos = 0
		Page = 0
		for x in piclist:
			if x[0][1] == False:
				self.filelist.append((index, framePos, Page, x[0][0], path + x[0][0]))
				index += 1
				framePos += 1
				if framePos > (self.thumbsC - 1):
					framePos = 0
					Page += 1
			else:
				self.dirlistcount += 1

		self.maxentry = len(self.filelist) - 1
		self.index = lastindex - self.dirlistcount
		if self.index < 0:
			self.index = 0

		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.showPic)

		self.onLayoutFinish.append(self.setPicloadConf)

		self.ThumbTimer = eTimer()
		self.ThumbTimer.callback.append(self.showPic)

	def setPicloadConf(self):
		sc = getScale()
		self.picload.setPara([self["thumb0"].instance.size().width(), self["thumb0"].instance.size().height(), sc[0], sc[1], config.plugins.mc_pp.cache.value, int(config.plugins.mc_pp.resize.value), config.plugins.mc_pp.bgcolor.value])
		self.paintFrame()

	def paintFrame(self):
		#print "index=" + str(self.index)
		if self.maxentry < self.index or self.index < 0:
			return

		pos = self.positionlist[self.filelist[self.index][T_FRAME_POS]]
		self["frame"].moveTo(pos[0], pos[1], 1)
		self["frame"].startMoving()

		if self.currPage != self.filelist[self.index][T_PAGE]:
			self.currPage = self.filelist[self.index][T_PAGE]
			self.newPage()

	def newPage(self):
		self.Thumbnaillist = []
		#clear Labels and Thumbnail
		for x in range(self.thumbsC):
			self["label" + str(x)].setText("")
			self["thumb" + str(x)].hide()
		#paint Labels and fill Thumbnail-List
		for x in self.filelist:
			if x[T_PAGE] == self.currPage:
				self["label" + str(x[T_FRAME_POS])].setText(x[T_NAME])
				self.Thumbnaillist.append([0, x[T_FRAME_POS], x[T_FULL]])

		#paint Thumbnail start
		self.showPic()

	def showPic(self, picInfo=""):
		for x in range(len(self.Thumbnaillist)):
			if self.Thumbnaillist[x][0] == 0:
				if self.picload.getThumbnail(self.Thumbnaillist[x][2]) == 1: #zu tun probier noch mal
					self.ThumbTimer.start(500, True)
				else:
					self.Thumbnaillist[x][0] = 1
				break
			elif self.Thumbnaillist[x][0] == 1:
				self.Thumbnaillist[x][0] = 2
				ptr = self.picload.getData()
				if ptr != None:
					self["thumb" + str(self.Thumbnaillist[x][1])].instance.setPixmap(ptr.__deref__())
					self["thumb" + str(self.Thumbnaillist[x][1])].show()

	def key_left(self):
		self.index -= 1
		if self.index < 0:
			self.index = self.maxentry
		self.paintFrame()

	def key_right(self):
		self.index += 1
		if self.index > self.maxentry:
			self.index = 0
		self.paintFrame()

	def key_up(self):
		self.index -= self.thumbsX
		if self.index < 0:
			self.index = self.maxentry
		self.paintFrame()

	def key_down(self):
		self.index += self.thumbsX
		if self.index > self.maxentry:
			self.index = 0
		self.paintFrame()

	def StartExif(self):
		if self.maxentry < 0:
			return
		self.session.open(Pic_Exif, self.picload.getInfo(self.filelist[self.index][T_FULL]))

	def KeyOk(self):
		if self.maxentry < 0:
			return

		self.old_index = self.index
		self.session.openWithCallback(self.callbackView, MC_PicView, self.filelist, self.index, self.path, False)

	def startslideshow(self):
		if self.maxentry < 0:
			return

		self.session.openWithCallback(self.callbackView, MC_PicView, self.filelist, self.index, self.path, True)

	def Settings(self):
		self.session.open(MC_PicSetup)

	def callbackView(self, val=0):
		self.index = val
		if self.old_index != self.index:
			self.paintFrame()

	def Exit(self):
		del self.picload
		self.close(self.index + self.dirlistcount)

	def Home(self):
		del self.picload
		self.close(self.index + self.dirlistcount, True)
#------------------------------------------------------------------------------------------


class MC_PicView(Screen):
	def __init__(self, session, filelist, index, path, startslide):

		space = config.plugins.mc_pp.framesize.value
		size_w = getDesktop(0).size().width()
		size_h = getDesktop(0).size().height()

		self.skin = "<screen position=\"0,0\" size=\"" + str(size_w) + "," + str(size_h) + "\" flags=\"wfNoBorder\" > \
			<eLabel position=\"0,0\" zPosition=\"0\" size=\"" + str(size_w) + "," + str(size_h) + "\" backgroundColor=\"black\" /><widget name=\"pic\" position=\"" + str(space) + "," + str(space) + "\" size=\"" + str(size_w - (space * 2)) + "," + str(size_h - (space * 2)) + "\" zPosition=\"1\" alphatest=\"on\" /> \
			<widget name=\"point\" position=\"" + str(space + 5) + "," + str(space + 2) + "\" size=\"20,20\" zPosition=\"2\" pixmap=\"skin_default/icons/record.png\" alphatest=\"on\" /> \
			<widget name=\"play_icon\" position=\"" + str(space + 25) + "," + str(space + 2) + "\" size=\"20,20\" zPosition=\"2\" pixmap=\"skin_default/icons/ico_mp_play.png\"  alphatest=\"on\" /> \
			</screen> \
			"

		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MovieSelectionActions"],
		{
			"cancel": self.Exit,
			"green": self.PlayPause,
			"yellow": self.PlayPause,
			"blue": self.nextPic,
			"red": self.prevPic,
			"left": self.prevPic,
			"right": self.nextPic,
			"showEventInfo": self.StartExif,
		}, -1)

		self["point"] = Pixmap()
		self["pic"] = Pixmap()
		self["play_icon"] = Pixmap()

		self.old_index = 0
		self.filelist = []
		self.lastindex = index
		self.currPic = []
		self.shownow = True
		self.dirlistcount = 0

		for x in filelist:
			if len(filelist[0]) == 3: #orig. filelist
				if x[0][1] == False:
					self.filelist.append(path + x[0][0])
				else:
					self.dirlistcount += 1
			else: # thumbnaillist
				self.filelist.append(x[T_FULL])

		self.maxentry = len(self.filelist) - 1
		self.index = index - self.dirlistcount
		if self.index < 0:
			self.index = 0

		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.finish_decode)

		self.slideTimer = eTimer()
		self.slideTimer.callback.append(self.slidePic)

		if self.maxentry >= 0:
			self.onLayoutFinish.append(self.setPicloadConf)

		if startslide == True:
			self.PlayPause()

	def setPicloadConf(self):
		sc = getScale()
		self.picload.setPara([self["pic"].instance.size().width(), self["pic"].instance.size().height(), sc[0], sc[1], 0, int(config.plugins.mc_pp.resize.value), config.plugins.mc_pp.bgcolor.value])

		self["play_icon"].hide()
		self.start_decode()

	def ShowPicture(self):
		if self.shownow and len(self.currPic):
			self.shownow = False
			self.lastindex = self.currPic[1]
			self["pic"].instance.setPixmap(self.currPic[2].__deref__())
			self.currPic = []

			self.next()
			self.start_decode()

	def finish_decode(self, picInfo=""):
		self["point"].hide()
		ptr = self.picload.getData()
		if ptr != None:
			text = ""
			try:
				text = picInfo.split('\n', 1)
				text = "(" + str(self.index + 1) + "/" + str(self.maxentry + 1) + ") " + text[0].split('/')[-1]
			except:
				pass
			self.currPic = []
			self.currPic.append(text)
			self.currPic.append(self.index)
			self.currPic.append(ptr)
			self.ShowPicture()

	def start_decode(self):
		self.picload.startDecode(self.filelist[self.index])
		self["point"].show()

	def next(self):
		self.index += 1
		if self.index > self.maxentry:
			self.index = 0

	def prev(self):
		self.index -= 1
		if self.index < 0:
			self.index = self.maxentry

	def slidePic(self):
		print("slide to next Picture index=" + str(self.lastindex))
		if config.plugins.mc_pp.loop.value == False and self.lastindex == self.maxentry:
			self.PlayPause()
		self.shownow = True
		self.ShowPicture()

	def PlayPause(self):
		if self.slideTimer.isActive():
			self.slideTimer.stop()
			self["play_icon"].hide()
		else:
			self.slideTimer.start(config.plugins.mc_pp.slidetime.value * 1000)
			self["play_icon"].show()
			self.nextPic()

	def prevPic(self):
		self.currPic = []
		self.index = self.lastindex
		self.prev()
		self.start_decode()
		self.shownow = True

	def nextPic(self):
		self.shownow = True
		self.ShowPicture()

	def StartExif(self):
		if self.maxentry < 0:
			return
		self.session.open(Pic_Exif, self.picload.getInfo(self.filelist[self.lastindex]))

	def Exit(self):
		del self.picload
		self.close(self.lastindex + self.dirlistcount)


#------------------------------------------------------------------------------------------

class Pic_Exif(Screen):
	skin = """
		<screen name="Pic_Exif" position="center,center" size="560,360" title="Info" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="menu" render="Listbox" position="5,50" size="550,310" scrollbarMode="showOnDemand" selectionDisabled="1" >
				<convert type="TemplatedMultiContent">
				{
					"template": [  MultiContentEntryText(pos = (5, 5), size = (250, 30), flags = RT_HALIGN_LEFT, text = 0), MultiContentEntryText(pos = (260, 5), size = (290, 30), flags = RT_HALIGN_LEFT, text = 1)],
					"fonts": [gFont("Regular", 20)],
					"itemHeight": 30
				}
				</convert>
			</widget>
		</screen>"""

	def __init__(self, session, exiflist):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"cancel": self.close
		}, -1)

		self["key_red"] = StaticText(_("Close"))

		exifdesc = [_("filename") + ':', "EXIF-Version:", "Make:", "Camera:", "Date/Time:", "Width / Height:", "Flash used:", "Orientation:", "User Comments:", "Metering Mode:", "Exposure Program:", "Light Source:", "CompressedBitsPerPixel:", "ISO Speed Rating:", "X-Resolution:", "Y-Resolution:", "Resolution Unit:", "Brightness:", "Exposure Time:", "Exposure Bias:", "Distance:", "CCD-Width:", "ApertureFNumber:"]
		list = []

		for x in range(len(exiflist)):
			if x > 0:
				list.append((exifdesc[x], exiflist[x]))
			else:
				name = exiflist[x].split('/')[-1]
				list.append((exifdesc[x], name))
		self["menu"] = List(list)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("Info"))

#------------------------------------------------------------------------------------------


class MC_PicSetup(Screen):
	def __init__(self, session):
		self.skin = """<screen position="120,180" size="480,310" title="Settings" >
					<widget name="liste" position="5,5" size="470,300" scrollbarMode="showOnDemand" />
				</screen>"""
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
		}, -1)

		self.list = []
		self["liste"] = ConfigList(self.list)
		self.list.append(getConfigListEntry(_("Slideshow Interval (sec.)"), config.plugins.mc_pp.slidetime))
		self.list.append(getConfigListEntry(_("Scaling Mode"), config.plugins.mc_pp.resize))
		self.list.append(getConfigListEntry(_("Cache Thumbnails"), config.plugins.mc_pp.cache))
		self.list.append(getConfigListEntry(_("Play slide show in loop"), config.plugins.mc_pp.loop))

	def keyLeft(self):
		self["liste"].handleKey(KEY_LEFT)

	def keyRight(self):
		self["liste"].handleKey(KEY_RIGHT)

	def keyNumber(self, number):
		self["liste"].handleKey(KEY_0 + number)

#--------------------------------------------------------------------------------------------------


class MC_FolderOptions(Screen):
	skin = """
		<screen position="160,200" size="400,200" title="Media Center - Folder Options" >
			<widget source="pathlabel" transparent="1" render="Label" zPosition="2" position="0,180" size="380,20" font="Regular;16" />
			<widget source="menu" render="Listbox" zPosition="5" transparent="1" position="10,10" size="380,160" scrollbarMode="showOnDemand" >
				<convert type="StringList" />
			</widget>
		</screen>"""

	def __init__(self, session, directory, dirname):
		self.skin = MC_FolderOptions.skin
		Screen.__init__(self, session)

		self.dirname = dirname
		self.directory = directory

		self.list = []
		#list.append(("Titel", "nothing", "entryID", "weight"))
		self.list.append((_("Delete File / Folder"), "delete", "menu_delete", "50"))

		self["menu"] = List(self.list)
		self["pathlabel"] = StaticText(_("Folder:") + " " + self.directory)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"cancel": self.Exit,
			"ok": self.okbuttonClick
		}, -1)

	def okbuttonClick(self):
		print("okbuttonClick")
		selection = self["menu"].getCurrent()
		if selection is not None:
			if selection[1] == "delete":
				self.removedir()
			else:
				self.close()
		else:
			self.close()

	def removedir(self):
		self.session.openWithCallback(self.deleteConfirm, MessageBox, _("Are you sure to delete this file / folder?"))

	def deleteConfirm(self, result):
		if result:
			try:
				os.rmdir(self.directory)
			except os.error:
				self.session.open(MessageBox, _("Error: Cannot remove file / folder\n"), MessageBox.TYPE_INFO)
			self.close()

	def Exit(self):
		self.close()
