#!/usr/bin/python3

import re

input = '1 - 42'

result = re.search(r"(\d+)\s*\-\s*(\d+)", input)
stbs = []

if len(result.groups()) == 2:
	start = result.group(1)
	end = result.group(2)
	#print(f"{start} - {end}")
	stbs = range(int(start),int(end)+1)

for i in stbs:
	print(i)
