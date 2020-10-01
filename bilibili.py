#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import sys
import math
import time
import json
import base64
import requests
import argparse
from requests.adapters import HTTPAdapter


class Uploader(object):
    def __init__(self):
        # TODO: 增加登录接口使用账号密码登陆
        cookie = '----------------请自行获取B站COOKIE--------------'
        self.MAX_RETRYS = 5
        self.profile = 'ugcupos/yb'
        self.cdn = 'ws'
        self.csrf = re.search('bili_jct=(.*?);', cookie + ';').group(1)
        self.mid = re.search('DedeUserID=(.*?);', cookie + ';').group(1)
        self.session = requests.session()
        self.session.mount('https://', HTTPAdapter(max_retries=self.MAX_RETRYS))
        self.session.headers['cookie'] = cookie
        self.session.headers['Accept'] = 'application/json, text/javascript, */*; q=0.01'
        self.session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'
        self.session.headers['Referer'] = 'https://space.bilibili.com/{mid}/#!/'.format(mid=self.mid)


    def _upload(self, filepath):
        """执行上传文件操作"""
        if not os.path.isfile(filepath):
            print >> sys.stderr, 'FILE NOT EXISTS:', filepath
            return

        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)

        # 1.获取本次上传所需信息
        preupload_url = 'https://member.bilibili.com/preupload'
        params = {
            'os': 'upos',
            'r': 'upos',
            'ssl': '0',
            'name': filename,
            'size': filesize,
            'upcdn': self.cdn,
            'profile': self.profile,
        }
        response = self.session.get(preupload_url, params=params)
        upload_info = response.json()

        # 本次上传bilibili端文件名
        upload_info['bili_filename'] = upload_info['upos_uri'].split('/')[-1].split('.')[0]
        # 本次上传url
        endpoint = 'http:%s/' % upload_info['endpoint']
        upload_url = re.sub(r'^upos://', endpoint, upload_info['upos_uri'])
        print >> sys.stderr, 'UPLOAD URL:', upload_url
        # 本次上传session
        upload_session = requests.session()
        upload_session.mount('http://', HTTPAdapter(max_retries=self.MAX_RETRYS))
        upload_session.headers['X-Upos-Auth'] = upload_info['auth']

        # 2.获取本次上传的upload_id
        response = upload_session.post(upload_url + '?uploads&output=json')
        upload_info['upload_id'] = response.json()['upload_id']

        print(sys.stderr, 'UPLOAD INFO:', upload_info)

        # 3.分块上传文件
        CHUNK_SIZE = 4 * 1024 * 1024
        total_chunks = math.ceil(filesize * 1.0 / CHUNK_SIZE)
        offset = 0
        chunk = 0
        parts_info = {'parts': []}
        fp = open(filepath, 'rb')
        while True:
            blob = fp.read(CHUNK_SIZE)
            if not blob:
                break
            params = {
                'partNumber': chunk + 1,
                'uploadId': upload_info['upload_id'],
                'chunk': chunk,
                'chunks': total_chunks,
                'size': len(blob),
                'start': offset,
                'end': offset + len(blob),
                'total': filesize,
            }
            response = upload_session.put(upload_url, params=params, data=blob)
            print('Uploading...',math.floor(chunk / total_chunks  * 100), '%  UPLOAD CHUNK', chunk, ':', response.text)

            parts_info['parts'].append({
                'partNumber': chunk + 1,
                'eTag': 'etag'
            })
            chunk += 1
            offset += len(blob)

        # 4.标记本次上传完成
        params = {
            'output': 'json',
            'name': filename,
            'profile': self.profile,
            'uploadId': upload_info['upload_id'],
            'biz_id': upload_info['biz_id']
        }
        response = upload_session.post(upload_url, params=params, data=parts_info)
        print(sys.stderr, 'UPLOAD RESULT:', response.text)

        return upload_info

    def _cover_up(self, image_path):
        """上传图片并获取图片链接"""
        if not os.path.isfile(image_path):
            return ''
        fp = open(image_path, 'rb')
        encode_data = base64.b64encode(fp.read())
        url='https://member.bilibili.com/x/vu/web/cover/up'
        data={
            'cover': b'data:image/jpeg;base64,' + encode_data,
            'csrf': self.csrf,
        }
        response = self.session.post(url, data=data)
        return response.json()['data']['url']

    def upload(self, filepath, title, tid, tag='', desc='', source='', cover_path='', dynamic='', no_reprint=1):
        """视频投稿
        Args:
            filepath   : 视频文件路径
            title      : 投稿标题
            tid        : 投稿频道id,详见https://member.bilibili.com/x/web/archive/pre
            tag        : 视频标签，多标签使用','号分隔
            desc       : 视频描述信息
            source     : 转载视频出处url
            cover_path : 封面图片路径
            dynamic    : 分享动态, 比如："#周五##放假# 劳资明天不上班"
            no_reprint : 1表示不允许转载,0表示允许
        """
        # TODO:
        # 1.增加多P上传
        # 2.对已投稿视频进行删改, 包括删除投稿，修改信息，加P删P等

        # 上传文件, 获取上传信息
        upload_info = self._upload(filepath)
        if not upload_info:
            return
        # 获取图片链接
        cover_url = self._cover_up(cover_path) if cover_path else ''
        # 版权判断, 转载无版权
        copyright = 2 if source else 1
        # tag设置
        if isinstance(tag, list):
            tag = ','.join(tag)
        # 设置视频基本信息
        params = {
            'copyright' : copyright,
            'source'    : source,
            'title'     : title,
            'tid'       : tid,
            'tag'       : tag,
            'no_reprint': no_reprint,
            'desc'      : desc,
            'desc_format_id': 0,
            'dynamic': dynamic,
            'cover'     : cover_url,
            'videos'    : [{
                'filename': upload_info['bili_filename'],
                'title'   : title,
                'desc'    : '',
            }]
        }
        if source:
            del params['no_reprint']
        url = 'https://member.bilibili.com/x/vu/web/add?csrf=' + self.csrf
        response = self.session.post(url, json=params)
        print >> sys.stderr, 'SET VIDEO INFO:', response.text
        return response.json()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='上传bilibili视频')
    parser.add_argument('-f', '--file', help='视频文件路径', required=True)
    parser.add_argument('-t', '--title', help='标题', required=True)
    parser.add_argument('-c', '--channel', type=int, help='频道id, 详见https://member.bilibili.com/x/web/archive/pre', required=True)
    parser.add_argument('-T', '--tag', nargs='*', help='标签')
    parser.add_argument('-C', '--cover', help='封面文件路径')
    args = parser.parse_args()

    uper = Uploader()
    uper.upload(args.file, args.title, args.channel, args.tag, args.cover)
