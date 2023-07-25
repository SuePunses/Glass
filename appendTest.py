#!/usr/bin/python3

import os

str = 'Hi'
str += ' there!'

print(str)

dir = '/var/www/html/glassAutomation/files/results/ChannelChangeTests_2023-01-17_11:08'

print(os.listdir(dir))
