from enigma import iPlayableService, eTimer, eWidget, eRect, eServiceReference, iServiceInformation, ePicLoad
from Screens.Screen import Screen
from Screens.ServiceInfo import ServiceInfoList, ServiceInfoListEntry
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.Button import Button
from Components.config import *
from Tools.Directories import resolveFilename, fileExists, pathExists, SCOPE_MEDIA
from Tools.LoadPixmap import LoadPixmap
import os

from MC_Filelist import FileList

config.plugins.mc_vp = ConfigSubsection()
config.plugins.mc_vp.lastDir = ConfigText(default='mountpoint')


class MC_VideoPlayer(Screen, HelpableScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)

		self["key_red"] = Button(_("Exit"))
		self["key_green"] = Button(_("Info"))
		self["key_yellow"] = Button(_("IMDb"))
		self["key_blue"] = Button(_("Menu"))
		self["currentfolder"] = Label("")

		#Check if AzBox because of using MRUA
		if os.path.exists("/proc/player"):
			self.azbox = True
		else:
			self.azbox = False

		#Check if we have a saved last dir
		currDir = config.plugins.mc_vp.lastDir.value
		if not pathExists(currDir):
			currDir = None

		self["currentfolder"].setText(str(currDir))

		self.filelist = FileList(currDir, showMountpoints=True, useServiceRef=True, showDirectories=True, showFiles=True, matchingPattern="(?i)^.*\.(vob|mpg|mpeg|avi|mkv|dat|iso|img|mp4|divx|m2ts|wmv|flv|mov)")
		self["filelist"] = self.filelist
		self["filelist"].onSelectionChanged.append(self.selectionChanged)

		self["actions"] = HelpableActionMap(self, "MC_VideoPlayerActions",
			{
				"ok": (self.KeyOk, _("Play selected file")),
				"cancel": (self.Exit, _("Exit Video Player")),
				"left": (self.leftUp, _("List Top")),
				"right": (self.rightDown, _("List Bottom")),
				"up": (self.up, _("List up")),
				"down": (self.down, _("List down")),
				"menu": (self.showMenu, _("File / Folder Options")),
				"info": (self.showFileInfo, _("Show File Info")),
				#"red": (self.Exit, _("Exit Videos")),
				"yellow": (self.startIMDb, ("Start IMDb")),
				"home": (self.Exit, _("Exit Videos")),
			}, -2)

	def selectionChanged(self):
		pass

	def up(self):
		self["filelist"].up()

	def down(self):
		self["filelist"].down()

	def leftUp(self):
		self["filelist"].pageUp()

	def rightDown(self):
		self["filelist"].pageDown()

	def showFileInfo(self):
		if self["filelist"].canDescent():
			return
		else:
			self.session.open(MC_VideoInfoView, self["filelist"].getCurrentDirectory() + self["filelist"].getFilename(), self["filelist"].getFilename(), self["filelist"].getServiceRef())

	def KeyExit(self):
		self.filelist.gotoParent()

	def KeyOk(self):
		self.isDVD = False
		self.isIso = False
		self.isFile = False
		self.pathname = ""

		filename = self["filelist"].getFilename()
		if filename is not None:
			if filename.lower().endswith("iso") or filename.lower().endswith("img"):
				os.system("mkdir /tmp/discmount")
				os.system("umount -f /tmp/discmount")
				os.system("losetup -d /dev/loop0")
				os.system("losetup /dev/loop0 \"" + str(filename) + "\"")
				os.system("mount -t udf /dev/loop0 /tmp/discmount")
				self.pathname = "/tmp/discmount/"
				self.isIso = True

			elif self.filelist.canDescent():
				self.filelist.descent()
				self["filelist"].refresh()
				self.pathname = self["filelist"].getCurrentDirectory() or ""

			else:
				self.isFile = True

		elif self.filelist.canDescent():
				self.filelist.descent()
				self["filelist"].refresh()

		if self.pathname != "":
			dvdFilelist = []
			dvdDevice = None
			if fileExists(self.pathname + "VIDEO_TS.IFO"):
				dvdFilelist.append(str(self.pathname[0:-1]))
				self.isDVD = True
			elif fileExists(self.pathname + "VIDEO_TS/VIDEO_TS.IFO"):
				dvdFilelist.append(str(self.pathname + "VIDEO_TS"))
				self.isDVD = True
			elif self.isIso:
				self["filelist"].setIsoDir(filename, self["filelist"].getCurrentDirectory())
				self.JumpToFolder("/tmp/discmount/")
				self["filelist"].up()

		if self.isDVD:
			self.filelist.gotoParent()
			if self.azbox == True:
				from AZ_DVDPlayer import AZDVDPlayer
				self.session.open(AZDVDPlayer, dvd_device=dvdDevice, dvd_filelist=dvdFilelist)
			else:
				print("Play dvd normal")
				from Screens import DVD
				self.session.open(DVD.DVDPlayer, dvd_filelist=dvdFilelist)

		elif self.isFile:
			if self.azbox == True:
				from AZ_MRUAPlayer import MRUAPlayer
				self.session.open(MRUAPlayer, ref=self["filelist"].getFilename())
			else:
				from MC_MoviePlayer import MC_MoviePlayer
				self.session.open(MC_MoviePlayer, self["filelist"].getServiceRef())

	def JumpToFolder(self, jumpto=None):
		if jumpto is None:
			return
		else:
			self["filelist"].changeDir(jumpto)
			self["currentfolder"].setText(("%s") % (jumpto))

	def KeySettings(self):
		self.session.open(VideoPlayerSettings)

	def Exit(self):
		try:
			config.plugins.mc_vp.lastDir.value = self.filelist.getCurrentDirectory()
		except:
			config.plugins.mc_vp.lastDir.value = 'mountpoint'
		config.plugins.mc_vp.save()
		configfile.save()
		self.close()

	def showMenu(self):
		menu = []
		menu.append((_("Check IMDB"), "imdblookup"))
		if self.filelist.canDescent():
			x = self.filelist.getName()
			if x == "..":
				return
			menu.append((_("delete directory"), "deletedir"))
		else:
			menu.append((_("delete file"), "deletefile"))
		self.session.openWithCallback(self.menuCallback, ChoiceBox, title="", list=menu)

	def menuCallback(self, choice):
		if choice is None:
			return
		if choice[1] == "deletedir":
			self.deleteDir()
		elif choice[1] == "deletefile":
			self.deleteFile()
		elif choice[1] == "imdblookup":
			try:
				from MC_Imdb import IMDB
				name = self["filelist"].getName()
				self.session.open(IMDB, name.partition('(')[0])
			except ImportError:
				self.session.open(MessageBox, _("Cannot load IMDB, please check if python-html is installed"), MessageBox.TYPE_INFO, timeout=5)

	def deleteDir(self):
		self.session.openWithCallback(self.deleteDirConfirmed, MessageBox, _("Do you really want to delete this directory and it's content ?"))

	def deleteDirConfirmed(self, confirmed):
		if confirmed:
			import shutil
			deldir = self.filelist.getSelection()[0]
			shutil.rmtree(deldir)
			self["filelist"].refresh()

	def deleteFile(self):
		self.session.openWithCallback(self.deleteFileConfirmed, MessageBox, _("Do you really want to delete this file ?"))

	def deleteFileConfirmed(self, confirmed):
		if confirmed:
			delfile = self["filelist"].getFilename()
			os.remove(delfile)
			self["filelist"].refresh()

	def startIMDb(self):
		from MC_Imdb import IMDB
		name = self["filelist"].getName()
		self.session.open(IMDB, name.partition('(')[0])


