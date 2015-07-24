import json
import os, sys


configFileName = 'path to the config file/config'

def getConfigParameters(keyValue):

	returnValue = ''

	if( len(keyValue) > 0 ):
		try:
			configFile = open(configFileName, 'r')
			config = configFile.read()
			configFile.close()

			jsonFile = json.loads(config)
			returnValue = jsonFile[keyValue]

			if( type(jsonFile[keyValue]) == unicode ):
				returnValue = str(returnValue)


		except:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			print(fname, exc_tb.tb_lineno, sys.exc_info() )

	return returnValue