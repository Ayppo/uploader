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


class Uploader(object):
    def __init__(self, cookie):
        # TODO: 增加登录接口使用账号密码登陆
        self.MAX_RETRY_TIMES = 5
        self.profile = 'ugcupos/yb'
        self.cdn = 'ws'
        self.csrf = re.search('bili_jct=(.*?);', cookie + ';').group(1)
        self.mid = re.search('DedeUserID=(.*?);', cookie + ';').group(1)
        self.session = requests.session()
        self.session.headers['cookie'] = cookie
        self.session.headers['Accept'] = 'application/json, text/javascript, */*; q=0.01'
        self.session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'
        self.session.headers['Referer'] = 'https://space.bilibili.com/{mid}/#!/'.format(mid=self.mid)


    def _upload(self, filepath):
        """执行上传文件操作"""
        if not os.path.isfile(filepath):
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
        times = 0
        while times < self.MAX_RETRY_TIMES:
            times += 1
            try:
                response = self.session.get(preupload_url, params=params)
                upload_info = response.json()
                break
            except Exception:
                pass

        # 本次上传bilibili端文件名
        upload_info['bili_filename'] = upload_info['upos_uri'].split('/')[-1].split('.')[0]
        # 本次上传url
        endpoint = 'http:%s/' % upload_info['endpoint']
        upload_url = re.sub(r'^upos://', endpoint, upload_info['upos_uri'])
        print >> sys.stderr, 'UPLOAD URL:', upload_url
        # 本次上传headers
        upload_headers = {'X-Upos-Auth': upload_info['auth']}

        # 2.获取本次上传的upload_id
        times = 0
        while times < self.MAX_RETRY_TIMES:
            times += 1
            try:
                response = requests.post(upload_url + '?uploads&output=json', headers=upload_headers)
                upload_info['upload_id'] = response.json()['upload_id']
                break
            except Exception, e:
                print str(e)
                pass

        print >> sys.stderr, 'UPLOAD INFO:', upload_info

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
            response = requests.put(upload_url, params=params, data=blob, headers=upload_headers)
            print >> sys.stderr, 'UPLOAD CHUNK', chunk, ':', response.text

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
        response = requests.post(upload_url, params=params, data=parts_info, headers=upload_headers)
        print >> sys.stderr, 'UPLOAD RESULT:', response.text

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

    def upload(self, filepath, title, tid, tag, desc='', source='', cover_path='', dynamic='', no_reprint=1):
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
        # TODO: 增加多P上传
        # 上传文件, 获取上传信息
        upload_info = self._upload(filepath)
        if not upload_info:
            return
        # 获取图片链接
        cover_url = self._cover_up(cover_path) if cover_path else ''
        # 版权判断, 转载无版权
        copyright = 2 if source else 1
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


if __name__ == '__main__':
    cookie = 'finger=edc6ecda; sid=knfjvm2n; stardustvideo=1; CURRENT_FNVAL=8; rpdid=iwxpsppxiwdoskxplpoww; '\
             'fts=1536494317; CURRENT_QUALITY=80; member_v2=1; LIVE_BUVID=bf021f79d618d82a9185a9e94b2ac87b; '\
             'LIVE_BUVID__ckMd5=119e906d758b1132; UM_distinctid=1660567fc7bce5-01bf5d1763c045-8383268-1fa400-1660567fc7c3b7; '\
             'DedeUserID=3867708; DedeUserID__ckMd5=24a621788d887ac6; SESSDATA=31c92c81%2C1540281029%2C741bc432; '\
             'bili_jct=fd0154f557d67360dea0a00dfebf7af7; pgv_pvi=3914371072; _dfcaptcha=854d0e7f6c4134ececc8ca612f69b46b; '\
             'bp_t_offset_3867708=167695254318052704; buvid3=096DDB4B-A946-4251-91E0-E516E06309C4163036infoc'
    uper = Uploader(cookie)
    uper.upload('Judd Trump.mkv', '特朗姆普的暴力美学', 163, '台球,斯诺克,特朗姆普', cover_path='Judd Trump.jpg')
