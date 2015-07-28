import tweepy
import time
import os, sys

from common import datetime_from_utc_to_local
from common import getOrSetArchive
from common import expandUrl
from common import scheduleNextRun

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
globalPrefix = getConfigParameters('globalPrefix')


#gets tweets with since id larger (means tweet is newer) than the previous since id 
#updates since id with largest tweet sinceID
def getRequestUrls():

	sinceIDValue = ''
	sinceIDFilename = globalPrefix + 'sinceID.txt'
	try:
		print 'f:', sinceIDFilename

		sinceIDFile = open(sinceIDFilename, 'r')
		prevSinceIDFile = open(globalPrefix + 'prev_sinceID.txt', 'w')

		line = sinceIDFile.readline()

		if(len(line) > 1):
			sinceIDValue = long(line)
		else:
			sinceIDValue = long('0')

		prevSinceIDFile.write(str(sinceIDValue) + '\n')

		sinceIDFile.close()
		prevSinceIDFile.close()
	except:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		print(fname, exc_tb.tb_lineno, sys.exc_info() )
		sinceIDValue = long('0')


	#get spam filter coeff.
	spamFilterCoeff = getConfigParameters('spamFilterCoeff')
	print 'spamFilterCoeff', spamFilterCoeff

	requestsRemaining = 0
	try:
		requestsRemaining = api.rate_limit_status()['resources']['search']['/search/tweets']['remaining']
	except:
		requestsRemaining = 0
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		print(fname, exc_tb.tb_lineno, sys.exc_info() )

		errorMessage = (fname, exc_tb.tb_lineno, sys.exc_info() )
		sendErrorEmail( str(errorMessage) )


	#requestsRemaining = 10
	print "Before Request remaining: ", requestsRemaining


	if( requestsRemaining > 0 ):
		#<user, expandedUrlsArray>
		twitterUsersDict = {}


		#assume initially tweet is present
		isTweetPresentFlag = True
		while( isTweetPresentFlag ):
			
			#if tweet is present this will change the False to True, else it will remain False and Stop the loop
			isTweetPresentFlag = False
			print "current sinceIDValue: ", sinceIDValue
			try:
				for tweet in tweepy.Cursor(api.search, q="%23icanhazmemento", since_id=sinceIDValue).items(30):
					print
					isTweetPresentFlag = True

					# From 2015-07-12 18:45:11
					# To   Sun, 12 Jul 2015 14:45:11 GMT
					localTweetDatetime = datetime_from_utc_to_local(tweet.created_at)
					#localTweetDatetime = tweet.created_at
					localTweetDatetime = localTweetDatetime.strftime('%a, %d %b %Y %H:%M:%S')
					localTweetDatetime = str(localTweetDatetime) + ' GMT'


					#update since_id
					if( tweet.id > sinceIDValue ):
						sinceIDValue = tweet.id

					#print localTweetDatetime, ",tweet_id:", tweet.id, ",", tweet.user.screen_name, " - ", tweet.text

					#get urls from tweet - start
					#since even though access to none short url, still meant that
					#url has to be chased down until the final value, no need to access none
					#short url
					shortTwitterUrls = []
					if( tweet.text.find('#icanhazmemento') != -1 ):
						for shortURL in tweet.entities['urls']:
							#print 'n: ', shortURL['expanded_url']
							shortTwitterUrls.append(shortURL['url'])
					#get urls from tweet - end


					#if this tweet is in response to a parent tweet with link(s) - start
					if( tweet.in_reply_to_status_id is not None and len(shortTwitterUrls) == 0):
						print 'checking parent:', tweet.in_reply_to_status_id

						parentTweet = api.get_status(tweet.in_reply_to_status_id)
						for shortURL in parentTweet.entities['urls']:
							shortTwitterUrls.append(shortURL['url'])
					#if this tweet is in response to a parent tweet with link(s) - end

					if(len(shortTwitterUrls) != 0):
						for url in shortTwitterUrls:
							potentialExpandedUrl = expandUrl(url)

							if( len(potentialExpandedUrl) > 0 ):

								#url normalization - start
								if( potentialExpandedUrl[-1] == '/' ):
									potentialExpandedUrl = potentialExpandedUrl[:-1]
								#url normalization - end

								#create new entry for user since user is not in dictionary
								print '...potentialExpandedUrl:', potentialExpandedUrl
								potentialExpandedUrl = potentialExpandedUrl.strip()
								if( tweet.user.screen_name in twitterUsersDict):
									#twitterUsersDict[tweet.user.screen_name].append(potentialExpandedUrl)
									
									#spam filter measure - start
									if( len(twitterUsersDict[tweet.user.screen_name]) < spamFilterCoeff ):

										twitterUsersDict[tweet.user.screen_name]['potentialExpandedUrlsArray'].append(potentialExpandedUrl)
									#spam filter measure - end

								else:
									#twitterUsersDict[tweet.user.screen_name] = [potentialExpandedUrl]

									twitterUsersDict[tweet.user.screen_name] = {}

									twitterUsersDict[tweet.user.screen_name]['potentialExpandedUrlsArray'] = [potentialExpandedUrl]
									twitterUsersDict[tweet.user.screen_name]['create_datetime'] = localTweetDatetime
									twitterUsersDict[tweet.user.screen_name]['tweet_id'] = tweet.id 
			except:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
				print(fname, exc_tb.tb_lineno, sys.exc_info() )

				errorMessage = (fname, exc_tb.tb_lineno, sys.exc_info() )
				sendErrorEmail( str(errorMessage) )
			
			if( isTweetPresentFlag ):
				print '...sleeping for 15 seconds'
				time.sleep(15)
	try:
		#MOD
		sinceIDFile = open(sinceIDFilename, 'w')
		
		#print 'DEBUG CAUTION, sinceIDValue SET'
		#print
		#sinceIDValue = 624360098433994752

		sinceIDFile.write(str(sinceIDValue) + '\n')
		sinceIDFile.close()
		
	except:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		print(fname, exc_tb.tb_lineno, sys.exc_info() )

	return twitterUsersDict

def processNewURLs(twitterUsersDict):

	if( len(twitterUsersDict) == 0 ):
		return

	for user, userDataDict in twitterUsersDict.items():
		print 'for:', user
		for url in userDataDict['potentialExpandedUrlsArray']:
			getOrSetArchive(user, userDataDict['tweet_id'], url, userDataDict['create_datetime'])
		print

def genericBadMessage(url, screenName, tweet_id):

	url = url.strip()
	screenName = screenName.strip()
	

	if( len(url) == 0 or len(screenName) == 0 or tweet_id == 0 ):
		return

	#untested block - start

	pageTitle = getPageTitle(url)
	#50: 140 - remaining text
	if( len(pageTitle) > 50 ):
		pageTitle = pageTitle[0:46]
		pageTitle = pageTitle + '...'

	notificationMessage = '@'+ screenName + ', Error processing page (' + url + ': '+ pageTitle +')'
	
	print '\tsending message:', notificationMessage
	
	updateStatus(statusUpdateString = notificationMessage, tweet_id = tweet_id, dotFlag = '') 
	#untested block - end

def entryPoint():

	twitterUsersDict = getRequestUrls()
	processNewURLs(twitterUsersDict)

entryPoint()
