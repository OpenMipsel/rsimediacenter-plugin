# -*- coding: UTF-8 -*-
from __future__ import print_function
from Plugins.Plugin import PluginDescriptor
from twisted.web.client import downloadPage
from enigma import ePicLoad, eServiceReference
from Screens.Screen import Screen
from Screens.EpgSelection import EPGSelection
from Screens.ChannelSelection import SimpleChannelSelection
from Screens.ChoiceBox import ChoiceBox
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.Button import Button
from Components.AVSwitch import AVSwitch
from Components.MenuList import MenuList
from Components.Language import language
from Components.ProgressBar import ProgressBar
from Components.Sources.StaticText import StaticText
from Components.config import config, ConfigSubsection, ConfigYesNo
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS, SCOPE_SKIN_IMAGE
from os import environ as os_environ
from NTIVirtualKeyBoard import NTIVirtualKeyBoard
import re
try:
	import htmlentitydefs
	from urllib import quote_plus
	iteritems = lambda d: d.iteritems()
except ImportError as ie:
	from html import entities as htmlentitydefs
	from urllib.parse import quote_plus
	iteritems = lambda d: d.items()
	unichr = chr
import gettext

config.plugins.imdb = ConfigSubsection()
config.plugins.imdb.force_english = ConfigYesNo(default=False)

def quoteEventName(eventName, safe="/()" + ''.join(map(chr,range(192,255)))):
	# BBC uses '\x86' markers in program names, remove them
	text = eventName.decode('utf8').replace(u'\x86', u'').replace(u'\x87', u'').encode('latin-1','ignore')
	# IMDb doesn't seem to like urlencoded characters at all, hence the big "safe" list
	return quote_plus(text, safe=safe)

