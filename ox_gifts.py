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

#ÄÄÐ©ÇþµÀÕý³£ÏÔÊ¾¸¶·ÑÌáÊ¾
g_normalPay=(99967636,99977400)
g_normalPay_qudao=(999,)

#æœ€å¤§é€šé“,ç¤¼åŒ…id,è¯·æ±‚é‚£ä¸ªæˆ¿é—´çš„é…ç½®,å…ƒå®æ•°é‡,æ˜¯å¦æ¸¸æˆå†…è¯·æ±‚æ ‡è®°,å¹³å°id,å­æ¸ é“id
#/gifts?maxAmount=xxx&giftId=xxx&roomId=xx&gold=xx&gameFlg=xx&channelId=xx&douId=xx&weizhi=xx
class OxGifts(tornado.web.RequestHandler):
    def get(self):
        global g_normalPay
        global g_normalPay_qudao
        #roomAmountConfig=[2,4,6,0,6]#¶·µØÖ÷ 0³õ¼¶,1ÖÐ¼¶,2¸ß¼¶,3Ã»ÓÐÓÃ,4´óÌü
        roomAmountConfig=[2,4,0,6,6,6]#¶·µØÖ÷ 0³õ¼¶,1ÖÐ¼¶,2Ã»ÓÐÓÃ,3¸ß¼¶,4´óÌü,5±ÈÈü
        uID = int(self.get_argument( "id", 0 ))
        giftId = int(self.get_argument( "giftId", 0 ))
        smsAmount=int(self.get_argument( "maxAmount", 0 ))
        roomId=int(self.get_argument( "roomId", -1 ))
        gameFlg=int(self.get_argument( "gameFlg", 0 ))
        channelId=int(self.get_argument( "channelId", 0 ))
        douId=int(self.get_argument( "douId", 0 ))
        #±êÊ¶ÓÃ»§µã»÷Ôª±¦¶Ò»»½ð±ÒµÄ±ê¼Ç 0:ÓÎÏ··¿¼ä 1:½ð±Ò²»¹»²»×ãÒÔ½øÈëÓÎÏ··¿¼ä  2:ÀÏ»¢»ú Ë®¹û»ú Éý¼¶ Ê±Ê±²ÊµÈ½ð±Ò²»×ã  
        #3£º±»Ìß³öÓÎÏ··¿¼ä 4£ºÔÚÉÌ³Ç¶ÌÐÅ¶Ò»»½ð±Ò  5:¶Ò»»VIP½ðÅ£ 6:´óÌü³äÖµ°´Å¥7:½ðÅ£³äÖµ
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
                 roomConfig=[6,12,6,18,12,18]# 0³õ¼¶,1ÖÐ¼¶,2Ã»ÓÐÓÃ,3¸ß¼¶,4´óÌü,5±ÈÈü
                 usertype=data1[0][0]
                 data=data1;
                 if(weizhi==6):#´óÌü¿ì³ä
                     smsAmount=12
                 elif(weizhi==1 or weizhi==0 or weizhi==3):	#¸÷ÖÖ·¿¼ä½ð±Ò²»×ã
                     smsAmount=roomConfig[roomId]
                 elif(weizhi ==5):#´óÌü¹ºÂòVIP
                     smsAmount=25
                     giftId=2
                 elif(weizhi==7):		#´óÌü½ðÅ£³äÖµ 
                     smsAmount=25
                     giftId=1
                 elif(weizhi==2):		#ÀÏ»¢»ú Ë®¹û»ú Éý¼¶ Ê±Ê±²ÊµÈ½ð±Ò²»×ã  
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
