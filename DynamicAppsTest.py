#!/usr/bin/env python3

from PIL import Image
from datetime import datetime
from os.path import exists
from time import sleep
from io import BytesIO
import sys
import cv2
import numpy as np
import pytesseract
import os
import urllib.request
import subprocess
import json
import re
import glob
import imagehash
import pathlib
import csv

curdir = pathlib.Path(__file__)                         # Gets the current directory of this script
parentdir = curdir.parent                               # Gets the parent directory of "curdir"
parentdir2 = parentdir.parent                           # Gets the parent directory of "parentdir"
workingdir = str(parentdir2.parent) + '/'                             # Gets the parent directory of "parentdir2" so we have the main directory for automation
#workingdir = parentdir.parent.joinpath('/')
stbcontrolfile = '/home/rtglass/stbController/config/stbData.json'	# Define the STB controller data file for use later

#workingdir = '/var/www/html/glassAutomation/'	# Define the working directory for later use

filedir = f"{workingdir}files/"
#filedir = workingdir.joinpath('files')

tempdir = f"{filedir}tmp/"
#tempdir = filedir.joinpath('tmp')

refimgdir = f"{filedir}matchTemplates/"	# The app reference image directory
#refimgdir = filedir.joinpath('matchTemplates')

appcropfile = f"{filedir}testFiles/appBarCropValues.json"
#appcropfile = filedir.joinpath('testFiles', 'appBarCropValues.json')

sshotdir = workingdir + 'files/tmp/'
#sshotdir = filedir.joinpath('tmp')

resultsdir = workingdir + 'files/results/'
#resultdir = filedir.joinpath('results')

apploaddir = f"{filedir}testFiles/tmpScreenshots/"
#apploaddir = filedir.joinpath('testFiles', 'tmpScreenshots')

# Load the STB controller JSON data
controlf = open(stbcontrolfile)
stbData = json.load(controlf)

# Load the app crop paramters data
appcropf = open(appcropfile)
appcropdata = json.load(appcropf)

#appreffile = workingdir + 'appRefImages.json';	# App reference image filenames are stored in this JSON file
appreffile = f"{workingdir}files/testFiles/appReferences.json";	# App reference details are stored in this JSON file
appf = open(appreffile)	# Read in the list of app reference image filenames
appRefs = json.load(appf)	# Create the dictionary for apps and their various references

# Load the panel camera info JSON data
camfile = workingdir + 'files/panelCameraInfo.json'
pcf = open(camfile)
camData = json.load(pcf)

# From line 34 - JSON data
#resultsf = open(resultsfile)
#resultsStates = json.load(resultsf)


# Load the keys from the refLocations dictionary in to the string list for user help info
applist = ''
for key in appRefs.keys():
	applist = applist + key + "\n"

# Parse the input arguments to check an app and STBs were chosen
if len(sys.argv) < 3:
	print("Please provide an app selection and STBs. App options are:\n" + applist)
	exit()


# Check the chosen app exists as an option in the JSON file
appOpt = sys.argv[1]
if appOpt not in appRefs:
	print('Error: ' + appOpt + " is not a valid option. Please select from the following\n" + applist)
	exit()

new_appOpt = re.sub(r' ', '_', appOpt)	# Replace spaces with underscores in the appOpt string

# Split the list of provided STBs by the comma character
stbOpt = sys.argv[2]
stbs = stbOpt.split(',')

refFile = f"{workingdir}files/appTestConfigFiles/{new_appOpt}.json"
with open(refFile, 'r') as f:
	appSRefs = json.load(f)

# Create the timestamp for "now" and make the results directory for this test run
now = datetime.now()
timestamp = now.strftime("%Y-%m-%d_%H:%M:%S")
resdir = f"{resultsdir}{new_appOpt}_{timestamp}"
if not os.path.exists(resdir):
	os.mkdir(resdir)

def getMenuImageAndOCR(stbname,stbip):
	screenshotfile = workingdir + 'captureVnc_' + stbname + '.png'	# Define the screenshot filename
	cropfile = workingdir + 'highlightedApp_' + stbname + '.png'	# Define the cropped image filename
	urllib.request.urlretrieve('http://' + stbip + ':5800/screenshot.png', screenshotfile)
	sleep(2)
	img = cv2.imread(screenshotfile)

	cropImg = img[590:880, 80:380]	# Crop the image to the area where the start of the Apps bar is

	res = pytesseract.image_to_string(cropImg, lang='eng')	# Process the image through pytesseract to get the text
	return res	# Return the extracted text

