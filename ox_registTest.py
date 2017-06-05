# -*- coding:utf-8 -*-
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web


import  CMySQLPort
import sys
import os
import time
import log
import ConfigParser
from log import MyLog

from log import OXTRACE
from ox_define import LOG_MODE
from ox_define import LOG_FILE
from ox_gift_msg_pb2 import OX_GIFT_MSG

from ox_reglogin_pb2 import OX_REGLOGIN_MSG
from ox_reglogin_pb2 import OX_REGLOGIN_RESULT
#IOSע���¼
#/OxRegLogin?version=xx&channelId=xx
class OxRegLoginTest(tornado.web.RequestHandler):
    def get(self):
        for i in range(1251,1301,1):
            account = "zyb"+str(i)
            password=account;
            if(account and password):
                hasecode = self.getHashCode(account);
                OXTRACE(LOG_FILE,str(password));
                #Regist_accountscheck�����룺ƽ̨id���ⲿid���˺š����롢type ��0ע�ᡢ1��¼�������룺0���� ����ע����¼������ȷ��-1 �û����Ѿ����ڡ�-2�û��������벻����
                data=self.GetDataFromDateBase("Regist_accountscheck",88,hasecode,account,password,0)
                if data:
                    OXTRACE(LOG_FILE,data[0][0]);
                #time.sleep( 0.1)
        self.write(  "OK!" )


    def GetDataFromDateBase(self, spName, *args):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( spName, *args)
        data = sqlhandler.sql_fetchall()
        #print data
        return data


    def convert_n_bytes(self,n, b):
        bits = b*8
        return (n + 2**(bits-1)) % 2**bits - 2**(bits-1)

    def convert_4_bytes(self,n):
        return self.convert_n_bytes(n, 4)

    def getHashCode(self,s):
        h = 0
        n = len(s)
        for i, c in enumerate(s):
            h = h + ord(c)*31**(n-1-i)
        return self.convert_4_bytes(h)














































