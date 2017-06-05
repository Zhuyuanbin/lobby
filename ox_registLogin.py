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
class OxRegLogin(tornado.web.RequestHandler):
    def post(self):
        version = int(self.get_argument( "version", 0 ))
        channelId = int(self.get_argument( "channelId", 0))

        if (len(self.request.body) == 0):
            raise tornado.web.HTTPError(403)
            return
        oxdata = OX_REGLOGIN_MSG()
        oxdataret = OX_REGLOGIN_RESULT();
        
        
        #�����ͻ��˷�����������
        oxdata.ParseFromString( self.request.body )

        account =oxdata.account;
        password=oxdata.password;
        oxdataret.type=-4;
        if(account and password):
            hasecode = self.getHashCode(account);
            OXTRACE(LOG_FILE,str(password));
            #Regist_accountscheck�����룺ƽ̨id���ⲿid���˺š����롢type ��0ע�ᡢ1��¼�������룺0���� ����ע����¼������ȷ��-1 �û����Ѿ����ڡ�-2�û��������벻����
            data=self.GetDataFromDateBase("Regist_accountscheck",channelId,hasecode,account,str(password),oxdata.type)
            if data:
                oxdataret.type = data[0][0];
                oxdataret.externalid=hasecode;
        else:
            oxdataret.type=-3;
        #��������
        retstr = oxdataret.SerializeToString()
        self.write(  retstr )


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














































