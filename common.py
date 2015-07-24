import tweepy
import time
import httplib
import urllib
import urllib2
import os, sys
import commands

from datetime import datetime
from datetime import timedelta
from urlparse import urlparse
from bs4 import BeautifulSoup
from getConfig import getConfigParameters
from sendEmail import sendErrorEmail

# Consumer keys and access tokens, used for OAuth
consumer_key = getConfigParameters('twitterConsumerKey')
consumer_secret = getConfigParameters('twitterConsumerSecret')
access_token = getConfigParameters('twitterAccessToken')
access_token_secret = getConfigParameters('twitterAccessTokenSecret')

# OAuth process, using the keys and tokens
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)

# Creation of the actual interface, using authentication
api = tweepy.API(auth)

MEMENTO_AGGREGATOR_TIMEGATE = getConfigParameters('MEMENTO_AGGREGATOR_TIMEGATE')
IA_SAVEWEBPAGE_URI = getConfigParameters('IA_SAVEWEBPAGE_URI')
AIS_SAVEWEBPAGE_URI = getConfigParameters('AIS_SAVEWEBPAGE_URI')


def expandUrl(url):
	if(len(url) > 0):

		url = url.strip()
		#http://stackoverflow.com/questions/17910493/complete-urls-in-tweepy-when-expanded-url-is-not-enough-integration-with-urllib
		
		try:
			url = urlparse(url)	# split URL into components

			conn = httplib.HTTPConnection(url.hostname, url.port)
			conn.request('HEAD', url.path)			# just look at the headers

			rsp = conn.getresponse()

			if rsp.status in (301,401):			   # resource moved (permanent|temporary)
				return rsp.getheader('location')
			else:
				return url
			conn.close()

		except:
			return ''

	else:
		return ''

#http://stackoverflow.com/questions/4770297/python-convert-utc-datetime-string-to-local-datetime
def datetime_from_utc_to_local(utc_datetime):
	now_timestamp = time.time()
	offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
	return utc_datetime + offset

def getPageTitle(url):

	titleOfPage = ''
	if( len(url) > 0 ):

		try:
			req = urllib2.Request(url)
			req.add_header('User-agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.101 Safari/537.36')

			response = urllib2.urlopen(req)
			soup = BeautifulSoup(response)

			titleOfPage = soup.title.string

			#this line added because some titles contain "funny" characters that generate encoding errors
			titleOfPage = titleOfPage.encode('ascii', 'ignore')
		except:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			print(fname, exc_tb.tb_lineno, sys.exc_info() )
			titleOfPage = url + '...'

		titleOfPage = titleOfPage.strip()

	return titleOfPage

def updateStatus(statusUpdateString, tweet_id = 0, dotFlag = ''):

	if(len(statusUpdateString) > 0):
		if( tweet_id != 0 ):

			tweet_id = int(tweet_id)
			#MOD
			api.update_status(status=dotFlag + statusUpdateString, in_reply_to_status_id=tweet_id)
		else:
			api.update_status(statusUpdateString)

