#!/usr/bin/python3

from time import sleep
import sys
import cv2
import numpy as np
import pytesseract
import os
from os.path import exists
import urllib.request
import subprocess
import json
import re
import pathlib

curdir = pathlib.Path.cwd() 	# Gets the current directory of this script
parentdir = curdir.parent	# Gets the parent directory of "curdir"
maindir = parentdir.parent	# Gets the parent directory of "parentdir" so we have the main directory for automation
filedir = str(maindir) + '/files'	# The main file directory
testfilesdir = filedir + '/testFiles'	# The main directory for files that are used for tests
sshotdir = testfilesdir + '/tmpScreenshots'	# The screenshot directory for tests
ccfile = testfilesdir + '/chanChangeChannels.json'	# The JSON file containing channels to use
templatesfile = testfilesdir + '/chanChangeTemplates.json'
stbcontrolfile = '/home/rtglass/stbController/config/stbData.json'      # Define the STB controller data file for use later
stbcontrolscript = '/home/rtglass/stbController/scripts/stbControl.pl'	# Define the STB controller script to control the panels

# Load the STB controller JSON data
controlf = open(stbcontrolfile)
stbData = json.load(controlf)	# Load the JSON in to the stbData dictionary object

# Load the channel JSON data
ccf = open(ccfile)
chanData = json.load(ccf)	# Load the JSON in to the chanData dictionary object

# Load the channel change templates JSON data
ccf = open(templatesfile)
templateData = json.load(ccf)	# Load the JSON in to the templateData dictionary object

# Check that STB arguments have been passed to the script
if len(sys.argv) < 2:
	print(f"No panels selected for test")
	exit()

stbstring = sys.argv[1]	# Read the STB list from input argument 1
stbs = stbstring.split(',')	# Split the list by the comma (,) to support multiple STBs

def chanChange(stb):
	stbip = stbData[stb]['VNCIP']       # Get the STB IP from the STB controller data file

	# First check the panel is awake. The wakeCheck function will try and wake it 3 times using WOL
	wakeres = wakeCheck(stb,stbip)
	if wakeres is None:
		print(f"{stb} would not respond to ping after 3 wake attempts, aborting")
		return

	# Now navigate to the TV Guide rail
	tgres = tvguide(stb,stbip)
	if tgres is None:
		print(f"{stb} could not find the TV Guide rail, aborting")
		return

	# We should now be on the TV Guide rail
	# Hit "select" to enter the TV Guide
	subprocess.run(['perl', stbcontrolscript, 'control', 'select', stb], stdout=subprocess.DEVNULL)
	sleep(6)	# Wait for TV guide to load

	ocrres = screenshotAndOCR(stb,stbip,800,860,100,215)
	#sshotfile = sshotdir + '/' + stb + '_Screenshot.png'	# Define the main screenshot file

	#urllib.request.urlretrieve('http://' + stbip + ':5800/screenshot.png', sshotfile)	# Grab the screenshot
	#sleep(3)
	#img = cv2.imread(sshotfile)
	#cropImg = img[800:860,100:215]
	#cropImg = (255-cropImg)
	#text = pytesseract.image_to_string(cropImg, lang='eng')  # Process the image through pytesseract to get the text
	#text = text.replace(" ","")
	#text = text.replace("\n","")
	res = re.search("today", ocrres, re.IGNORECASE)
	if res is None:
		print(f"{stb} could not verify it was in the TV Guide")
		return

	# If we get this far, we know we are in the TV Guide. Now send the commands to get to live viewing
	subprocess.run(['perl', stbcontrolscript, 'control', 'cursor down', stb], stdout=subprocess.DEVNULL)
	sleep(3)
	subprocess.run(['perl', stbcontrolscript, 'control', 'select', stb], stdout=subprocess.DEVNULL)
	sleep(3)
	subprocess.run(['perl', stbcontrolscript, 'control', 'select', stb], stdout=subprocess.DEVNULL)
	sleep(10)

	for key in chanData:
		channo = chanData[key]
		nums = list(channo)
		comstring = ',t1,'.join(nums)
		subprocess.run(['perl', stbcontrolscript, 'control', comstring, stb], stdout=subprocess.DEVNULL)
		sleep(15)
		subprocess.run(['perl', stbcontrolscript, 'control', 'cursor left', stb], stdout=subprocess.DEVNULL)
		sleep(2)
		subprocess.run(['perl', stbcontrolscript, 'control', 'select', stb], stdout=subprocess.DEVNULL)
		sleep(3)
		ocrres = screenshotAndOCR(stb,stbip,865,925,345,415)
		#urllib.request.urlretrieve('http://' + stbip + ':5800/screenshot.png', sshotfile)	# Grab the screenshot
		subprocess.run(['perl', stbcontrolscript, 'control', 'backup', stb], stdout=subprocess.DEVNULL)
		sleep(3)
		#img = cv2.imread(sshotfile)
		#cropImg = img[865:925,345:415]
		#cropImg = (255-cropImg)
		#text = pytesseract.image_to_string(cropImg, lang='eng')  # Process the image through pytesseract to get the text
		#text = text.replace(" ","")
		#text = text.replace("\n","")
		res = re.search(channo, ocrres, re.IGNORECASE)
		if res is None:
			print(f"{stb} could not verify it was on {channo}")