#------LOOK HERE----------object oriented python
class device():
	def __init__(self, stb):
		self.ip = stbData[stb]['VNCIP']
		self.name = stb

def test(stbname):
	dev = device(stbname)
	#print(f"{dev.name} - {dev.ip}")
	#os._exit(0)

	#stbip = stbData[stbname]['VNCIP']	# Get the STB IP from the STB controller data file
	dev.screenshotfile = tempdir + 'captureVnc_' + stbname + '.png'	# Define the screenshot filename
	dev.cropfile = tempdir + 'highlightedApp_' + stbname + '.png'	# Define the cropped image filename
	cropimagedir = workingdir + 'cropImages/'

	# We need to create the STB results directory :)
	dev.resdir = resdir + '/' + stbname + '/'
	if not os.path.exists(dev.resdir):
		os.mkdir(dev.resdir)

	dev.resfile = dev.resdir + 'Results.json'

	results = {}

	# First do some checks to see if the panel is awake and responding
	# Ping check
	awake = 0

#	for key in resultsStates:
#		state = resultsStates[key]
#		results = confirmPrimeLoad(stbname)

	for i in range(3):
		#pingres = os.system("ping -c 1 " + stbip)
		pingres = subprocess.run(['ping','-c','1',dev.ip], stdout=subprocess.DEVNULL)
		#print(pingres)
		if pingres.returncode == 0:
			awake = 1
			break
		else:
			print(stbname + ' did not respond to ping. Attempting to wake it with WOL')
			#os.system("perl /home/rtglass/stbController/scripts/stbControl.pl control wakeonlan " + stbname)
			subprocess.run(['perl', '/home/rtglass/stbController/scripts/stbControl.pl', 'control', 'wakeonlan', stbname], stdout=subprocess.DEVNULL)
			sleep(15)

	# If awake is still 0, we haven't received a ping response from the panel after 3 tries so assume it is not working
	if awake == 0:
		results['1 Panel Ready'] = "Fail: Unable to wake {stbname} for testing"
		print("Error: We could not wake " + stbname + " for testing. Aborting this STB")
		saveSTBResult(results,dev.resfile)
		exit()
	else:
		results['1 Panel Ready'] = "Pass"
		saveSTBResult(results,dev.resfile)


	subprocess.run(['perl', '/home/rtglass/stbController/scripts/stbControl.pl', 'control', 'tv guide', stbname], stdout=subprocess.DEVNULL)
	sleep(3)

	# Now we make 3 attempts to get to the Apps and Inputs list
	inapps = 0
	for i in range(10):
		# Run the control sequence to get to the app list
		subprocess.run(['perl', '/home/rtglass/stbController/scripts/stbControl.pl', 'control', 'cursor down', stbname], stdout=subprocess.DEVNULL)
		sleep(3)	# Wait 10 seconds

		# Check we are at the right place in the UI (Apps & Inputs) using OCR
		text = getMenuImageAndOCR(stbname,dev.ip)
		text = text.replace("\n"," ")
		res = re.match("apps", text, re.IGNORECASE)
		if res is not None:
			inapps = 1
			break

	if inapps == 0:
		results['2 Find Apps Rail'] = "Fail: Unable to get to Apps and Inputs bar after 10tries"
		print("Error: " + stbname + " did not get to the Apps and Inputs bar after 10 tries, aborting this STB")
		saveSTBResult(results,dev.resfile)
		exit()
	else:
		results['2 Find Apps Rail'] = "Pass"
		saveSTBResult(results,dev.resfile)

	# Preflight checks done. If we get this far, we can start testing!
	previmageflag = 0
	previmage = ''
	lasthdmi = ''
	found = 0	# This will be changed to '1' if the chosen app is found
	count = 1	# This counter increases by 1 each time we go right in the list of apps
	cropcnt = 1

	# Loop until we find the app in the Apps bar or we have gone right 35 times
	while not found:
		#print("App loop:")
		urllib.request.urlretrieve('http://' + dev.ip + ':5800/screenshot.png', dev.screenshotfile)
		sleep(2)

		#img = cv2.imread(screenshotfile,0)
		img = cv2.imread(dev.screenshotfile)
		imgcopy = img.copy()	# Create a copy of the image for use with description cropping

		# Store the crop dimensions in slice objects so they can be adjusted during the loop
		#y = slice(590,880)
		#x = slice(80,380)
		#print(str(appcropdata[cropcnt]['x']) + ' <- x value')
		if str(cropcnt) not in appcropdata:
			results = "Fail: cannot find app within the app bar"
			print("Looks like we reached the end of the apps bar without finding the app. Test failed!")
			#exit()
			break

		x = slice(appcropdata[str(cropcnt)]['x'],appcropdata[str(cropcnt)]['w'])
		y = slice(appcropdata[str(cropcnt)]['y'],appcropdata[str(cropcnt)]['h'])
		#cropImg = img[590:880, 80:380]	# Crop the main image around the first select app area
		#print("Cropping image with set " + str(cropcnt))
		cropImg = img[y, x]	# Crop the main image around the first select app area
		cropsave = dev.cropfile.replace(".png", "_" + str(cropcnt) + ".png")
		cv2.imwrite(cropsave,cropImg)
		cropsave2 = cropimagedir + "app" + str(count) + "_Image.png"
		cv2.imwrite(cropsave2,cropImg)

		# Crop the copy image "imgcopy" to the area where the heading of the selection description is
		descy = 210
		desch = 100
		descx = 75
		descw = 800

		descImg = imgcopy[descy:descy+desch, descx:descx+descw]
		descImg = (255-descImg)	# Invert the image so that the white text becomes black. This makes OCR more reliable
		descsave = cropimagedir + "app" + str(count) + "_Description.png"
		#descsave = cropfile.replace(".png", "_Description_" + str(cropcnt) + ".png")
		cv2.imwrite(descsave,descImg)


		thishdmi = ''

		desctext = pytesseract.image_to_string(descImg, lang='eng')  # Process the image through pytesseract to get the text
		if desctext is not None:
			desctext = desctext.replace("\n"," ")
			#print(desctext)
			res = re.search(r"HDMI\s*(\d+)", desctext, re.IGNORECASE)
			if res is not None:
				thishdmi = res.group(1)
				#print("Saw HDMI " + lasthdmi)

		fullname = refimgdir + appRefs[appOpt]["ImageRef"]	# Make the full file path for the reference image we need
		#template = cv2.imread(fullname,0)	# Load the reference image file in to "template"
		template = cv2.imread(fullname)	# Load the reference image file in to "template"
		#w, h = template.shape[::-1]		# Get the width and height of the reference image
		h = template.shape[0]
		w = template.shape[1]

		res = cv2.matchTemplate(cropImg,template,cv2.TM_CCOEFF_NORMED)	# Run the cropped image and the template through the matching process
		min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
		#top_left = max_loc
		#bottom_right = (top_left[0] + w, top_left[1] + h)

		if max_val > 0.8:	# The threshold value for a valid match is 0.8
			found = 1
		else:
			# If the image doesn't match, check the app description title using ocr
			matchref = appRefs[appOpt]["Description"]
			desctext = re.sub(r'\s+', '', desctext)	# Remove all whitespace from the description text ready for the regex
			descres = re.match(matchref, desctext, re.IGNORECASE)
			if descres is not None:
				found = 1
				continue

			subprocess.run(['perl', '/home/rtglass/stbController/scripts/stbControl.pl', 'control', "cursor right", stbname], stdout=subprocess.DEVNULL)
			sleep(5)

		count = count + 1	# Increase the counter by 1

		# If the counter is greater than 35, give up trying
		if count > 35:
			print(stbname + ' unable to locate app ' + appOpt + ' after 35 tries. Aborting')
			#exit()
			break

	# End of while loop for finding the app in the bar

	if found == 0:
		print(f"ERROR: {stbname} failed to find app in apps rail")
		results['3 Find App In Apps Rail'] = "Fail"
		saveSTBResult(results,dev.resfile)
		exit()
	else:
		results['3 Find App In Apps Rail'] = "Pass"
		saveSTBResult(results,dev.resfile)

	# If we get this far, the app has been located in the bar and we can hit select to open it
	print(stbname + ' found ' + appOpt)

	subprocess.run(['perl', '/home/rtglass/stbController/scripts/stbControl.pl', 'control', "select", stbname], stdout=subprocess.DEVNULL)
	sleep(15)

	#appResult = confirmAppLoad(stbname)
	appResult = confirmAppLoad(dev)
	if re.search('Fail', appResult):
		print(f"ERROR: {stbname} failed to load the app")
		results["4 Open App And Confirm Loaded"] = "Fail"
		saveSTBResult(results,dev.resfile)
		exit()
	else:
		results["4 Open App And Confirm Loaded"] = "Pass"
		saveSTBResult(results,dev.resfile)

	camip = camData[stbname]
	stream = 'rtsp://admin:Chilworthevo1@' + camip + ':554/h265Preview_01_main'
	moving = verifyStreaming(stbname,stream)
	if moving is None:
		print('Fail: No content playing')
		results["5 Confirm Content Streaming"] = "Fail"
		saveSTBResult(results,dev.resfile)
		exit()
	else:
		print(appOpt + 'content is playing on ' + stbname)
		results["5 Confirm Content Streaming"] = "Pass"
		saveSTBResult(results,dev.resfile)

	print(f"{stbname} test finished, attempting to reset panel back to home screen")
	subprocess.run(['perl', '/home/rtglass/stbController/scripts/stbControl.pl', 'control', "backup,t3,backup,t3,backup,t3,backup,t2,tv guide", stbname], stdout=subprocess.DEVNULL)

