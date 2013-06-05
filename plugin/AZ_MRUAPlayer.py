from Screens.Screen import Screen
from Screens.ServiceScan import ServiceScan
from Screens.MessageBox import MessageBox
from Components.Label import Label
from Components.TuneTest import Tuner
from Components.ConfigList import ConfigListScreen
from Components.ProgressBar import ProgressBar
from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Components.ActionMap import NumberActionMap, ActionMap
from Components.NimManager import nimmanager, getConfigSatlist
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigYesNo, ConfigInteger, getConfigListEntry, ConfigSlider, ConfigEnableDisable
from Tools.HardwareInfo import HardwareInfo
from Tools.Directories import resolveFilename
from enigma import eTimer, eDVBFrontendParametersSatellite, eDVBFrontendParameters, eComponentScan, eDVBSatelliteEquipmentControl, eDVBFrontendParametersTerrestrial, eDVBFrontendParametersCable, eConsoleAppContainer, eDVBResourceManager, getDesktop
import time
from Components.FileList import FileList
import re
import os
import sys
from os import system, listdir, statvfs, popen, makedirs, stat, major, minor, path, access
from Components.AVSwitch import AVSwitch
from Components.SystemInfo import SystemInfo
from Components.Console import Console
import datetime
import os.path
from Tools.LoadPixmap import LoadPixmap
from Components.Sources.List import List
from enigma import *
from Components.config import configfile, getConfigListEntry, ConfigEnableDisable, ConfigYesNo, ConfigText, ConfigDateTime, ConfigClock, ConfigNumber, ConfigSelectionNumber, ConfigSelection, config, ConfigSubsection, ConfigSubList, ConfigSubDict, ConfigIP, ConfigSlider, ConfigDirectory, ConfigInteger
from os.path import isdir as os_path_isdir
from Components.MenuList import MenuList
from Components.VolumeControl import VolumeControl

config.plugins.mc_mrua = ConfigSubsection()
config.plugins.mc_mrua.lastDir = ConfigText(default='/')
config.plugins.mc_mrua.lastFile = ConfigText(default='None')
config.plugins.mc_mrua.lastPosition = ConfigText(default='0')
config.plugins.mc_mrua.ExtSub_Enable = ConfigSelection(choices={'0': _('ON'),
 '1': _('OFF')}, default='0')
config.plugins.mc_mrua.ExtSub_Size = ConfigSelection(default=50, choices=['30',
 '35',
 '40',
 '45',
 '50',
 '55',
 '60',
 '65',
 '70',
 '75',
 '80',
 '85',
 '90'])
config.plugins.mc_mrua.ExtSub_Position = ConfigSelection(default='0', choices=['0',
 '10',
 '20',
 '30',
 '40',
 '50',
 '60',
 '70',
 '80',
 '90'])
config.plugins.mc_mrua.ExtSub_Color = ConfigSelection(choices={'1': _('White'),
 '2': _('Yellow'),
 '3': _('Blue'),
 '4': _('Red'),
 '5': _('Green'),
 '6': _('Orange'),
 '7': _('Blue2'),
 '8': _('Blue3'),
 '9': _('Pink'),
 '0': _('Black')}, default='1')
config.plugins.mc_mrua.ExtSub_OutColor = ConfigSelection(choices={'1': _('White'),
 '2': _('Yellow'),
 '3': _('Blue'),
 '4': _('Red'),
 '5': _('Green'),
 '6': _('Orange'),
 '7': _('Blue2'),
 '8': _('Blue3'),
 '9': _('Pink'),
 '0': _('Black')}, default='0')
config.plugins.mc_mrua.ExtSub_Encoding = ConfigSelection(choices={'none': _('None'),
 'windows-1256': _('Arabic'),
 'windows-1257': _('Baltic'),
 'csbig5': _('Chinese'),
 'windows-1251': _('Cyrlic'),
 'windows-1250': _('EastEurope'),
 'windows-1253': _('Greek'),
 'windows-1255': _('Hebrew'),
 'windows-1254': _('Turkish'),
 'windows-1258': _('Vietnamese'),
 'windows-1252': _('WestEurope'),
 'iso-8859-1': _('Spanish (es)')}, default='none')

config.plugins.mc_mrua.Scaling = ConfigSelection(default='Just Scale', choices=['Just Scale', 'Pan&Scan', 'Pillarbox'])

config.plugins.mc_mrua.UPnP_Enable = ConfigSelection(choices={'0': _('OFF'),
 '1': _('ON')}, default='0')
path = '/usr/share/fonts/'
cache = {}
try:
    cached_mtime, list = cache[path]
    del cache[path]
except KeyError:
    cached_mtime, list = (-1, [])

mtime = os.stat(path).st_mtime
if mtime != cached_mtime:
    list = os.listdir(path)
    list.sort()
cache[path] = (mtime, list)
n = 0
for fontchk in list:
    if fontchk[len(fontchk) - 3:] != 'ttf':
        del list[n]
    n += 1

scriptliste = list

config.plugins.mc_mrua.ExtSub_FontSel = ConfigSelection(choices=scriptliste, default='nmsbd.ttf')