class MC_VideoInfoView(Screen):
	skin = """
		<screen position="80,130" size="560,320" title="View Video Info" >
			<widget name="infolist" position="5,5" size="550,310" selectionDisabled="1" />
		</screen>"""

	def __init__(self, session, fullname, name, ref):
		self.skin = MC_VideoInfoView.skin
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"cancel": self.close,
			"ok": self.close
		}, -1)

		tlist = []
		self["infolist"] = ServiceInfoList(tlist)

		currPlay = self.session.nav.getCurrentService()
		if currPlay is not None:
			stitle = currPlay.info().getInfoString(iServiceInformation.sTitle)

			if stitle == "":
				stitle = currPlay.info().getName().split('/')[-1]

			tlist.append(ServiceInfoListEntry(_("Title:") + " ", stitle))
			tlist.append(ServiceInfoListEntry(_("Namespace:") + " ", currPlay.info().getInfoString(iServiceInformation.sNamespace)))
			tlist.append(ServiceInfoListEntry(_("Provider:") + " ", currPlay.info().getInfoString(iServiceInformation.sProvider)))
			tlist.append(ServiceInfoListEntry(_("TimeCreate:") + " ", currPlay.info().getInfoString(iServiceInformation.sTimeCreate)))
			tlist.append(ServiceInfoListEntry(_("VideoWidth:") + " ", currPlay.info().getInfoString(iServiceInformation.sVideoWidth)))
			tlist.append(ServiceInfoListEntry(_("VideoHeight:") + " ", currPlay.info().getInfoString(iServiceInformation.sVideoHeight)))
			tlist.append(ServiceInfoListEntry(_("Description:") + " ", currPlay.info().getInfoString(iServiceInformation.sDescription)))