class IMDB(Screen):
	
	def __init__(self, session, eventName, callbackNeeded=False):
		Screen.__init__(self, session)

		self.eventName = eventName
		
		self.callbackNeeded = callbackNeeded
		self.callbackData = ""
		self.callbackGenre = ""

		self.dictionary_init()

		self["poster"] = Pixmap()
		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.paintPosterPixmapCB)

		self["stars"] = ProgressBar()
		self["starsbg"] = Pixmap()
		self["stars"].hide()
		self["starsbg"].hide()
		self.ratingstars = -1

		self["title"] = StaticText(_("The Internet Movie Database"))
		# map new source -> old component
		def setText(txt):
			StaticText.setText(self["title"], txt)
			self["titellabel"].setText(txt)
		self["title"].setText = setText
		self["titellabel"] = Label()
		self["detailslabel"] = ScrollLabel("")
		self["menulabel"] = ScrollLabel("")
		self["castlabel"] = ScrollLabel("")
		self["extralabel"] = ScrollLabel("")
		self["statusbar"] = Label("")
		self["ratinglabel"] = Label("")
		self.resultlist = []
		self["menu"] = MenuList(self.resultlist)
		self["menu"].hide()

		self["key_red"] = Button(_("Exit"))
		self["key_green"] = Button("")
		self["key_yellow"] = Button("")
		self["key_blue"] = Button(_("Enter Search"))

		# 0 = multiple query selection menu page
		# 1 = movie info page
		# 2 = extra infos page
		self.Page = 0

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "MovieSelectionActions", "DirectionActions"],
		{
			"ok": self.showDetails,
			"cancel": self.exit,
			"down": self.pageDown,
			"up": self.pageUp,
			"red": self.exit,
			"yellow": self.showMenu,
			"blue": self.openVirtualKeyBoard,
			"contextMenu": self.contextMenuPressed,
			"showEventInfo": self.showDetails
		}, -1)

		self.getIMDB()

	def exit(self):
		if self.callbackNeeded:
			self.close([self.callbackData, self.callbackGenre])
		else:
			self.close()

	event_quoted = property(lambda self: quote_plus(self.eventName.encode('utf8')))

	def dictionary_init(self):
		syslang = language.getLanguage()
		if "de" not in syslang or config.plugins.imdb.force_english.value:
			self.IMDBlanguage = ""  # set to empty ("") for english version

			self.generalinfomask = re.compile(
			'<h1 class="header".*?>(?P<title>.*?)<.*?</h1>.*?'
			'(?:.*?<h4 class="inline">\s*(?P<g_director>Regisseur|Directors?):\s*</h4>.*?<a\s+href=\".*?\"\s*>(?P<director>.*?)</a>)*'
			'(?:.*?<h4 class="inline">\s*(?P<g_creator>Sch\S*?pfer|Creators?):\s*</h4>.*?<a\s+href=\".*?\"\s*>(?P<creator>.*?)</a>)*'
			'(?:.*?<h4 class="inline">\s*(?P<g_seasons>Seasons?):\s*</h4>.*?<a\s+href=\".*?\"\s*>(?P<seasons>\d+?)</a>)*'
			'(?:.*?<h4 class="inline">\s*(?P<g_writer>Drehbuch|Writer).*?</h4>.*?<a\s+href=\".*?\"\s*>(?P<writer>.*?)</a>)*'
			'(?:.*?<h4 class="inline">\s*(?P<g_country>Land|Country):\s*</h4>.*?<a\s+href=\".*?\"\s*>(?P<country>.*?)</a>)*'
			'(?:.*?<h4 class="inline">\s*(?P<g_premiere>Premiere|Release Date).*?</h4>\s+(?P<premiere>.*?)\s*<span)*'
			'(?:.*?<h4 class="inline">\s*(?P<g_alternativ>Auch bekannt als|Also Known As):\s*</h4>\s*(?P<alternativ>.*?)\s*<span)*'
			, re.DOTALL)

			self.extrainfomask = re.compile(
			'(?:.*?<h4 class="inline">(?P<g_outline>Kurzbeschreibung|Plot Outline):</h4>(?P<outline>.+?)<)*'
			'(?:.*?<h2>(?P<g_synopsis>Storyline)</h2>.*?<p>(?P<synopsis>.+?)\s*</p>)*'
			'(?:.*?<h4 class="inline">(?P<g_keywords>Plot Keywords):</h4>(?P<keywords>.+?)(?:Mehr|See more</a>|</div>))*'
			'(?:.*?<h4 class="inline">(?P<g_tagline>Werbezeile|Tagline?):</h4>\s*(?P<tagline>.+?)<)*'
			'(?:.*?<h4 class="inline">(?P<g_awards>Filmpreise|Awards):</h4>\s*(?P<awards>.+?)(?:Mehr|See more</a>|</div>))*'
			'(?:.*?<h4 class="inline">(?P<g_language>Sprache|Language):</h4>\s*(?P<language>.+?)</div>)*'
			'(?:.*?<h4 class="inline">(?P<g_locations>Drehorte|Filming Locations):</h4>.*?<a\s+href=\".*?\">(?P<locations>.+?)</a>)*'
			'(?:.*?<h4 class="inline">(?P<g_runtime>L\S*?nge|Runtime):</h4>\s*(?P<runtime>.+?)</div>)*'
			'(?:.*?<h4 class="inline">(?P<g_sound>Tonverfahren|Sound Mix):</h4>\s*(?P<sound>.+?)</div>)*'
			'(?:.*?<h4 class="inline">(?P<g_color>Farbe|Color):</h4>\s*(?P<color>.+?)</div>)*'
			'(?:.*?<h4 class="inline">(?P<g_aspect>Seitenverh\S*?ltnis|Aspect Ratio):</h4>\s*(?P<aspect>.+?)(?:Mehr|See more</a>|</div>))*'
			'(?:.*?<h4 class="inline">(?P<g_cert>Altersfreigabe|Certification):</h4>\s*(?P<cert>.+?)</div>)*'
			'(?:.*?<h4 class="inline">(?P<g_company>Firma|Company):</h4>\s*(?P<company>.+?)(?:Mehr|See more</a>|</div>))*'
			'(?:.*?<h4>(?P<g_trivia>Dies und das|Trivia)</h4>\s*(?P<trivia>.+?)(?:<span))*'
			'(?:.*?<h4>(?P<g_goofs>Pannen|Goofs)</h4>\s*(?P<goofs>.+?)(?:<span))*'
			'(?:.*?<h4>(?P<g_quotes>Dialogzitate|Quotes)</h4>\s*(?P<quotes>.+?)(?:<span))*'
			'(?:.*?<h4>(?P<g_connections>Bez\S*?ge zu anderen Titeln|Movie Connections)</h4>\s*(?P<connections>.+?)(?:<span))*'
			'(?:.*?<h2>(?P<g_comments>Nutzerkommentare|User Reviews)</h2>.*?<a href="/user/ur\d{7,7}/comments">(?P<commenter>.+?)</a>.*?<p>(?P<comment>.+?)</p>)*'
			, re.DOTALL)

			self.genreblockmask = re.compile('<h4 class="inline">Genre:</h4>\s<div class="info-content">\s+?(.*?)\s+?(?:Mehr|See more|</p|<a class|</div>)', re.DOTALL)
			self.ratingmask = re.compile('="ratingValue">(?P<rating>.*?)</', re.DOTALL)
			self.castmask = re.compile('<td class="name">\s*<a.*?>(.*?)</a>.*?<td class="character">\s*<div>\s*(?:<a.*?>)?(.*?)(?:</a>)?\s*( \(as.*?\))?\s*</div>', re.DOTALL)
			self.postermask = re.compile('<td .*?id="img_primary">.*?<img .*?src=\"(http.*?)\"', re.DOTALL)
		else:
			self.IMDBlanguage = "german." # it's a subdomain, so add a '.' at the end

			self.generalinfomask = re.compile(
			'<h1>(?P<title>.*?) <.*?</h1>.*?'
			'(?:.*?<h5>(?P<g_director>Regisseur|Directors?):</h5>.*?<a href=\".*?\">(?P<director>.*?)</a>)*'
			'(?:.*?<h5>(?P<g_creator>Sch\S*?pfer|Creators?):</h5>.*?<a href=\".*?\">(?P<creator>.*?)</a>)*'
			'(?:.*?<h5>(?P<g_seasons>Seasons):</h5>(?:.*?)<a href=\".*?\">(?P<seasons>\d+?)</a>\s+?(?:<a class|\|\s+?<a href="episodes#season-unknown))*'
			'(?:.*?<h5>(?P<g_writer>Drehbuch|Writer).*?</h5>.*?<a href=\".*?\">(?P<writer>.*?)</a>)*'
			'(?:.*?<h5>(?P<g_premiere>Premiere|Release Date).*?</h5>\s+<div.*?>\s?(?P<premiere>.*?)\n\s.*?<)*'
			'(?:.*?<h5>(?P<g_alternativ>Auch bekannt als|Also Known As):</h5><div.*?>\s*(?P<alternativ>.*?)(?:<br>)?\s*<a.*?>(?:Mehr|See more))*'
			'(?:.*?<h5>(?P<g_country>Land|Country):</h5>\s+<div.*?>(?P<country>.*?)</div>(?:.*?Mehr|\s+?</div>))*'
			, re.DOTALL)

			self.extrainfomask = re.compile(
			'(?:.*?<h5>(?P<g_tagline>Werbezeile|Tagline?):</h5>\n(?P<tagline>.+?)<)*'
			'(?:.*?<h5>(?P<g_outline>Kurzbeschreibung|Handlung):</h5>(?P<outline>.+?)<)*'
			'(?:.*?<h5>(?P<g_synopsis>Plot Synopsis):</h5>(?:.*?)(?:<a href=\".*?\">)*?(?P<synopsis>.+?)(?:</a>|</div>))*'
			'(?:.*?<h5>(?P<g_keywords>Plot Keywords):</h5>(?P<keywords>.+?)(?:Mehr|See more</a>|</div>))*'
			'(?:.*?<h5>(?P<g_awards>Filmpreise|Awards):</h5>(?P<awards>.+?)(?:Mehr|See more</a>|</div>))*'
			'(?:.*?<h5>(?P<g_runtime>L\S*?nge|Runtime):</h5>(?P<runtime>.+?)</div>)*'
			'(?:.*?<h5>(?P<g_language>Sprache|Language):</h5>(?P<language>.+?)</div>)*'
			'(?:.*?<h5>(?P<g_color>Farbe|Color):</h5>(?P<color>.+?)</div>)*'
			'(?:.*?<h5>(?P<g_aspect>Seitenverh\S*?ltnis|Aspect Ratio):</h5>(?P<aspect>.+?)(?:Mehr|See more</a>|</div>))*'
			'(?:.*?<h5>(?P<g_sound>Tonverfahren|Sound Mix):</h5>(?P<sound>.+?)</div>)*'
			'(?:.*?<h5>(?P<g_cert>Altersfreigabe|Certification):</h5>(?P<cert>.+?)</div>)*'
			'(?:.*?<h5>(?P<g_locations>Drehorte|Filming Locations):</h5>(?P<locations>.+?)(?:Mehr|See more</a>|</div>))*'
			'(?:.*?<h5>(?P<g_company>Firma|Company):</h5>(?P<company>.+?)(?:Mehr|See more</a>|</div>))*'
			'(?:.*?<h5>(?P<g_trivia>Dies und das|Trivia):</h5>(?P<trivia>.+?)(?:Mehr|See more</a>|</div>))*'
			'(?:.*?<h5>(?P<g_goofs>Pannen|Goofs):</h5>(?P<goofs>.+?)(?:Mehr|See more</a>|</div>))*'
			'(?:.*?<h5>(?P<g_quotes>Dialogzitate|Quotes):</h5>(?P<quotes>.+?)(?:Mehr|See more</a>|</div>))*'
			'(?:.*?<h5>(?P<g_connections>Bez\S*?ge zu anderen Titeln|Movie Connections):</h5>(?P<connections>.+?)(?:Mehr|See more</a>|</div>))*'
			'(?:.*?<h3>(?P<g_comments>Nutzerkommentare|User Comments)</h3>.*?<a href="/user/ur\d{7,7}/comments">(?P<commenter>.+?)\n</div>.*?<p>(?P<comment>.+?)</p>)*'
			, re.DOTALL)

			self.genreblockmask = re.compile('<h5>Genre:</h5>\s<div class="info-content">\s+?(.*?)\s+?(?:Mehr|See more|</p|<a class|</div>)', re.DOTALL)
			self.ratingmask = re.compile('<h5>(?P<g_rating>Nutzer-Bewertung|User Rating):</h5>.*?<b>(?P<rating>.*?)/10</b>', re.DOTALL)
			self.castmask = re.compile('<td class="nm">.*?>(.*?)</a>.*?<td class="char">(?:<a.*?>)?(.*?)(?:</a>)?(\s\(.*?\))?</td>', re.DOTALL)
			self.postermask = re.compile('<div class="photo">.*?<img .*? src=\"(http.*?)\" .*?>', re.DOTALL)

		self.htmltags = re.compile('<.*?>')

	def resetLabels(self):
		self["detailslabel"].setText("")
		self["ratinglabel"].setText("")
		self["title"].setText("")
		self["castlabel"].setText("")
		self["titellabel"].setText("")
		self["extralabel"].setText("")
		self.ratingstars = -1

	def pageUp(self):
		if self.Page == 0:
			self["menu"].instance.moveSelection(self["menu"].instance.moveUp)
		if self.Page == 1:
			self["castlabel"].pageUp()
			self["detailslabel"].pageUp()
		if self.Page == 2:
			self["extralabel"].pageUp()

	def pageDown(self):
		if self.Page == 0:
			self["menu"].instance.moveSelection(self["menu"].instance.moveDown)
		if self.Page == 1:
			self["castlabel"].pageDown()
			self["detailslabel"].pageDown()
		if self.Page == 2:
			self["extralabel"].pageDown()

	def showMenu(self):
		if ( self.Page is 1 or self.Page is 2 ) and self.resultlist:
			self["menu"].show()
			self["stars"].hide()
			self["starsbg"].hide()
			self["ratinglabel"].hide()
			self["castlabel"].hide()
			self["poster"].hide()
			self["extralabel"].hide()
			self["detailslabel"].hide()
			self["title"].setText(_("Ambiguous results"))
			self["menulabel"].setText(_("Please select the matching entry"))
			self["menulabel"].show()
			self.Page = 0

	def showDetails(self):
		self["ratinglabel"].show()
		self["detailslabel"].show()
		self["extralabel"].show()

		if self.resultlist and self.Page == 0:
			link = self["menu"].getCurrent()[1]
			title = self["menu"].getCurrent()[0]
			self["statusbar"].setText(_("Re-Query IMDb: %s...") % (title))
			localfile = "/tmp/imdbquery2.html"
			fetchurl = "http://" + self.IMDBlanguage + "imdb.com/title/" + link
			print("[IMDB] downloading query " + fetchurl + " to " + localfile)
			downloadPage(fetchurl,localfile).addCallback(self.IMDBquery2).addErrback(self.fetchFailed)
			self["menu"].hide()
			self["menulabel"].hide()
			self.resetLabels()
			self["key_yellow"].setText(_("Title List"))
			self.Page = 1

	def contextMenuPressed(self):
		list = [
			(_("Enter search"), self.openVirtualKeyBoard),
		]

		self.session.openWithCallback(
			self.menuCallback,
			ChoiceBox,
			list = list,
		)

	def menuCallback(self, ret = None):
		ret and ret[1]()

	def openVirtualKeyBoard(self):
		self.session.openWithCallback(
			self.gotSearchString,
			NTIVirtualKeyBoard,
			title = _("Enter text to search for"))

	def gotSearchString(self, ret = None):
		if ret:
			self.eventName = ret
			self.Page = 0
			self.resultlist = []
			self["menu"].hide()
			self["ratinglabel"].show()
			self["detailslabel"].show()
			self["extralabel"].show()
			self["poster"].hide()
			self["stars"].hide()
			self["starsbg"].hide()
			self.getIMDB()

	def getIMDB(self):
		self.resetLabels()
		if not self.eventName:
			s = self.session.nav.getCurrentService()
			info = s and s.info()
			event = info and info.getEvent(0) # 0 = now, 1 = next
			if event:
				self.eventName = event.getEventName()
		if self.eventName:
			self["statusbar"].setText(_("Query IMDb: %s...") % (self.eventName))
			event_quoted = quoteEventName(self.eventName)
			localfile = "/tmp/imdbquery.html"
			if self.IMDBlanguage:
				fetchurl = "http://" + self.IMDBlanguage + "imdb.com/find?q=" + event_quoted + "&s=tt&site=aka"
			else:
				fetchurl = "http://akas.imdb.com/find?s=tt;mx=20;q=" + event_quoted
			print("[IMDB] Downloading Query " + fetchurl + " to " + localfile)
			downloadPage(fetchurl,localfile).addCallback(self.IMDBquery).addErrback(self.fetchFailed)
		else:
			self["statusbar"].setText(_("Could't get Eventname"))

	def fetchFailed(self,string):
		print("[IMDB] fetch failed", string)
		self["statusbar"].setText(_("IMDb Download failed"))

	def html2utf8(self,in_html):
		entitydict = {}

		entities = re.finditer('&([^#][A-Za-z]{1,5}?);', in_html)
		for x in entities:
			key = x.group(0)
			if key not in entitydict:
				entitydict[key] = htmlentitydefs.name2codepoint[x.group(1)]

		entities = re.finditer('&#x([0-9A-Fa-f]{2,2}?);', in_html)
		for x in entities:
			key = x.group(0)
			if key not in entitydict:
				entitydict[key] = "%d" % int(key[3:5], 16)

		entities = re.finditer('&#(\d{1,5}?);', in_html)
		for x in entities:
			key = x.group(0)
			if key not in entitydict:
				entitydict[key] = x.group(1)

		for key, codepoint in iteritems(entitydict):
			in_html = in_html.replace(key, unichr(int(codepoint)).encode('latin-1', 'ignore'))
		self.inhtml = in_html.decode('latin-1').encode('utf8')

	def IMDBquery(self,string):
		print("[IMDBquery]")
		self["statusbar"].setText(_("IMDb Download completed"))

		self.html2utf8(open("/tmp/imdbquery.html", "r").read())

		self.generalinfos = self.generalinfomask.search(self.inhtml)

		if self.generalinfos:
			self.IMDBparse()
		else:
			if re.search("<title>(?:IMDb.{0,9}Search|IMDb Titelsuche)</title>", self.inhtml):
				searchresultmask = re.compile("<tr> <td.*?img src.*?>.*?<a href=\".*?/title/(tt\d{7,7})/\".*?>(.*?)</td>", re.DOTALL)
				searchresults = searchresultmask.finditer(self.inhtml)
				self.resultlist = [(self.htmltags.sub('',x.group(2)), x.group(1)) for x in searchresults]
				Len = len(self.resultlist)
				self["menu"].l.setList(self.resultlist)
				if Len == 1:
					self["statusbar"].setText(_("Re-Query IMDb: %s...") % (self.resultlist[0][0],))
					self.eventName = self.resultlist[0][1]
					localfile = "/tmp/imdbquery.html"
					fetchurl = "http://" + self.IMDBlanguage + "imdb.com/find?q=" + self.event_quoted + "&s=tt&site=aka"
					print("[IMDB] Downloading Query " + fetchurl + " to " + localfile)
					downloadPage(fetchurl,localfile).addCallback(self.IMDBquery).addErrback(self.fetchFailed)
				elif Len > 1:
					self.Page = 1
					self.showMenu()
				else:
					self["statusbar"].setText(_("No IMDb match."))
			else:
				splitpos = self.eventName.find('(')
				if splitpos > 0 and self.eventName.endswith(')'):
					self.eventName = self.eventName[splitpos+1:-1]
					self["statusbar"].setText(_("Re-Query IMDb: %s...") % (self.eventName))
					event_quoted = quoteEventName(self.eventName)
					localfile = "/tmp/imdbquery.html"
					fetchurl = "http://" + self.IMDBlanguage + "imdb.com/find?q=" + event_quoted + "&s=tt&site=aka"
					print("[IMDB] Downloading Query " + fetchurl + " to " + localfile)
					downloadPage(fetchurl,localfile).addCallback(self.IMDBquery).addErrback(self.fetchFailed)

	def IMDBquery2(self,string):
		self["statusbar"].setText(_("IMDb Re-Download completed"))
		self.html2utf8(open("/tmp/imdbquery2.html", "r").read())
		self.generalinfos = self.generalinfomask.search(self.inhtml)
		self.IMDBparse()

	def IMDBparse(self):
		print("[IMDBparse]")
		self.Page = 1
		Detailstext = _("No details found.")
		if self.generalinfos:
			self["statusbar"].setText(_("IMDb Details parsed"))
			Titeltext = self.generalinfos.group("title")
			if len(Titeltext) > 57:
				Titeltext = Titeltext[0:54] + "..."
			self["title"].setText(Titeltext)

			Detailstext = ""

			genreblock = self.genreblockmask.findall(self.inhtml)
			if genreblock:
				genres = self.htmltags.sub('', genreblock[0])
				if genres:
					Detailstext += _("Genre:") + " "
					Detailstext += genres
					self.callbackGenre = genres

			for category in ("director", "creator", "writer", "seasons"):
				if self.generalinfos.group(category):
					Detailstext += "\n" + self.generalinfos.group('g_'+category) + ": " + self.generalinfos.group(category)

			for category in ("premiere", "country", "alternativ"):
				if self.generalinfos.group(category):
					Detailstext += "\n" + self.generalinfos.group('g_'+category) + ": " + self.htmltags.sub('', self.generalinfos.group(category).replace('\n',' ').replace("<br>", '\n').replace("<br />",'\n').replace("  ",' '))

			rating = self.ratingmask.search(self.inhtml)
			Ratingtext = _("no user rating yet")
			if rating:
				rating = rating.group("rating")
				if rating != '<span id="voteuser"></span>':
					Ratingtext = _("User Rating") + ": " + rating + " / 10"
					self.ratingstars = int(10*round(float(rating.replace(',','.')),1))
					self["stars"].show()
					self["stars"].setValue(self.ratingstars)
					self["starsbg"].show()
			self["ratinglabel"].setText(Ratingtext)

			castresult = self.castmask.finditer(self.inhtml)
			if castresult:
				Casttext = ""
				for x in castresult:
					Casttext += "\n" + self.htmltags.sub('', x.group(1))
					if x.group(2):
						Casttext += _(" as ") + self.htmltags.sub('', x.group(2).replace('/ ...','')).replace('\n', ' ')
						if x.group(3):
							Casttext += x.group(3)
				if Casttext:
					Casttext = _("Cast:") + " " + Casttext
				else:
					Casttext = _("No cast list found in the database.")
				self["castlabel"].setText(Casttext)
				self["castlabel"].hide() #Hide this as I dont want this to show for now

			posterurl = self.postermask.search(self.inhtml)
			if posterurl and posterurl.group(1).find("jpg") > 0:
				posterurl = posterurl.group(1)
				self["statusbar"].setText(_("Downloading Movie Poster: %s...") % (posterurl))
				localfile = "/tmp/poster.jpg"
				print("[IMDB] downloading poster " + posterurl + " to " + localfile)
				downloadPage(posterurl,localfile).addCallback(self.IMDBPoster).addErrback(self.fetchFailed)
			else:
				self.IMDBPoster("kein Poster")

			extrainfos = self.extrainfomask.search(self.inhtml)
			if extrainfos:
				Extratext = "\n"

				for category in ("tagline","outline","synopsis","keywords","awards","runtime"):
					if extrainfos.group('g_'+category):
						Extratext += extrainfos.group('g_'+category) + ": " + self.htmltags.sub('',extrainfos.group(category).replace("\n",'').replace("<br>", '\n').replace("<br />",'\n')) + "\n\n"

				self["extralabel"].setText(Extratext)

		self["detailslabel"].setText(Detailstext)
		self["key_yellow"].setText(_("Title List"))
		self.callbackData = Detailstext

	def IMDBPoster(self,string):
		self["statusbar"].setText(_("IMDb Details parsed"))
		if not string:
			filename = "/tmp/poster.jpg"
		else:
			filename = resolveFilename(SCOPE_PLUGINS, "Extensions/IMDb/no_poster.png")
		sc = AVSwitch().getFramebufferScale()
		self.picload.setPara((self["poster"].instance.size().width(), self["poster"].instance.size().height(), sc[0], sc[1], False, 1, "#00000000"))
		self.picload.startDecode(filename)

	def paintPosterPixmapCB(self, picInfo=None):
		ptr = self.picload.getData()
		if ptr != None:
			self["poster"].instance.setPixmap(ptr.__deref__())
			self["poster"].show()