class MRUAPlayer(Screen):
	skin = '\n\t\t<screen position="0,0" size="0,0" title="Infobar" flags="wfNoBorder" >\n\t\t</screen>'
	
	def __init__(self, session, ref, path="/", ftype="video"):
		Screen.__init__(self, session)
		self.session = session
		self.MediaFileName = ref
		self.MediaFilePath = path
		self.MediaFType = ftype
		self['actions'] = NumberActionMap([ 'MRUAPlayerActions',
		 'MediaPlayerActions',
		 'MediaPlayerSeekActions',
		 'InputActions',
		 'OkCancelActions',
		 'ColorActions',
		 'DirectionActions',
		 'StandbyActions',
		 'MenuActions',
		 'MoviePlayerActions'], {'ok': self.ok,
		 'cancel': self.exit1,
		 'up': self.ZapUp,
		 'down': self.ZapDown,
		 'left': self.ZapLeft,
		 'right': self.ZapRight,
		 'nextBouquet': self.ZapUp,
		 'prevBouquet': self.ZapDown,
		 'power': self.exit2,
		 'play': self.keyPlay,
		 'pause': self.keyPlay,
		 'stop': self.exit1,
		 'previous': self.keyPrev,
		 'next': self.keyNext,
		 'seekFwd': self.keyFF,
		 'seekBack': self.keyREW,
		 'menu': self.Konfig,
		 'subtitles': self.SubSel,
		 'delete': self.SubSel,
		 'AudioSelection': self.ALngSel}, -1)
		
		#TOMMY: ff printen hier
		print "\n\n"
		print "Filename:"
		print ref
		print "\n\n"
		
		self.playpause = 102
		self.VCodec = ''
		self.Resol = ''
		self.Format = ''
		self.ACodec = ''
		self.SRate = '48000'
		self.ChNo = ''
		self.FFval = 0
		self.REWval = 0
		self.info1 = 'Play |>'
		self.ALanguages = []
		self.SubtitlesL = []
		self.onLayoutFinish.append(self.keyGo)
		
		#Detect box type and set command
		self.cmdV0 = ''
		self.cmdV1 = ''
		self.cmdV2 = ''
		self.cmdV3 = ''
		hw_type = HardwareInfo().get_device_name()
		if hw_type == 'minime' or hw_type == 'me':
			self.cmdA = 'rmfp_player -dram 0 -ve 0 -vd 0 -ae 0 -no_disp -prebuf 256 -resetvcxo '
			self.cmdV = 'rmfp_player -dram 0 -ve 0 -vd 0 -ae 0 -no_disp -resetvcxo -subs_res 1080 -forced_font /usr/share/fonts/' + config.plugins.mc_mrua.ExtSub_FontSel.value + ' '
			self.cmdV0 = 'rmfp_player -dram 0 -ve 0 -vd 0 -ae 0 -no_disp -resetvcxo -no_close -oscaler spu -subs_res 1080 -yuv_palette_subs '
		if hw_type == 'elite' or hw_type == 'premium' or hw_type == 'premium+' or hw_type == 'ultra':
			self.cmdA = 'rmfp_player -dram 1 -ve 1 -vd 0 -ae 0 -no_disp -prebuf 256 -resetvcxo '
			self.cmdV = 'rmfp_player -dram 1 -ve 1 -vd 0 -ae 0 -no_disp -resetvcxo -subs_res 1080 -forced_font /usr/share/fonts/' + config.plugins.mc_mrua.ExtSub_FontSel.value + ' '
			self.cmdV0 = 'rmfp_player -dram 1 -ve 1 -vd 0 -ae 0 -no_disp -resetvcxo -no_close -oscaler spu -subs_res 1080 -yuv_palette_subs '
		
		#Actually launching rmfp_player. Video Only
		self.cmd = self.cmdV0 + self.cmdV1 + self.cmdV2 + self.cmdV3 + "'" + self.MediaFileName + "' &"
		os.popen('killall rmfp_player')
		time.sleep(0.1)
		os.popen(self.cmd)
		time.sleep(2)
		if os.path.exists('/tmp/rmfp.cmd2'):
			os.remove('/tmp/rmfp.cmd2')
		for n in range(0, 8):
			try:
				f = open('/tmp/rmfp.cmd2', 'wb')
				try:
					f.write('102\n')
				finally:
					f.close()
			except Exception as e:
				print e
			if os.path.exists('/tmp/rmfp.cmd2'):
				break
			time.sleep(0.05)

	def keyGo(self):
		self.PlayerState = eTimer()
		self.PlayerState.callback.append(self.PlayerStateCheck)
		self.PlayerState.start(100, True)
		self.PlayerGetInfo = eTimer()
		self.PlayerGetInfo.callback.append(self.GetInfo)
		self.PlayerGetInfo.start(3500, True)

    #Check if player is still running
	def PlayerStateCheck(self):
		f = os.popen('ps|grep -v ps| grep -v grep| grep rmfp_player')
		Playtmp = f.readlines()
		f.close()
		self.AZP = len(Playtmp)
		if self.AZP == 0:
			if os.path.exists('/tmp/rmfp.cmd2'):
				os.remove('/tmp/rmfp.cmd2')
			for n in range(0, 8):
				try:
					f = open('/tmp/rmfp.cmd2', 'wb')
					try:
						f.write('100\n')
					finally:
						f.close()
				except Exception as e:
					print e
				if os.path.exists('/tmp/rmfp.cmd2'):
					break
				time.sleep(0.05)
			self.close('*Stop*')
		self.PlayerState.start(300, True)

    #Get infro about video from player once video is started
	def GetInfo(self):
		self.ALanguages = []
		self.SubtitlesL = []
		if os.path.exists('/tmp/rmfp.out2'):
			os.remove('/tmp/rmfp.out2')
		if os.path.exists('/tmp/rmfp.cmd2'):
			os.remove('/tmp/rmfp.cmd2')
		for n in range(0, 8):
			try:
				f = open('/tmp/rmfp.cmd2', 'wb')
				try:
					f.write('130\n')
				finally:
					f.close()
			except Exception as e:
				print e
			if os.path.exists('/tmp/rmfp.cmd2'):
				break
			time.sleep(0.05)

		time.sleep(0.05)
		for n in range(0, 9):
			try:
				tmpfile = open('/tmp/rmfp.out2', 'r')
				lines = tmpfile.readlines()
				tmpfile.close()
				lno = 0
			except:
				print "rmfp.out2 or no lines available yet, trying again later"
				self.PlayerGetInfo = eTimer()
				self.PlayerGetInfo.callback.append(self.GetInfo)
				self.PlayerGetInfo.start(3500, True)
				return
			try:
				for line in lines:
					ipos = line.find('Video stream ID')
					if ipos >= 0:
						ipos1 = lines[lno + 1].find('(')
						ipos2 = lines[lno + 1].find(')')
						VCodec = lines[lno + 1][ipos1 + 1:ipos2]
						self.VCodec = VCodec.replace(' ', '')
						ipos1 = lines[lno + 2].find('Resolution')
						Resol = lines[lno + 2][ipos1 + 10:-1]
						self.Resol = Resol.replace(' ', '')
						ipos1 = lines[lno + 3].find('Format')
						Format = lines[lno + 3][ipos1 + 6:-1]
						self.Format = Format.replace(' ', '')
					ipos = line.find('Audio stream ID')
					if ipos >= 0:
						ipos1 = lines[lno + 1].find('(')
						ipos2 = lines[lno + 1].find(')')
						ACodec = lines[lno + 1][ipos1 + 1:ipos2]
						self.ACodec = ACodec.replace(' ', '')
						ipos1 = lines[lno + 2].find('SampleRate')
						SRate = lines[lno + 2][ipos1 + 10:-1]
						self.SRate = SRate.replace(' ', '')
						ipos1 = lines[lno + 3].find('ChannelNumber')
						ChNo = lines[lno + 3][ipos1 + 13:-1]
						self.ChNo = ChNo.replace(' ', '')
						if self.ChNo == '5':
							self.ChNo = '5.1'
					ipos = line.find('Video Streams count:')
					if ipos >= 0:
						ino = int(lines[lno][ipos + 20:-1])
						print 'broj na Video strimovi:', ino
						for n in range(0, ino):
							print lines[lno + n + 1][:-1]
					ipos = line.find('Audio Streams count:')
					if ipos >= 0:
						ino = int(lines[lno][ipos + 20:-1])
						print 'No Of Audio streams:', ino
						for n in range(0, ino):
							print lines[lno + n + 1][:-1]
							tmpstr = lines[lno + n + 1][:-1]
							ipos = tmpstr.find('ID')
							if ipos >= 0:
								tmpstr = ' - ' + tmpstr[ipos:]
							self.ALanguages.append(tmpstr)
					ipos = line.find('Subtitles Streams count:')
					if ipos >= 0:
						ino = int(lines[lno][ipos + 24:-1])
						print 'No Of Subtitles streams:', ino
						for n in range(0, ino):
							print lines[lno + n + 1][:-1]
							tmpstr = lines[lno + n + 1][:-1]
							ipos = tmpstr.find('ID')
							if ipos >= 0:
								tmpstr = ' - ' + tmpstr[ipos:]
							self.SubtitlesL.append(tmpstr)
					ipos = line.find('Duration:')
					if ipos >= 0:
						ino = int(lines[lno][ipos + 9:-3])
						self.Duration = ino
					lno += 1
				break
			except Exception:
				print 'Error GetInfo'
			time.sleep(0.1)

		if self.MediaFType != 'video':
			return
		if os.path.exists('/tmp/rmfp.out2'):
			os.remove('/tmp/rmfp.out2')
		if os.path.exists('/tmp/rmfp.cmd2'):
			os.remove('/tmp/rmfp.cmd2')
		time.sleep(0.05)
		if config.plugins.mc_mrua.ExtSub_Enable.value == '0':
			self.SendCMD2(config.plugins.mc_mrua.ExtSub_Size.value, 212)
			time.sleep(0.05)
			self.SendCMD2(config.plugins.mc_mrua.ExtSub_Position.value, 214)
			time.sleep(0.05)
			self.SendCMD2(config.plugins.mc_mrua.ExtSub_Color.value, 216)
			time.sleep(0.05)
		cmd = 0
		if config.plugins.mc_mrua.Scaling.value == 'Just Scale':
			cmd = 223
		if config.plugins.mc_mrua.Scaling.value == 'Pan&Scan':
			cmd = 224
		if config.plugins.mc_mrua.Scaling.value == 'Pillarbox':
			cmd = 225
		if cmd > 0:
			self.SendCMD2(-1, cmd)
		#TOMMY: Ah hier word resume geregeld
		if config.plugins.mc_mrua.lastFile.value == self.MediaFileName:
			self.session.openWithCallback(self.ResumeConfirmed, MessageBox, _('Last position = ' + str(datetime.timedelta(seconds=long(config.plugins.mc_mrua.lastPosition.value))) + '\n\nResume ?'), timeout=5)

	def ResumeConfirmed(self, yesno):
		if yesno:
			self.GetSec1()
			sec3 = long(config.plugins.mc_mrua.lastPosition.value)
			if sec3 > 0 and sec3 < self.sec2:
				time.sleep(0.11)
				self.SendCMD2(sec3, 106)
				time.sleep(0.75)
				self.ok1(2)