#def findAppInBar():

def saveSTBResult(results,stbresfile):
	with open(stbresfile, 'w') as outfile:
		json.dump(results, outfile, indent=4)


def confirmAppLoad(dev):
	tempfdir = f"{tempdir}{dev.name}/"	# The temp folder to store test files related to this STB
	if not os.path.exists(tempfdir):
		os.mkdir(tempfdir)

	#stbresdir = f"{resdir}/{stbname}"
	#stbip = stbData[stbname]['VNCIP']
	#if not os.path.exists(stbresdir):
	#	os.mkdir(stbresdir)

	screenshotLoad = apploaddir + dev.name + '_' + new_appOpt + 'Load.png'
	screenshotSuccess = apploaddir + dev.name + '_' + new_appOpt + 'Success.png'
	screenshotFail = apploaddir + dev.name + '_' + new_appOpt + 'Fail.png'
	loadSuccess = 0
	loadFail = 0
	cnt = 0
	finalResult = "Fail"
	foundamatch = 0
	while not loadSuccess:
		cnt = cnt + 1
		#print('Count = ' + str(cnt))
		if cnt > 10:
			break
		urllib.request.urlretrieve('http://' + dev.ip + ':5800/screenshot.png', screenshotLoad)
		sleep(2)

		appLoadScreen = cv2.imread(screenshotLoad)
		appLoadScreenCopy = appLoadScreen.copy()

		thisApp = appRefs[appOpt]

		#failImgRef = thisApp['LoadFailRef']
		#failTemplate = cv2.imread('/home/rtglass/glassPanelDev/' + failImgRef)
		#cropRefFaily = thisApp['LoadFailCoOrdinates'][0]
		#cropRefFailh = thisApp['LoadFailCoOrdinates'][1]
		#cropRefFailx = thisApp['LoadFailCoOrdinates'][2]
		#cropRefFailw = thisApp['LoadFailCoOrdinates'][3]
		#cropImg = appLoadScreenCopy[cropRefFaily:cropRefFailh,cropRefFailx:cropRefFailw]
		#invCropImg = cropImg.copy()
		#invCropImg = (255-invCropImg)
		#cv2.imwrite('/home/rtglass/glassPanelDev/glassLoad/practiceCrop.png', invCropImg)

		#textOutput = pytesseract.image_to_string(invCropImg)
		#print("'" + textOutput + "'")

		#if re.search('Sign in', textOutput):
		#	loadSuccess = 0
		#	print(f"{stbname} - {appOpt} requires Sign in, aborting test")
		#	break
		#elif re.search('watching', textOutput):
		#	subprocess.run(['perl', '/home/rtglass/stbController/scripts/stbControl.pl', 'control', "select", stbname], stdout=subprocess.DEVNULL)

		#	urllib.request.urlretrieve('http://' + stbip + ':5800/screenshot.png', screenshotLoad)
		#	sleep(2)
		#	appLoadScreen = cv2.imread(screenshotLoad)
		#	appLoadScreenCopy = appLoadScreen.copy()

		#	continue
		#else:
		#	print(appOpt + ' next stage continue.. ')

		#sleep(10)

		matched = 0
		for ref in appSRefs:
			fp = f"{filedir}testFiles/templates/apps/{new_appOpt}/{appSRefs[ref]['filePath']}"
			sn = appSRefs[ref]['screenName']
			rc = appSRefs[ref]['responseCommand']
			rw = appSRefs[ref]['responseWait']
			ts = appSRefs[ref]['textOnScreen']

			# Take mini screenshot of THIS Cords
			scy = appSRefs[ref]['onScreenCords'][0]
			sch = appSRefs[ref]['onScreenCords'][1]
			scx = appSRefs[ref]['onScreenCords'][2]
			scw = appSRefs[ref]['onScreenCords'][3]

			screenCords = appLoadScreenCopy[scy:sch,scx:scw]
			# Save the cropped screen section as per the template coOrds
			tpfilename = re.sub(r' ', '_', sn)	# Replace spaces with underscores in the sn string
			cv2.imwrite(f"{tempfdir}{tpfilename}.png",screenCords)

			# Make a copy of the cropped image for OCR purposes
			screenCordsImg = screenCords.copy()	# Copy the image
			screenCordsImg = (255-screenCordsImg)	# Invert the colours
			cv2.imwrite(f"{tempfdir}cropCords.png", screenCordsImg)	# Save the image
			sleep(2)
			sc = screenCordsImg
			#print(ref + ' ' + fp)

			# Do OCR text output for this mini screenshot of Cords given in JSON file
			#textDesc = pytesseract.image_to_string(screenCordsImg)
			#print(f'OCR output for screen name - {sn}: found.. {textDesc}')

			#### Template matching ####
			template = cv2.imread(fp)

			# Check that the cropped image is larger in both width and height than the template to be matched
			croph = screenCords.shape[0]	# Cropped image height
			cropw = screenCords.shape[1]	# Cropped image width
			temph = template.shape[0]    # Template image height
			tempw = template.shape[1]    # Template image width

			if temph > croph:
				print(f"ERROR: Template {tpfilename} height ({temph}) is bigger than the cropped image height ({croph})")
				continue
			elif tempw > cropw:
				print(f"ERROR: Template {tpfilename} width ({tempw}) is bigger than the cropped image width ({cropw})")
				continue

			#result = cv2.matchTemplate(appLoadScreenCopy, template, cv2.TM_CCOEFF_NORMED)
			result = cv2.matchTemplate(screenCords, template, cv2.TM_CCOEFF_NORMED)
			min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

			top_left = max_loc
			bottom_right = (top_left[0] + template.shape[1],
			top_left[1] + template.shape[0])
			sleep(4)
			#print(max_val)

			if max_val < 0.7:
				#if ts and any(word.lower() in textDesc.lower() for word in ts):
				#	print(f'Match found for screen {sn}')
				#	#it not run subprocess after it found the word
				#	print(f'Template did not match but OCR did!')
				#	subprocess.run(['perl', '/home/rtglass/stbController/scripts/stbControl.pl', 'control', rc, stbname], stdout=subprocess.DEVNULL)
				#	sleep(rw)
				#else:
				#	print(f'No template or text match found')
				#	continue
				print(f"No match found for template {sn}")

			if max_val >= 0.7:
				print(f"Match found for template {sn}!")
				matched = 1
				#cv2.rectangle(screenCords, top_left, bottom_right, (0, 0, 255), 2)
				#cv2.imwrite(f"{filedir}{tpfilename}MatchHighlight.png", screenCords)
				resultMatch = (sn + ' Found')
				#print(resultMatch)
				subprocess.run(['perl', '/home/rtglass/stbController/scripts/stbControl.pl', 'control', rc, dev.name], stdout=subprocess.DEVNULL)
				#print(f"Sleeping {rw}")
				sleep(int(rw))

				# Get a new screenshot as we have moved in the UI!
				urllib.request.urlretrieve('http://' + dev.ip + ':5800/screenshot.png', screenshotLoad)
				sleep(5)
				appLoadScreen = cv2.imread(screenshotLoad)
				appLoadScreenCopy = appLoadScreen.copy()


				# check if anyword in text match with textOnScreen
