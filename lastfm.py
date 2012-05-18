#! /usr/bin/python
import logging
import optparse
import exceptions
from datetime import timedelta
import time
from datetime import datetime as dt
import pytz as tz
from collections import OrderedDict
from edatoolkit import qLogFile,Event
import urllib2
import urllib
import json
import copy

def annotateLogfileFromTracks(logfile,username):
	from edatoolkit import qLogFile,Event
	lastfm = LastFM(username)
	tracks = lastfm.getRecentTracks(start=logfile.startTime, end=logfile.endTime)
	for track in tracks:
		e = Event(track["date"],end=(track["date"] + timedelta(seconds=track["duration"])),note=(track["name"] + " | " +track["artist"]),file=logfile)
	logfile.events.append(e)
	return logfile



class LastFM:

	def __init__(self,user=None,api_key="", disable_cache=False):
		self.apiKey = api_key
		self.user = user
		self.cache = {}
		self.disable_cache = disable_cache
	
	def apiCall(self,url, cache=True):
		fullurl = "http://ws.audioscrobbler.com/2.0/?method=" + url.replace(" ","%20") + "&api_key=" + self.apiKey + "&format=json"
		print fullurl
		try:
			if cache and not self.disable_cache:
				if fullurl in self.cache:
					data = copy.deepcopy(self.cache[fullurl])
				else:
					response = urllib2.urlopen(fullurl)
					data = json.load(response)
					self.cache[fullurl] = data
			else:
				response = urllib2.urlopen(fullurl)
				data = json.load(response)
			return data
		except exceptions.Exception as e:
			print str(e) + ": \n" + response.read()

	def getTrackInfo(self, track, artist=None):
		try:
			if artist == None:
				artist = track["artist"]["#text"]
				trackname = track["name"]
			else:
				trackname = track
			url = "track.getInfo&artist=%s&track=%s"%(artist,trackname)
			data = self.apiCall(url)
			trackData = data["track"]
			if not isinstance(trackData["duration"], float):
				trackData["duration"] = float(trackData["duration"])/1000.0 #Convert to seconds for convenience
		except exceptions.Exception as e:
			print track
			print e
		return trackData
		
	
	def cleanupTrack(self,track):
		info = self.getTrackInfo(track)
		track["duration"] = info["duration"]
		track["artist"] = info["artist"]["name"]
		track["date"] = dt.utcfromtimestamp(float(track["date"]["uts"])).replace(tzinfo=tz.UTC)
		return track
	
	def getRecentTracks(self, start=None, end=None, perpage=100):
		url = "user.getrecenttracks&user=%s&limit=%d"%(self.user,perpage)
		if start != None:
			url += "&from=%d"%(int(time.mktime(start.timetuple())))
		if end != None:
			url += "&to=%d"%(int(time.mktime(end.timetuple())))
		url += "&page=%d"
		tracks = []
		data = self.apiCall(url%(1), cache=False)
		totalPages = int(data["recenttracks"]["@attr"]["totalPages"])
		tracks += map(self.cleanupTrack,data["recenttracks"]["track"])
		if totalPages > 1:
			for page in range(2,totalPages+1):
				try:
					data = self.apiCall(url%(page), cache=False)
					tracks += map(self.cleanupTrack,data["recenttracks"]["track"])
				except exceptions.Exception as e:
					logging.error("Problem fetching data for page: %d"%(page))
					logging.error(e)
		return tracks	