#TOMMY: Needed???
#	def updateMsg(self):
#		self.close()

#	def exit(self):
#		self.close('---')

	def exit1(self):
		self.GetSec1()
		#TOMMY: Hier moet wellicht de resume opgeslagen worden
		#config.plugins.mc_mrua.lastPosition.value = str(self.sec1)
		#config.plugins.mc_mrua.lastFile.value = str(self.MediaFileName)
		if os.path.exists('/tmp/rmfp.cmd2'):
			os.remove('/tmp/rmfp.cmd2')
		for n in range(0, 8):
			try:
				f = open('/tmp/rmfp.cmd2', 'wb')
				try:
					f.write('100\n')
				finally:
					f.close()
			except Exception as e:
				print e
			if os.path.exists('/tmp/rmfp.cmd2'):
				break
			time.sleep(0.05)
		#Now we should return /proc/player
		hdparm = os.popen('killall rmfp_player')
		time.sleep(0.1)
		#TOMMY: VOLUME???
		self.close('*Stop*')

	#Directly go to standby disabled
	def exit2(self):
		pass
		#self.close('*StandBy*')

	def ok(self):
		self.ok1(5)

	def ok1(self, vreme):
		info1 = self.info1
		info2 = 'Filename: ' + self.MediaFileName
		info3 = self.GetFileSize(self.MediaFilePath)
		info4 = 'Audio codec: ' + self.ACodec + ' ' + self.ChNo + 'ch ' + str(int(self.SRate) // 1000) + 'kHz'
		info5 = 'Video codec: ' + self.VCodec + ' ' + self.Resol + ' ' + self.Format
		self.session.openWithCallback(self.ClBack2, MRUAInfoBar, 2, info1, info2, info3, info4, info5, vreme, 0, 0, self.MediaFType)

	def GetFileSize(self, pateka):
		tmp = os.stat(pateka).st_size
		if tmp // 1073741824 > 0:
			info3 = str(tmp // 107374182.4 / 10) + 'GB'
		elif tmp // 1048576 > 0:
			info3 = str(tmp // 104857.6 / 10) + 'MB'
		elif tmp // 1024 > 0:
			info3 = str(tmp // 102.4 / 10) + 'kB'
		else:
			info3 = str(tmp) + 'B'
		return info3

	def ZapRight(self):
		self.GetSec1()
		if self.MediaFType == 'audio':
			x = 10
		if self.MediaFType == 'video':
			x = 60
		sec3 = self.sec1 + x
		if self.sec2 == 0 or self.sec1 == 0:
			return
		if sec3 < self.sec2:
			info1 = self.info1
			info2 = 'Filename: ' + self.MediaFileName
			info3 = self.GetFileSize(self.MediaFilePath)
			info4 = 'Audio: ' + self.ACodec + ' ' + self.ChNo + 'ch ' + str(int(self.SRate) // 1000) + 'kHz'
			info5 = 'Video: ' + self.VCodec + ' ' + self.Resol + ' ' + self.Format
			self.session.openWithCallback(self.ClBack2, MRUAInfoBar, 1, info1, info2, info3, info4, info5, 0, sec3, self.sec2, self.MediaFType)
		else:
			sec3 = self.sec2

	def ZapLeft(self):
		self.GetSec1()
		if self.MediaFType == 'audio':
			x = 10
		if self.MediaFType == 'video':
			x = 60
		sec3 = self.sec1 - x
		if self.sec2 == 0 or self.sec1 == 0:
			return
		if sec3 > 0:
			info1 = self.info1
			info2 = 'Filename: ' + self.MediaFileName
			info3 = self.GetFileSize(self.MediaFilePath)
			info4 = 'Audio: ' + self.ACodec + ' ' + self.ChNo + 'ch ' + str(int(self.SRate) // 1000) + 'kHz'
			info5 = 'Video: ' + self.VCodec + ' ' + self.Resol + ' ' + self.Format
			self.session.openWithCallback(self.ClBack2, MRUAInfoBar, 1, info1, info2, info3, info4, info5, 0, sec3, self.sec2, self.MediaFType)
		else:
			sec3 = 0

	def ZapUp(self):
		self.GetSec1()
		if self.MediaFType == 'audio':
			x = 60
		if self.MediaFType == 'video':
			x = 300
		sec3 = self.sec1 + x
		if self.sec2 == 0 or self.sec1 == 0:
			return
		if sec3 < self.sec2:
			info1 = self.info1
			info2 = 'Filename: ' + self.MediaFileName
			info3 = self.GetFileSize(self.MediaFilePath)
			info4 = 'Audio: ' + self.ACodec + ' ' + self.ChNo + 'ch ' + str(int(self.SRate) // 1000) + 'kHz'
			info5 = 'Video: ' + self.VCodec + ' ' + self.Resol + ' ' + self.Format
			self.session.openWithCallback(self.ClBack2, MRUAInfoBar, 1, info1, info2, info3, info4, info5, 0, sec3, self.sec2, self.MediaFType)
		else:
			sec3 = self.sec2

	def ZapDown(self):
		self.GetSec1()
		if self.MediaFType == 'audio':
			x = 60
		if self.MediaFType == 'video':
			x = 300
		sec3 = self.sec1 - x
		if self.sec2 == 0 or self.sec1 == 0:
			return
		if sec3 > 0:
			info1 = self.info1
			info2 = 'Filename: ' + self.MediaFileName
			info3 = self.GetFileSize(self.MediaFilePath)
			info4 = 'Audio: ' + self.ACodec + ' ' + self.ChNo + 'ch ' + str(int(self.SRate) // 1000) + 'kHz'
			info5 = 'Video: ' + self.VCodec + ' ' + self.Resol + ' ' + self.Format
			self.session.openWithCallback(self.ClBack2, MRUAInfoBar, 1, info1, info2, info3, info4, info5, 0, sec3, self.sec2, self.MediaFType)
		else:
			sec3 = 0

	def keyPlay(self):
		vreme = 5
		self.FFval = 0
		self.REWval = 0
		if self.playpause == 103:
			self.playpause = 102
			self.info1 = 'Play |>'
		else:
			self.playpause = 103
			self.info1 = 'Paused ||'
		os.popen('echo ' + str(self.playpause) + ' > /tmp/rmfp.cmd2')
		time.sleep(0.05)
		os.popen('echo ' + str(self.playpause) + ' > /tmp/rmfp.cmd2')
		info1 = self.info1
		info2 = 'Filename: ' + self.MediaFileName
		info3 = self.GetFileSize(self.MediaFilePath)
		info4 = 'Audio: ' + self.ACodec + ' ' + self.ChNo + 'ch ' + str(int(self.SRate) // 1000) + 'kHz'
		info5 = 'Video: ' + self.VCodec + ' ' + self.Resol + ' ' + self.Format
		time.sleep(0.11)
		self.session.openWithCallback(self.ClBack2, MRUAInfoBar, 2, info1, info2, info3, info4, info5, vreme, 0, 0, self.MediaFType)

	def keyStop(self):
		self.playpause = 103
		os.popen('echo 105 > /tmp/rmfp.cmd2')
		time.sleep(0.05)
		os.popen('echo 105 > /tmp/rmfp.cmd2')

	def keyPrev(self):
		self.info1 = 'Play |>'
		self.FFval = 0
		self.GetSec1()
		if self.MediaFType == 'audio':
			x = 10
		if self.MediaFType == 'video':
			x = 60
		sec3 = self.sec1 - x
		if sec3 > 0:
			self.SendCMD2(sec3, 106)
			time.sleep(0.75)
		self.ok1(2)

	def keyNext(self):
		self.info1 = 'Play |>'
		self.FFval = 0
		self.GetSec1()
		if self.MediaFType == 'audio':
			x = 10
		if self.MediaFType == 'video':
			x = 60
		sec3 = self.sec1 + x
		if sec3 < self.sec2:
			self.SendCMD2(sec3, 106)
			time.sleep(0.75)
		self.ok1(2)

	def GetSec1(self):
		if os.path.exists('/tmp/rmfp.out2'):
			os.remove('/tmp/rmfp.out2')
		if os.path.exists('/tmp/rmfp.cmd2'):
			os.remove('/tmp/rmfp.cmd2')
		self.sec1 = 0
		self.sec2 = 0
		for n in range(0, 8):
			try:
				f = open('/tmp/rmfp.cmd2', 'wb')
				try:
					f.write('222\n')
				finally:
					f.close()
			except Exception as e:
				print e
			if os.path.exists('/tmp/rmfp.cmd2'):
				break
			time.sleep(0.05)
		time.sleep(0.03)
		for n in range(0, 8):
			try:
				tmpfile = open('/tmp/rmfp.out2', 'r')
				line = tmpfile.readlines()
				tmpfile.close()
				os.remove('/tmp/rmfp.out2')
				self.sec1 = int(line[1]) // 1000
				self.sec2 = int(line[0]) // 1000
				break
			except Exception:
				sec1 = 0
			time.sleep(0.1)

	def keyFF(self):
		if self.MediaFType != 'video':
			return
		vreme = 5
		FFcmd = '102'
		self.REWval = 0
		self.FFval += 1
		if self.FFval == 1:
			FFcmd = '143'
			self.info1 = 'Speed: x 1.2'
		if self.FFval == 2:
			FFcmd = '150'
			self.info1 = 'Speed: x 2.0'
		if self.FFval == 3:
			FFcmd = '109'
			self.info1 = 'Speed: x 4.0'
		if self.FFval == 4:
			FFcmd = '110'
			self.info1 = 'Speed: x 0.5'
		if self.FFval == 5:
			FFcmd = '144'
			self.info1 = 'Speed: x 0.8'
		if self.FFval > 5:
			self.FFval = 0
			FFcmd = '102'
			self.info1 = 'Play |>'
		self.playpause = 103
		cmd = 'echo ' + FFcmd + ' > /tmp/rmfp.cmd2'
		os.popen(cmd)
		time.sleep(0.05)
		os.popen(cmd)
		info1 = self.info1
		info2 = 'Filename: ' + self.MediaFileName
		info3 = self.GetFileSize(self.MediaFilePath)
		info4 = 'Audio: ' + self.ACodec + ' ' + self.ChNo + 'ch ' + str(int(self.SRate) // 1000) + 'kHz'
		info5 = 'Video: ' + self.VCodec + ' ' + self.Resol + ' ' + self.Format
		time.sleep(0.11)
		self.session.openWithCallback(self.ClBack2, MRUAInfoBar, 2, info1, info2, info3, info4, info5, vreme, 0, 0, self.MediaFType)

	def keyREW(self):
		if self.MediaFType != 'video':
			return
		vreme = 5
		REWcmd = '102'
		self.FFval = 0
		self.REWval += 1
		if self.REWval == 1:
			REWcmd = '144'
			self.info1 = 'Speed: x -0.5'
		if self.REWval == 2:
			REWcmd = '151'
			self.info1 = 'Speed: x -2.0'
		if self.REWval == 3:
			REWcmd = '112'
			self.info1 = 'Speed: x -4.0'
		if self.REWval > 3:
			REWcmd = '102'
			self.info1 = 'Play |>'
			self.REWval = 0
		self.playpause = 103
		cmd = 'echo ' + REWcmd + ' > /tmp/rmfp.cmd2'
		os.popen(cmd)
		time.sleep(0.05)
		os.popen(cmd)
		info1 = self.info1
		info2 = 'Filename: ' + self.MediaFileName
		info3 = self.GetFileSize(self.MediaFilePath)
		info4 = 'Audio: ' + self.ACodec + ' ' + self.ChNo + 'ch ' + str(int(self.SRate) // 1000) + 'kHz'
		info5 = 'Video: ' + self.VCodec + ' ' + self.Resol + ' ' + self.Format
		time.sleep(0.11)
		self.session.openWithCallback(self.ClBack2, MRUAInfoBar, 2, info1, info2, info3, info4, info5, vreme, 0, 0, self.MediaFType)

	def ClBack2(self, komanda):
		if komanda == '*REW*':
			self.keyREW()
		if komanda == '*FF*':
			self.keyFF()
		if komanda == '*PLAY*':
			self.keyPlay()
		if komanda == '*PREW*':
			self.keyPrev()
		if komanda == '*NEXT*':
			self.keyNext()

	def Konfig(self):
		if self.MediaFType != 'video':
			return
		self.session.openWithCallback(self.ClBackCfg, MRUAConfig, '1')

	def ALngSel(self):
		print "Trying to open Audio selection Dialog"
		#ino = len(self.ALanguages)
		#if self.MediaFType != 'video' or ino < 2:
		#	return
		self.session.openWithCallback(self.ClBackCfg, MRUASelectLang, self.ALanguages)

	def SubSel(self):
		print "Trying to open Subtitle selection Dialog"
		#ino = len(self.SubtitlesL)
		#if self.MediaFType != 'video' or ino < 2:
		#	return
		self.session.openWithCallback(self.ClBackCfg, MRUASelectSub, self.SubtitlesL)

	def ClBackCfg(self, komanda = None):
		if komanda == 'ok' and self.MediaFType == 'video':
			print 'ClBackCfg - return'

	def SendCMD2(self, k1, k2):
		if k1 >= 0:
			if os.path.exists('/tmp/rmfp.in2'):
				os.remove('/tmp/rmfp.in2')
			if os.path.exists('/tmp/rmfp.cmd2'):
				os.remove('/tmp/rmfp.cmd2')
			cmd = 'echo ' + str(k1) + ' > /tmp/rmfp.in2;echo ' + str(k2) + ' > /tmp/rmfp.cmd2'
			os.popen(cmd)
		else:
			if os.path.exists('/tmp/rmfp.cmd2'):
				os.remove('/tmp/rmfp.cmd2')
			os.popen('echo ' + str(k2) + ' > /tmp/rmfp.cmd2')

class MRUAInfoBar(Screen):

	skin = """
		<screen position="center,490" size="1280,200" title="" flags="wfNoBorder" zPosition="-1" >
		<ePixmap alphatest="off" pixmap="PLi-HD/infobar/hd.png" position="0,0" size="1280,220" zPosition="-1" />
		<widget name="infoC" position="220,60" zPosition="2" size="840,30" font="Regular;26" foregroundColor="#ffffff" transparent="1" halign="left" valign="center" />
		<widget name="media_progress" position="220,100" size="840,8" zPosition="2" pixmap="PLi-HD/infobar/pbar.png" backgroundColor="#333333" />
		<widget name="infoA" position="220,115" zPosition="2" size="150,15" font="Regular;14" foregroundColor="#ffffff" transparent="1" halign="left" valign="center" />
		<widget name="infoB" position="910,115" zPosition="2" size="150,15" font="Regular;14" foregroundColor="#ffffff" transparent="1" halign="right" valign="center" />
		<widget name="infoF" position="220,140" zPosition="2" size="300,20" font="Regular;18" foregroundColor="#aaaaaa" transparent="1" halign="left" valign="center" />
		<widget name="infoD" position="220,160" zPosition="2" size="300,20" font="Regular;18" foregroundColor="#aaaaaa" transparent="1" halign="left" valign="center" />
		<widget name="infoE" position="910,160" zPosition="2" size="150,20" font="Regular;18" foregroundColor="#aaaaaa" transparent="1" halign="right" valign="center" />
		</screen>"""

	def __init__(self, session, mod, info1, info2, info3, info4, info5, vremetr, vreme1, vreme2, ftype):
		Screen.__init__(self, session)
		self.session = session

		self.IMod = mod
		self.info1 = info1
		self.info2 = info2
		self.info3 = info3
		self.info4 = info4
		self.info5 = info5
		self.vremeT = vremetr
		self.vreme1 = vreme1
		self.vreme2 = vreme2
		self.MediaFType = ftype
		self['actions'] = ActionMap(['MediaPlayerActions',
		 'MediaPlayerSeekActions',
		 'ChannelSelectBaseActions',
		 'WizardActions',
		 'DirectionActions',
		 'MenuActions',
		 'NumberActions',
		 'ColorActions'], {'ok': self.ok,
		 'back': self.exit,
		 'left': self.ZapLeft,
		 'right': self.ZapRight,
		 'up': self.ZapUp,
		 'down': self.ZapDown,
		 'play': self.keyPlay,
		 'pause': self.keyPlay,
		 'stop': self.keyStop,
		 'seekFwd': self.keyFF,
		 'seekBack': self.keyREW,
		 'previous': self.keyPrev,
		 'next': self.keyNext}, -1)
		self.onLayoutFinish.append(self.StartScroll)
		self['infoA'] = Label()
		self['infoB'] = Label()
		self['infoC'] = Label()
		self['infoD'] = Label()
		self['infoE'] = Label()
		self['infoF'] = Label()
		self['infoG'] = Label()
		self['media_progress'] = ProgressBar()
		self['pozadina'] = Pixmap()
		self.msgno = 0
		self['infoA'].setText('0:00:00 / 0:00:00')
		self['infoB'].setText('0:00:00')
		self['infoC'].setText(self.info2)
		self['infoD'].setText(str(self.info4))
		self['infoE'].setText(self.info1)
		self['infoF'].setText(str(self.info5))
		self['infoG'].setText('Size: ' + self.info3)
		self.start_time = time.time()
		self.last_val = 0

	def exit(self):
		self.close('*EXIT*')

	def keyPlay(self):
		self.close('*PLAY*')

	def keyStop(self):
		self.close('*STOP*')

	def keyFF(self):
		self.close('*FF*')

	def keyREW(self):
		self.close('*REW*')

	def keyPrev(self):
		self.close('*PREW*')

	def keyNext(self):
		self.close('*NEXT*')

	def ok(self):
		if self.skok == 1:
			if os.path.exists('/tmp/rmfp.in2'):
				os.remove('/tmp/rmfp.in2')
			if os.path.exists('/tmp/rmfp.cmd2'):
				os.remove('/tmp/rmfp.cmd2')
			for n in range(0, 8):
				try:
					f = open('/tmp/rmfp.in2', 'wb')
					try:
						f.write(str(self.vreme1) + '\n')
					finally:
						f.close()
				except Exception as e:
					print e
				if os.path.exists('/tmp/rmfp.in2'):
					break
				time.sleep(0.05)
			time.sleep(0.03)
			for n in range(0, 8):
				try:
					f = open('/tmp/rmfp.cmd2', 'wb')
					try:
						f.write('106\n')
					finally:
						f.close()
				except Exception as e:
					print e
				if os.path.exists('/tmp/rmfp.cmd2'):
					break
				time.sleep(0.05)
		else:
			self.close('*EXIT*')

	def StartScroll(self):
		self.ExitTimer = eTimer()
		self.ExitTimer.callback.append(self.exit)
		self.ExitTimer.start(5000, True)
		plugin_path = '/usr/lib/enigma2/python/Plugins/Extensions/MediaCenter'
		self.slikaon = LoadPixmap(plugin_path + '/skins/default/images/hd.png')
		self['pozadina'].instance.setPixmap(self.slikaon)
		self.skok = 0
		if self.IMod == 1:
			self.skok = 1
			self.pozic = self.vreme1 * 100 // self.vreme2
			self.position = str(datetime.timedelta(seconds=self.vreme1)) + ' / ' + str(datetime.timedelta(seconds=int(self.vreme2 - self.vremeT)))
			self.length = str(datetime.timedelta(seconds=self.vreme2))
			self['media_progress'].setValue(self.pozic)
			self['infoA'].setText(self.position)
			self['infoB'].setText(self.length)
		if self.IMod == 2:
			self.NoLoop = 0
			self.position = '0:00:00 / 0:00:00'
			self.length = '0:00:00'
			self['media_progress'].setValue(0)
			self['infoA'].setText(self.position)
			self['infoB'].setText(self.length)
			self.sec1 = 0
			self.sec2 = 0
			self.pozic = 0
			self.msgTimer = eTimer()
			self.msgTimer.callback.append(self.updateMsg)
			self.msgTimer.start(10, True)
		if self.IMod == 3:
			self.NoLoop = 0
			self.position = '0:00:00 / 0:00:00'
			self.length = '0:00:00'
			self['media_progress'].setValue(0)
			self['infoA'].setText(self.position)
			self['infoB'].setText(self.length)
			self.sec1 = 0
			self.sec2 = 0
			self.pozic = 0
			self.msgTimer = eTimer()
			self.msgTimer.callback.append(self.updateMsg)
			self.msgTimer.start(3000, True)

	def ZapRight(self):
		self.skok = 1
		self.NoLoop = 0
		if self.MediaFType == 'audio':
			x = 10
		if self.MediaFType == 'video':
			x = 60
		self.vreme1 += x
		if self.vreme1 < self.vreme2:
			self.ZapDoThis()
		else:
			self.vreme1 -= 60

	def ZapLeft(self):
		self.skok = 1
		self.NoLoop = 0
		if self.MediaFType == 'audio':
			x = 10
		if self.MediaFType == 'video':
			x = 60
		self.vreme1 -= x
		if self.vreme1 > 0:
			self.ZapDoThis()
		else:
			self.vreme1 += 60

	def ZapUp(self):
		self.skok = 1
		self.NoLoop = 0
		if self.MediaFType == 'audio':
			x = 60
		if self.MediaFType == 'video':
			x = 300
		self.vreme1 += x
		if self.vreme1 < self.vreme2:
			self.ZapDoThis()
		else:
			self.vreme1 -= 300

	def ZapDown(self):
		self.skok = 1
		self.NoLoop = 0
		if self.MediaFType == 'audio':
			x = 60
		if self.MediaFType == 'video':
			x = 300
		self.vreme1 -= x
		if self.vreme1 > 0:
			self.ZapDoThis()
		else:
			self.vreme1 += 300

	def ZapDoThis(self):
		if self.vreme2 > 0:
			self.pozic = self.vreme1 * 100 // self.vreme2
		else:
			self.pozic = 0
			return
		self.position = str(datetime.timedelta(seconds=self.vreme1)) + ' / ' + str(datetime.timedelta(seconds=int(self.vreme2 - self.vreme1)))
		self.length = str(datetime.timedelta(seconds=self.vreme2))
		self['media_progress'].setValue(self.pozic)
		self['infoA'].setText(self.position)
		self['infoB'].setText(self.length)
		self.ExitTimer = eTimer()
		self.ExitTimer.callback.append(self.exit)
		self.ExitTimer.start(5000, True)

	def updateMsg(self):
		if self.skok == 1:
			return
		if os.path.exists('/tmp/rmfp.out2'):
			os.remove('/tmp/rmfp.out2')
		if os.path.exists('/tmp/rmfp.cmd2'):
			os.remove('/tmp/rmfp.cmd2')
		for n in range(0, 8):
			try:
				f = open('/tmp/rmfp.cmd2', 'wb')
				try:
					f.write('222\n')
				finally:
					f.close()
			except Exception as e:
				print e
			if os.path.exists('/tmp/rmfp.cmd2'):
				break
			time.sleep(0.05)
		time.sleep(0.03)
		for n in range(0, 8):
			try:
				tmpfile = open('/tmp/rmfp.out2', 'rb')
				line = tmpfile.readlines()
				tmpfile.close()
				os.remove('/tmp/rmfp.out2')
				self.sec1 = int(line[1]) // 1000
				self.sec2 = int(line[0]) // 1000
				self.position = str(datetime.timedelta(seconds=self.sec1)) + ' / ' + str(datetime.timedelta(seconds=int(self.sec2 - self.sec1)))
				self.length = str(datetime.timedelta(seconds=self.sec2))
				break
			except Exception:
				print 'Error updateMsg'
			time.sleep(0.1)
		if self.sec2 > 0:
			self.pozic = self.sec1 * 100 // self.sec2
		self['media_progress'].setValue(self.pozic)
		self['infoA'].setText(self.position)
		self['infoB'].setText(self.length)
		self.NoLoop += 1
		self.vreme1 = self.sec1
		self.vreme2 = self.sec2
		if self.NoLoop < self.vremeT and self.skok == 0:
			self.msgTimer.start(1000, True)
		else:
			self.close('*EXIT*')

class LoadSub(Screen):
	skin = """
		<screen position="center,center" size="710,390" title="MRUA - Load Subtitle">
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/skins/default/images/buttons/key_red_140x40.png" position="10,350" size="140,40" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/skins/default/images/buttons/key_green_140x40.png" position="560,350" size="140,40" alphatest="on" />
		<widget source="key_red" render="Label" position="10,350" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1"/>
		<widget source="key_green" render="Label" position="560,350" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1"/>
		<widget name="text" position="0,5" font="Regular;20" size="710,24" halign="center" />
		<widget name="list_left" position="5,45" size="700,295" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, pateka):
		Screen.__init__(self, session)
		self.session = session
		self.Pateka = pateka
		self['actions'] = ActionMap(['OkCancelActions', 'ShortcutActions', 'ColorActions'], {'red': self.quit,
		 'green': self.keyGo,
		 'blue': self.keyBlue,
		 'ok': self.keyGo,
		 'cancel': self.quit}, -2)
		self['key_red'] = StaticText(_('Cancel'))
		self['key_green'] = StaticText(_('Start'))
		self['text'] = Label(_('Select Device :'))
		path_left = self.Pateka
		self['list_left'] = FileList(path_left, matchingPattern='(?i)^.*\\.(sub|srt)')
		self.SOURCELIST = self['list_left']
		self.onLayoutFinish.append(self.keyGo)

	def keyGo(self):
		if self.SOURCELIST.canDescent():
			self.SOURCELIST.descent()
			if self.SOURCELIST.getCurrentDirectory():
				aaa = self.SOURCELIST.getCurrentDirectory()
				if len(aaa) > 40:
					aaa = '...' + aaa[len(aaa) - 40:]
				self['text'].setText(aaa)
			else:
				self['text'].setText('Select Device :')
		else:
			fn = self['list_left'].getFilename()
			self.SubFileName = fn
			playfile = self.SOURCELIST.getCurrentDirectory() + fn
			self.SubFilePath = playfile
			if os.path.splitext(fn)[1][1:] == 'srt':
				self.close(playfile)

	def keyBlue(self):
		print 'OK'

	def quit(self):
		self.close('empty')

class MRUAConfig(ConfigListScreen, Screen):
	skin = """
		<screen position="center,center" size="710,275" title="Setup" >
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/skins/default/images/buttons/key_red_140x40.png" position="10,230" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/skins/default/images/buttons/key_green_140x40.png" position="560,230" size="140,40" transparent="1" alphatest="on" />
		<widget source="key_red" render="Label" position="10,230" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_green" render="Label" position="560,230" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="text" render="Label" position="150,230" zPosition="1" size="400,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget name="config" position="10,10" size="690,210" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, args = None):
		Screen.__init__(self, session)
		self.session = session
		self.ActivePlay = args
		self.list = []
		self['actions'] = ActionMap(['ChannelSelectBaseActions',
		 'WizardActions',
		 'DirectionActions',
		 'MenuActions',
		 'NumberActions',
		 'ColorActions'], {'save': self.SaveCfg,
		 'back': self.Izlaz,
		 'ok': self.SaveCfg,
		 'green': self.SaveCfg,
		 'red': self.Izlaz}, -2)
		self['key_red'] = StaticText(_('Exit'))
		self['key_green'] = StaticText(_('Save Conf'))
		self['text'] = StaticText(_(' '))
		ConfigListScreen.__init__(self, self.list)
		self.ExtSub_Size_old = config.plugins.mc_mrua.ExtSub_Size.value
		self.ExtSub_Position_old = config.plugins.mc_mrua.ExtSub_Position.value
		self.ExtSub_Color_old = config.plugins.mc_mrua.ExtSub_Color.value
		self.Scaling_old = config.plugins.mc_mrua.Scaling.value
		self.UPnP_Enable_old = config.plugins.mc_mrua.UPnP_Enable.value
		self.ExtSub_Size_old1 = config.plugins.mc_mrua.ExtSub_Size.value
		self.ExtSub_Position_old1 = config.plugins.mc_mrua.ExtSub_Position.value
		self.ExtSub_Color_old1 = config.plugins.mc_mrua.ExtSub_Color.value
		self.Scaling_old1 = config.plugins.mc_mrua.Scaling.value
		self.UPnP_Enable_old1 = config.plugins.mc_mrua.UPnP_Enable.value
		self.createSetup()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(_('Subtitle Enable:'), config.plugins.mc_mrua.ExtSub_Enable))
		self.list.append(getConfigListEntry(_('Encoding (After changing, Player must be restarted):'), config.plugins.mc_mrua.ExtSub_Encoding))
		self.list.append(getConfigListEntry(_('Font Select (After changing, Player must be restarted):'), config.plugins.mc_mrua.ExtSub_FontSel))
		self.list.append(getConfigListEntry(_('Subtitle Font Size:'), config.plugins.mc_mrua.ExtSub_Size))
		self.list.append(getConfigListEntry(_('Subtitle Position:'), config.plugins.mc_mrua.ExtSub_Position))
		self.list.append(getConfigListEntry(_('Subtitle Color:'), config.plugins.mc_mrua.ExtSub_Color))
		self.list.append(getConfigListEntry(_('Scaling:'), config.plugins.mc_mrua.Scaling))
		if self.ActivePlay == None:
			self.list.append(getConfigListEntry(_('UPnP Enable:'), config.plugins.mc_mrua.UPnP_Enable))
		self['config'].list = self.list
		self['config'].l.setList(self.list)
		if self.ExtSub_Size_old != config.plugins.mc_mrua.ExtSub_Size.value:
			self.SendCMD2(config.plugins.mc_mrua.ExtSub_Size.value, 212)
		if self.ExtSub_Position_old != config.plugins.mc_mrua.ExtSub_Position.value:
			self.SendCMD2(config.plugins.mc_mrua.ExtSub_Position.value, 214)
		if self.ExtSub_Color_old != config.plugins.mc_mrua.ExtSub_Color.value:
			self.SendCMD2(config.plugins.mc_mrua.ExtSub_Color.value, 216)
		if self.Scaling_old != config.plugins.mc_mrua.Scaling.value:
			cmd = 0
		if config.plugins.mc_mrua.Scaling.value == 'Just Scale':
			cmd = 223
		if config.plugins.mc_mrua.Scaling.value == 'Pan&Scan':
			cmd = 224
		if config.plugins.mc_mrua.Scaling.value == 'Pillarbox':
			cmd = 225
		if cmd > 0:
			self.SendCMD2(-1, cmd)
		if self.UPnP_Enable_old != config.plugins.mc_mrua.UPnP_Enable.value:
			if config.plugins.mc_mrua.UPnP_Enable.value == '1':
				try:
					os.system('/etc/init.d/djmount start &')
					print ' >> START UPnP'
				except IOError:
					print 'Error START_UPnP'
			else:
				try:
					os.system('/etc/init.d/djmount stop &')
					print ' >> STOP UPnP'
				except IOError:
					print 'Error STOP_UPnP'
		self.ExtSub_Size_old = config.plugins.mc_mrua.ExtSub_Size.value
		self.ExtSub_Position_old = config.plugins.mc_mrua.ExtSub_Position.value
		self.ExtSub_Color_old = config.plugins.mc_mrua.ExtSub_Color.value
		self.Scaling_old = config.plugins.mc_mrua.Scaling.value
		self.UPnP_Enable_old = config.plugins.mc_mrua.UPnP_Enable.value

	def SendCMD2(self, k1, k2):
		if k1 >= 0:
			if os.path.exists('/tmp/rmfp.in2'):
				os.remove('/tmp/rmfp.in2')
			if os.path.exists('/tmp/rmfp.cmd2'):
				os.remove('/tmp/rmfp.cmd2')
			cmd = 'echo ' + str(k1) + ' > /tmp/rmfp.in2;echo ' + str(k2) + ' > /tmp/rmfp.cmd2'
			os.popen(cmd)
		else:
			if os.path.exists('/tmp/rmfp.cmd2'):
				os.remove('/tmp/rmfp.cmd2')
			os.popen('echo ' + str(k2) + ' > /tmp/rmfp.cmd2')

	def SaveCfg(self):
		config.plugins.mc_mrua.ExtSub_Enable.save()
		config.plugins.mc_mrua.ExtSub_Encoding.save()
		config.plugins.mc_mrua.ExtSub_FontSel.save()
		config.plugins.mc_mrua.ExtSub_Size.save()
		config.plugins.mc_mrua.ExtSub_Position.save()
		config.plugins.mc_mrua.ExtSub_Color.save()
		config.plugins.mc_mrua.ExtSub_OutColor.save()
		config.plugins.mc_mrua.Scaling.save()
		config.plugins.mc_mrua.UPnP_Enable.save()
		self.close('ok')

	def Izlaz(self):
		config.plugins.mc_mrua.ExtSub_Size.value = self.ExtSub_Size_old1
		config.plugins.mc_mrua.ExtSub_Position.value = self.ExtSub_Position_old1
		config.plugins.mc_mrua.ExtSub_Color.value = self.ExtSub_Color_old1
		config.plugins.mc_mrua.Scaling.value = self.Scaling_old1
		config.plugins.mc_mrua.UPnP_Enable.value = self.UPnP_Enable_old1
		self.SendCMD2(config.plugins.mc_mrua.ExtSub_Size.value, 212)
		time.sleep(0.11)
		self.SendCMD2(config.plugins.mc_mrua.ExtSub_Position.value, 214)
		time.sleep(0.11)
		self.SendCMD2(config.plugins.mc_mrua.ExtSub_Color.value, 216)
		time.sleep(0.11)
		cmd = 0
		if config.plugins.mc_mrua.Scaling.value == 'Just Scale':
			cmd = 223
		if config.plugins.mc_mrua.Scaling.value == 'Pan&Scan':
			cmd = 224
		if config.plugins.mc_mrua.Scaling.value == 'Pillarbox':
			cmd = 225
		if cmd > 0:
			self.SendCMD2(-1, cmd)
		time.sleep(0.11)
		if self.ActivePlay == None:
			if config.plugins.mc_mrua.UPnP_Enable.value == '1':
				try:
					os.system('/etc/init.d/djmount start &')
					print ' >> START UPnP'
				except IOError:
					print 'Error START_UPnP'
			else:
				try:
					os.system('/etc/init.d/djmount stop &')
					print ' >> STOP UPnP'
				except IOError:
					print 'Error STOP_UPnP'
		self.close()


class MRUASelectLang(ConfigListScreen, Screen):
	skin = """
		<screen position="center,center" size="710,275" title="Language Selection" >
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/skins/default/images/buttons/key_red_140x40.png" position="10,230" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/skins/default/images/buttons/key_green_140x40.png" position="560,230" size="140,40" transparent="1" alphatest="on" />
		<widget source="key_red" render="Label" position="10,230" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_green" render="Label" position="560,230" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="text" render="Label" position="150,230" zPosition="1" size="400,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget name="list" position="10,10" size="690,210" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, ALanguages):
		Screen.__init__(self, session)
		self.session = session
		self.ALanguages = ALanguages
		self.list = []
		self['actions'] = ActionMap(['ChannelSelectBaseActions',
		 'WizardActions',
		 'DirectionActions',
		 'MenuActions',
		 'NumberActions',
		 'ColorActions'], {'save': self.SetLang,
		 'back': self.Exit,
		 'ok': self.SetLang,
		 'green': self.SetLang,
		 'red': self.Exit}, -2)
		self['key_red'] = StaticText(_('Exit'))
		self['key_green'] = StaticText(_('Set'))
		self['text'] = StaticText(_(' '))
		list = []
		for subitem in self.ALanguages:
			ipos = subitem.find(':')
			ipos1 = subitem.rfind("'")
			if ipos > -1 and ipos1 > -1:
				subtmp = '   - Audio track :  | ' + subitem[ipos + 3:ipos1 - 1] + ' |'
				list.append(subtmp)
		self['list'] = MenuList(list)

	def SendCMD2(self, k1, k2):
		if k1 >= 0:
			if os.path.exists('/tmp/rmfp.in2'):
				os.remove('/tmp/rmfp.in2')
			if os.path.exists('/tmp/rmfp.cmd2'):
				os.remove('/tmp/rmfp.cmd2')
			cmd = 'echo ' + str(k1) + ' > /tmp/rmfp.in2;echo ' + str(k2) + ' > /tmp/rmfp.cmd2'
			os.popen(cmd)
		else:
			if os.path.exists('/tmp/rmfp.cmd2'):
				os.remove('/tmp/rmfp.cmd2')
			os.popen('echo ' + str(k2) + ' > /tmp/rmfp.cmd2')

	def SetLang(self):
		ind = self['list'].getSelectionIndex()
		tmpstr = self.ALanguages[ind]
		ipos = tmpstr.find('ID')
		ipos1 = tmpstr.find('(')
		if ipos >= 0 and ipos1 >= 0:
			AudioL = int(tmpstr[ipos + 2:ipos1])
		self.SendCMD2(AudioL, 116)
		time.sleep(0.11)
		self.close()

	def Exit(self):
		self.close()

class MRUASelectSub(ConfigListScreen, Screen):
	skin = """
		<screen position="center,center" size="710,275" title="Subtitle Selection" >
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/skins/default/images/buttons/key_red_140x40.png" position="10,230" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MediaCenter/skins/default/images/buttons/key_green_140x40.png" position="560,230" size="140,40" transparent="1" alphatest="on" />
		<widget source="key_red" render="Label" position="10,230" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_green" render="Label" position="560,230" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="text" render="Label" position="150,230" zPosition="1" size="400,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget name="list" position="10,10" size="690,210" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, SubtitlesL):
		Screen.__init__(self, session)
		self.session = session
		self.SubtitlesL = SubtitlesL
		self.list = []
		self['actions'] = ActionMap(['ChannelSelectBaseActions',
		 'WizardActions',
		 'DirectionActions',
		 'MenuActions',
		 'NumberActions',
		 'ColorActions'], {'save': self.SetLang,
		 'back': self.Exit,
		 'ok': self.SetLang,
		 'green': self.SetLang,
		 'red': self.Exit}, -2)
		self['key_red'] = StaticText(_('Exit'))
		self['key_green'] = StaticText(_('Set'))
		self['text'] = StaticText(_(' '))
		list = []
		for subitem in self.SubtitlesL:
			ipos = subitem.find(':')
			ipos1 = subitem.find('[')
			if ipos > -1 and ipos1 > -1:
				subtrack = subitem[ipos + 3:ipos1 - 2]
				if subtrack == 'tmp.srt':
					subtrack = 'External'
				subtmp = '   - Subtitle track :  | ' + subtrack + ' |'
				list.append(subtmp)
		self['list'] = MenuList(list)

	def SendCMD2(self, k1, k2):
		if k1 >= 0:
			if os.path.exists('/tmp/rmfp.in2'):
				os.remove('/tmp/rmfp.in2')
			if os.path.exists('/tmp/rmfp.cmd2'):
				os.remove('/tmp/rmfp.cmd2')
			cmd = 'echo ' + str(k1) + ' > /tmp/rmfp.in2;echo ' + str(k2) + ' > /tmp/rmfp.cmd2'
			os.popen(cmd)
		else:
			if os.path.exists('/tmp/rmfp.cmd2'):
				os.remove('/tmp/rmfp.cmd2')
			os.popen('echo ' + str(k2) + ' > /tmp/rmfp.cmd2')

	def SetLang(self):
		ind = self['list'].getSelectionIndex()
		tmpstr = self.SubtitlesL[ind]
		ipos = tmpstr.find('ID')
		ipos1 = tmpstr.find('(')
		if ipos >= 0 and ipos1 >= 0:
			SubtitleL = int(tmpstr[ipos + 2:ipos1])
		self.SendCMD2(SubtitleL, 118)
		time.sleep(0.11)
		self.close()

	def Exit(self):
		self.close()

global cache