#				textOnScreen = appRefs[ref]['textOnScreen']
#				if isinstance(ts, list):
#					for word in ts:
#						if word.lower() in textDesc.lower():
#							print(f'{word} found in OCR output for screen {sn}')
#							subprocess.run(['perl', '/home/rtglass/stbController/scripts/stbControl.pl', 'control', rc, stbname], stdout=subprocess.DEVNULL)
#							sleep(rw)
#break
#				for screen in appSRefs.values():
#					resCom = '"' + screen['responseCommand'] +  '"'
#					resCom = screen['responseCommand']

				if appSRefs[ref].get('loaded') is not None:
					if appSRefs[ref]['loaded'] == 'yes':
						print(f"{dev.name} - {appOpt} content should be playing..")
						loadSuccess = 1
						break

				# The key "restartLoop" indicates that we need to restart the template loop if we match this template
				if appSRefs[ref].get('restartLoop') is not None:
					print(f"{dev.name} Loop restart detected")
					break

		if not matched:
			print(f"{dev.name} No templates matched. Sending backup command")
			subprocess.run(['perl', '/home/rtglass/stbController/scripts/stbControl.pl', 'control', 'backup,t4,cursor right', dev.name], stdout=subprocess.DEVNULL)
			sleep(5)


	if not loadSuccess:
		print(f"{dev.name} - {appOpt} failed to load")
	else:
		print(f"{dev.name} - {appOpt} loaded")
		finalResult  = "Pass"
	return finalResult


