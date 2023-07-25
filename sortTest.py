#!/usr/bin/python3

import os
import re

dirs = ['STB1','STB11','STB4','STB42','STB21']
r = re.compile(r'(\d+)')
dirs.sort(key=lambda x:int(r.search(x).group(1)))

print(dirs)
