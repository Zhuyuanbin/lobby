# -*- coding:utf-8 -*-
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web


# 根据计费位置 渠道 发送对应的商品信息
# /newgifts?id=17920896&maxAmount=0&giftId=1&roomId=5&gold=0&gameFlg=1&channelId=88
# &douId=0&weizhi=1&version=322
# /newgifts?id=17920896&channelId=88&douId=0&weizhi=4&version=322
class OxNewGifts(tornado.web.RequestHandler):
    def get(self):


    def post(self):