def getOrSetArchive(screenName, tweet_id, url, acceptDatetime):

	try:
		screenName = screenName.strip()
		url = url.strip()
		acceptDatetime = acceptDatetime.strip()

		if( len(screenName) == 0 or tweet_id == 0 or len(url) == 0 or len(acceptDatetime) == 0 ):
			print '\tBad parameter(s)'
			return

		msg = ''

		print
		print '\tURI found in tweet: ' + url
		print '\tQuerying aggregator at: ' + MEMENTO_AGGREGATOR_TIMEGATE + url
		print '\tAccept-Datetime: ' + acceptDatetime
		acceptDatetimeObj = datetime.strptime(acceptDatetime, '%a, %d %b %Y %H:%M:%S GMT')

		requestGetFromArchive = urllib2.Request(MEMENTO_AGGREGATOR_TIMEGATE + url, headers={'Accept-Datetime' : acceptDatetime})
		
		try:
			responseGetFromArchive = urllib2.urlopen(requestGetFromArchive)
		except urllib2.HTTPError, e:
			print '\tInside Exception: requestGetFromArchive'

			if e.code == 404:
				print '\tWe got a 404, submitting to the archive.'
				print '\tSending to: ' + IA_SAVEWEBPAGE_URI + url
				
				#send to webarchive.org - start
				goodResponseFlagArchive0 = True
				requestSendToArchive = urllib2.Request(IA_SAVEWEBPAGE_URI + url)
				try:
					responseSendToArchive = urllib2.urlopen(requestSendToArchive)
				except:
					#genericBadMessage(url, screenName, tweet_id)
					goodResponseFlagArchive0 = False
					exc_type, exc_obj, exc_tb = sys.exc_info()
					fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
					print(fname, exc_tb.tb_lineno, sys.exc_info() )
				#send to webarchive.org - end

				#send to archive.is - start
				print '\tSending to: ' + AIS_SAVEWEBPAGE_URI + url
				goodResponseFlagArchive1 = True
				query_args = { 'url': url }
				encoded_args = urllib.urlencode(query_args)

				try:
					urllib2.urlopen(AIS_SAVEWEBPAGE_URI, encoded_args).read()
				except urllib2.HTTPError, e:
					goodResponseFlagArchive1 = False
					exc_type, exc_obj, exc_tb = sys.exc_info()
					fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
					print(fname, exc_tb.tb_lineno, sys.exc_info() )
				#send to archive.is - end

				if( goodResponseFlagArchive0 == False and goodResponseFlagArchive1 == False ):
					print '\tArchiving error'
					return
				
				#here means success saving to archive
				#send notarchiveURI = 'http://web.archive.org' + responseSendToArchive.info().getheader("Content-Location")ification tweet - start

				pageTitle = getPageTitle(url)
				#50: 140 - remaining text
				if( len(pageTitle) > 20 ):
					pageTitle = pageTitle[0:17]
					pageTitle = pageTitle + '...'

				formattedTweetDatetime = acceptDatetimeObj.strftime('%Y%m%d%H%M%S')
				archiveURI = 'http://timetravel.mementoweb.org/memento/' + formattedTweetDatetime + '/' + url
				notificationMessage = '@'+ screenName + ', Your newly archived page: ' + archiveURI + ' (' + pageTitle + '). See other versions: http://timetravel.mementoweb.org/list/'+ formattedTweetDatetime +'/' + url
				
				print '\tsending message:', notificationMessage
				updateStatus(statusUpdateString = notificationMessage, tweet_id = tweet_id, dotFlag = '')

				#send notification tweet - end
				return
			else:
				#genericBadMessage(url, screenName, tweet_id)
				exc_type, exc_obj, exc_tb = sys.exc_info()
				fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
				print(fname, exc_tb.tb_lineno, sys.exc_info() )
				return

		#here means success retrieving archived page
		#contents = responseGetFromArchive.read()

		# Rudimentary parsing rather than regex
		lines = responseGetFromArchive.info().getheader('Link').split('<')
		
		if( len(lines) == 0 ):
			#genericBadMessage(url, screenName, tweet_id)
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			print(fname, exc_tb.tb_lineno, sys.exc_info() )
			return

		mementoDatetimeDict = {}
		listOfDatetimes = [acceptDatetimeObj]

		for line in lines:
			if( line.find('memento"') != -1 ):
				uriMAndRest = line.split('>')
				
				uriM = uriMAndRest[0]
				datetimeStr = uriMAndRest[1]

				uriM = uriM.strip()

				datetimeStr = datetimeStr.strip()
				datetimeStr = datetimeStr.split('datetime=')
				datetimeStr = datetimeStr[1]
				datetimeStr = datetimeStr.replace('"', '')
				datetimeStr = datetimeStr.replace(',', '')
				datetimeStr = datetimeStr.strip()

				datetimeObj = datetime.strptime(datetimeStr, '%a %d %b %Y %H:%M:%S GMT')
				
				listOfDatetimes.append(datetimeObj)
				mementoDatetimeDict[datetimeObj] = uriM
		
		if( len(mementoDatetimeDict) == 0 ):
			#genericBadMessage(url, screenName, tweet_id)
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			print(fname, exc_tb.tb_lineno, sys.exc_info() )
			return

		#get urim closest to access datetime - start

		listOfDatetimes.sort()
		datePriorToAcceptDatetime = None
		for i in range(0, len(listOfDatetimes)):
			if( listOfDatetimes[i] == acceptDatetimeObj ):
				#this date is prior to acceptDatetime
				datePriorToAcceptDatetime = listOfDatetimes[i-1]

		if datePriorToAcceptDatetime is not None:
			print '\t', datePriorToAcceptDatetime, mementoDatetimeDict[datePriorToAcceptDatetime]
			
			#send notification tweet - start

			pageTitle = getPageTitle(url)
			#50: 140 - remaining text
			if( len(pageTitle) > 15 ):
				pageTitle = pageTitle[0:12]
				pageTitle = pageTitle + '...'

			strPriorDate = str(datePriorToAcceptDatetime).split(' ')[0]
			#notificationMessage = '@'+ screenName + ', Your archived page (' + strPriorDate + '): ' + mementoDatetimeDict[datePriorToAcceptDatetime] + ' (' + pageTitle + '). See other versions: ' + 'http://timetravel.mementoweb.org/list/19700101000000/' + url
			
			#promote timetravel - start
			formattedTweetDatetime = acceptDatetimeObj.strftime('%Y%m%d%H%M%S')
			archiveURI = 'http://timetravel.mementoweb.org/memento/' + formattedTweetDatetime + '/' + url
			notificationMessage = '@'+ screenName + ', Your archived page (' + strPriorDate + '): ' + archiveURI + ' (' + pageTitle + '). See other versions: ' + 'http://timetravel.mementoweb.org/list/' + formattedTweetDatetime + '/' + url
			#promote timetravel - send

			print '\tsending message:', notificationMessage
			updateStatus(statusUpdateString = notificationMessage, tweet_id = tweet_id, dotFlag = '')

			#send notification tweet - end

		#get urim closest to access datetime - end
	except:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]

		errorMessage = fname + ', ' + str(exc_tb.tb_lineno)  + ', ' + str(sys.exc_info())
		print '\tERROR:', errorMessage
		sendErrorEmail( str(errorMessage) )

#calls this program to run at a scheduled time
#commandToSchedule = '/usr/bin/python ' + os.path.realpath(__file__)
def scheduleNextRun(minutesPlusNow, commandToSchedule):

	commandToSchedule = commandToSchedule.strip()
	if( minutesPlusNow < 1 or len(commandToSchedule) == 0 ):
		print 'BAD PARAM(S)'
		return

	now = datetime.now()
	nextRunTime = str(now + timedelta(minutes = minutesPlusNow))
	nextRunTime = nextRunTime.split(' ')[1].split('.')[0].strip()
	nextRunTime = nextRunTime[:-3]
	
	sendEmailFlag = False
	messageToSend = ''

	try:
		co = 'echo "' + commandToSchedule + '" | at ' + nextRunTime
		print co
		commands.getoutput(co)
	except:
		sendEmailFlag = True
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		messageToSend = fname + '\n' + exc_tb.tb_lineno + '\n' + sys.exc_info()
		print(fname, exc_tb.tb_lineno, sys.exc_info() )

		errorMessage = (fname, exc_tb.tb_lineno, sys.exc_info() )
		sendErrorEmail( str(errorMessage) )