def verifyStreaming(stbname,stream):
	moving = 0
	for i in range(2):
		for i in range(1,3):
			cap = cv2.VideoCapture(stream)
			if (cap.isOpened() == False):
				print(f"Failed to open stream to {stream}")
				continue

			ret, frame = cap.read()

			#leftSection = frame[280:760, 250:700]
			leftSection = frame[480:960, 700:1100]
			cv2.imwrite(f"{sshotdir}/{stbname}_streamCapture{i}.jpg",leftSection)
			cap.release()
			cv2.destroyAllWindows()
			sleep(10)

		hash1 = imagehash.average_hash(Image.open(f"{sshotdir}/{stbname}_streamCapture1.jpg"))
		hash2 = imagehash.average_hash(Image.open(f"{sshotdir}/{stbname}_streamCapture2.jpg"))
		diff = hash1 - hash2

		#print(diff)
		if diff >= 15:
			moving = 1
			break

	return moving


def createSummaryReport():
	outrepfile = f"{appOpt}/TestSummary.csv"
	repstring = f"Find and Play" + {appOpt} + "_Test\n{timestamp}\n\n"
#	repstring += "STB"
	repstring += "STB, Find App in App Bar, Confirm Prime Load, Verify Streaming, Overall Result\n"

	for key in successRefData:
		refPoint = successRefData[key]
		repstring += f",{refPoint}"
		repstring += ",Overall Result\n"
		# We should now have a line in the CSV file that looks like STB,>

		# Now work through each of the individual STB results files and >
	stbrepdirs = os.listdir(resdir) # Get the directory list of STBs
	r = re.compile(r'(\d+)')        # Create a regex object which will pick >
	stbrepdirs.sort(key=lambda x:int(r.search(x).group(1))) # Sort the direc>

	for d in stbrepdirs:
		fulldir = f"{workingdir}/{d}"
		resfile = f"{resultsdir}/results.json"
		rf = open(resfile,"r")
		resdata = json.load(rf)
		nicename = d.replace("STB","Glass ")
		repstring += f"{nicename},"

		fullres = 'Pass'

		for stage in ["Find App", "Confirm Prime Load", "Verify Streaming"]:
			result = resdata.get(stage, "Fail")
			repstring += f"{result},"
			if result == "Fail":
				fullres = 'Fail'


#		for chankey in resdata:
#			cres = resdata[chankey]
#			if cres == "Fail":
#				fullres = 'Fail'
#				repstring += f"{cres},"

		repstring += f"{fullres}\n"
	repf = open(outrepfile, "w")    # Open the output file ready for writing
	repf.write(repstring)
	repf.close()

runningSTBs = {}        # This will contain entries for all STBs that are currently under test
processes = []



for b in stbs:
#	newpid = os.fork()
#	if newpid == 0:
#		tasks.append(newpid)
#	else:
		test(b)
#		os._exit(0)

#for i, child in enumerate(tasks):
#	os.waitpid(child,0)

#os.wait();



