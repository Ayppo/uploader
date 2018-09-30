#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import json
import time

from utils import bilibili


client = bilibili.Uploader()
tid = 24
tag = [u'AMV', u'燃向', u'我的英雄学院']

for filename in os.listdir('download'):
    if not filename.endswith('.info.json'):
        continue

    info = json.load(open(os.path.join('download', filename)))
    video_path = info['_filename']
    basename = video_path.rsplit('.', 1)[0]
    for ext in ['.mp4', '.mkv', '.flv']:
        if os.path.isfile(basename+ext):
            video_path = basename + ext
            break
    cover_path = basename + '.jpg'
    # title = u'【AMV/搬运】我的英雄学院--' + info['title']
    title = u'【AMV/搬运】我的英雄学院燃向混剪'
    source = info['webpage_url']
    author = info['uploader']
    desc = u'—— BY 搬运机器人, 代号Atom-9527\n\n原简介：\n' + info['description']
    if len(desc) > 240:
        desc = desc[:240] + '...'
    dynamic = ''.join(['#'+t+'#' for t in tag]) + u' 我的英雄学院燃向混剪'
    client.upload(video_path, title, tid, tag, desc, source, cover_path=cover_path, dynamic=dynamic)

    print 'UPLOADED:', filename
    time.sleep(30)
