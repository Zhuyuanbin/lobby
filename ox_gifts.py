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

#��Щ����������ʾ������ʾ
g_normalPay=(99967636,99977400)
g_normalPay_qudao=(999,)

#最大通道,礼包id,请求那个房间的配置,元宝数量,是否游戏内请求标记,平台id,子渠道id
#/gifts?maxAmount=xxx&giftId=xxx&roomId=xx&gold=xx&gameFlg=xx&channelId=xx&douId=xx&weizhi=xx
class OxGifts(tornado.web.RequestHandler):
    def get(self):
        global g_normalPay
        global g_normalPay_qudao
        #roomAmountConfig=[2,4,6,0,6]#������ 0����,1�м�,2�߼�,3û����,4����
        roomAmountConfig=[2,4,0,6,6,6]#������ 0����,1�м�,2û����,3�߼�,4����,5����
        uID = int(self.get_argument( "id", 0 ))
        giftId = int(self.get_argument( "giftId", 0 ))
        smsAmount=int(self.get_argument( "maxAmount", 0 ))
        roomId=int(self.get_argument( "roomId", -1 ))
        gameFlg=int(self.get_argument( "gameFlg", 0 ))
        channelId=int(self.get_argument( "channelId", 0 ))
        douId=int(self.get_argument( "douId", 0 ))
        #��ʶ�û����Ԫ���һ���ҵı�� 0:��Ϸ���� 1:��Ҳ��������Խ�����Ϸ����  2:�ϻ��� ˮ���� ���� ʱʱ�ʵȽ�Ҳ���  
        #3�����߳���Ϸ���� 4�����̳Ƕ��Ŷһ����  5:�һ�VIP��ţ 6:������ֵ��ť7:��ţ��ֵ
        weizhi=int(self.get_argument( "weizhi", -1 ))
        OXTRACE(LOG_FILE,str(gameFlg))
        gold=int(self.get_argument( "gold", 0 ))
        payType=0
        resultMsg =OX_GIFT_MSG()

        tempUYype=0;
        for d in g_normalPay_qudao:
            if d == channelId:
                tempUYype=200;
        for d in g_normalPay:
            if d== douId:
                tempUYype=200;
            
        if(smsAmount>8): 
            smsAmount=8
        if(giftId==5):
            if(smsAmount==0 or channelId==7):
                resultMsg.usertype=-1;
                resultMsg.amount=0
                resultMsg.paytype=0
                resultMsg.productid=0;
                for i in range(3,8,1):
                    resultMsg.giftvaule.append(0)
                retstr = resultMsg.SerializeToString()
                self.write(  retstr )
                return ;
            else:
                giftId=1


        if(channelId==88):
             data1 = self.GetDataFromDateBase( 'Charge_IosGiftContent', uID, 1,0,weizhi )      
             if(data1):
                 OXTRACE(LOG_FILE,"in this")
                 roomConfig=[6,12,6,18,12,18]# 0����,1�м�,2û����,3�߼�,4����,5����
                 usertype=data1[0][0]
                 data=data1;
                 if(weizhi==6):#�������
                     smsAmount=12
                 elif(weizhi==1 or weizhi==0 or weizhi==3):	#���ַ����Ҳ���
                     smsAmount=roomConfig[roomId]
                 elif(weizhi ==5):#��������VIP
                     smsAmount=25
                     giftId=2
                 elif(weizhi==7):		#������ţ��ֵ 
                     smsAmount=25
                     giftId=1
                 elif(weizhi==2):		#�ϻ��� ˮ���� ���� ʱʱ�ʵȽ�Ҳ���  
                     smsAmount=6
                 else:
                      smsAmount=12
                     
                 if(usertype%100!=1):
                     data = self.GetDataFromDateBase( 'Charge_IosGiftContent', uID,giftId ,smsAmount ,weizhi)
                 
                 resultMsg.usertype=data[0][0]
                 #resultMsg.usertype=2
                 if(resultMsg.usertype<100):
                     resultMsg.usertype=resultMsg.usertype+200;
                 resultMsg.amount=data[0][1]
                 resultMsg.paytype=1
                 resultMsg.productid=data[0][2]
                 for i in range(3,10,1):
                     resultMsg.giftvaule.append(data[0][i])
                 for d in data[0]:
                     OXTRACE(LOG_FILE,d)
                 resultMsg.payId="NiuNiuYeFKKC%04d"%resultMsg.amount
        elif(gameFlg==0):
            OXTRACE(LOG_FILE,"game wai")
            data = self.GetDataFromDateBase( 'Charge_GiftContent', uID, giftId,smsAmount )
            if(data):
                resultMsg.usertype=data[0][0]
                if(resultMsg.usertype<100):
                    resultMsg.usertype=resultMsg.usertype+tempUYype
                if(resultMsg.amount==smsAmount):
                    resultMsg.paytype=0
                else:
                    resultMsg.paytype=1
                resultMsg.productid=data[0][2]
                for i in range(3,8,1):
                    resultMsg.giftvaule.append(data[0][i])

                if(roomId!=-1 and smsAmount==0):
                    resultMsg.amount=roomAmountConfig[roomId]
                    if(resultMsg.usertype%100==1):
                        resultMsg.giftvaule[0]=roomAmountConfig[roomId]*20000
                    else:
                        resultMsg.giftvaule[0]=roomAmountConfig[roomId]*10000  
                else:
                    resultMsg.amount=data[0][1]
                for d in resultMsg.giftvaule:
                    OXTRACE(LOG_FILE,d)
                OXTRACE(LOG_FILE,"resultMsg.usertype=%d,payType=%d,resultMsg.amount=%d,resultMsg.productid=%d,"%(resultMsg.usertype,payType,resultMsg.amount,resultMsg.productid))
        else:
            self.GetDataFromDateBase( 'Charge_recordFirstInRoom', uID,1)
            if(smsAmount==0 and gold!=0):
                payType=3      
                smsAmount=gold
                if(smsAmount>6): 
                    smsAmount=6
            data = self.GetDataFromDateBase( 'Charge_GiftContent', uID, giftId,smsAmount )
            if(data):
                resultMsg.usertype=data[0][0]
                if(resultMsg.usertype<100):
                    resultMsg.usertype=resultMsg.usertype+tempUYype
                if(payType==0):
                    if(resultMsg.amount==smsAmount):
                        payType=0
                    else:
                        payType=1
                resultMsg.paytype=payType
                resultMsg.productid=data[0][2]
                for i in range(3,8,1):
                    resultMsg.giftvaule.append(data[0][i])
                if(payType!=3):
                    if(roomId!=-1 and smsAmount==0):
                        resultMsg.amount=roomAmountConfig[roomId]
                        if(resultMsg.usertype%100==1):
                            resultMsg.giftvaule[0]=roomAmountConfig[roomId]*20000
                        else:
                            resultMsg.giftvaule[0]=roomAmountConfig[roomId]*10000  
                    else:
                        resultMsg.amount=data[0][1]
                else:
                    if(roomId!=-1 ):
                        if(smsAmount>roomAmountConfig[roomId]):
                            resultMsg.amount=roomAmountConfig[roomId]
                            if(resultMsg.usertype%100==1):
                                resultMsg.giftvaule[0]=roomAmountConfig[roomId]*20000
                            else:
                                resultMsg.giftvaule[0]=roomAmountConfig[roomId]*10000  
                        else:
                            resultMsg.amount=smsAmount
                            if(resultMsg.usertype%100==1):
                                resultMsg.giftvaule[0]=smsAmount*20000
                            else:
                                resultMsg.giftvaule[0]=smsAmount*10000
                            
                    else:
                        resultMsg.amount=data[0][1]
                for d in resultMsg.giftvaule:
                    OXTRACE(LOG_FILE,d)
                #print("amount="+str(resultMsg.amount)+"payType="+str(payType))
                OXTRACE(LOG_FILE,"resultMsg.usertype=%d,payType=%d,resultMsg.amount=%d,resultMsg.productid=%d,"%(resultMsg.usertype,payType,resultMsg.amount,resultMsg.productid))
        retstr = resultMsg.SerializeToString()
        self.write(  retstr )


    def GetDataFromDateBase(self, spName, *args):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( spName, *args)
        data = sqlhandler.sql_fetchall()
        #print data
        return data
