#!/usr/bin/python3

from time import sleep

load = 0
cnt = 0

while not load:
	cnt = cnt + 1
	print(cnt)
	if cnt > 10:
		break
	sleep(1)