def screenshotAndOCR(stb,stbip,y,h,x,w):
	text = ''
	sshotfile = sshotdir + '/' + stb + '_Screenshot.png'	# Define the main screenshot file
	urllib.request.urlretrieve('http://' + stbip + ':5800/screenshot.png', sshotfile)	# Grab the screenshot
	img = cv2.imread(sshotfile)
	cropImg = img.copy()
	if None not in (y,h,x,w):
		cropImg = img[y:h,x:w]

	cropImg = (255-cropImg)
	text = pytesseract.image_to_string(cropImg, lang='eng')  # Process the image through pytesseract to get the text
	text = text.replace(" ","")
	text = text.replace("\n","")
	return text

def tvguide(stb,stbip):

	subprocess.run(['perl', stbcontrolscript, 'control', 'tv guide', stb], stdout=subprocess.DEVNULL)
	sleep(6)

	sshotfile = sshotdir + '/' + stb + '_Screenshot.png'

	# Clear out any old screenshot files for this STB
	if exists(sshotfile):
		os.remove(sshotfile)

	found = 0
	for i in range(10):
		urllib.request.urlretrieve('http://' + stbip + ':5800/screenshot.png', sshotfile)
		sleep(1)
		if exists(sshotfile) is None:
			continue

		img = cv2.imread(sshotfile)
		cropImg = img[590:750, 80:420]  # Crop the image to the area where the start of the Apps bar is
		cropImg = (255-cropImg)
		text = pytesseract.image_to_string(cropImg, lang='eng')  # Process the image through pytesseract to get the text
		text = text.replace(" ","")
		text = text.replace("\n","")

		res = re.search("tvguide", text, re.IGNORECASE)
		if res is not None:
			found = 1
			break
		else:
			#print(f"{text} did not match our key {option}",file=sys.stderr)
			subprocess.run(['perl', stbcontrolscript, 'control', 'cursor down', stb], stdout=subprocess.DEVNULL)
			sleep(1)


	return found


def wakeCheck(stb,stbip):
	awake = 0
	for i in range(3):
		pingres = subprocess.run(['ping','-c','1',stbip], stdout=subprocess.DEVNULL)
		if pingres.returncode != 0:
			subprocess.run(['perl', stbcontrolscript, 'control', 'wakeonlan', stb], stdout=subprocess.DEVNULL)
			sleep(15)
		else:
			awake = 1
			break

	return awake



runningSTBs = {}	# This will contain entries for all STBs that are currently set to run tests
for b in stbs:
	# First check the given STB has a valid number
	res = re.search('\d+',b)
	if res is None:
		print(f"{b} had no valid STB number")
		continue
	num = res[0]	# Capture the number from the provided STB string
	box = 'STB' + str(num)	# Create the STB name for testing

	# Now check this STB hasn't been selected more than once by accident
	# This will avoid clashes
	if box in runningSTBs:
		print(f"{box} has already been set to test")
		continue
	else:
		runningSTBs[box] = 1

	newpid = os.fork()
	if newpid == 0:
		chanChange(box)
		os._exit(0)
