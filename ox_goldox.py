# -*- coding:utf-8 -*-
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web


import  CMySQLPort
import time
import os


from log import MyLog

from log import OXTRACE
from ox_define import LOG_MODE
from ox_define import LOG_FILE

from ox_goldox_msg_pb2 import OX_GOLD_OX_MSG
from ox_goldox_msg_pb2 import OX_GOLD_OX_RET_MSG
# /getgoldox?id=xxx&type=x
# type=1是获取金牛信息 2是领取金牛信息
class GetGoldOx(tornado.web.RequestHandler):

    def get(self):
        uID = int(self.get_argument( "id", 0 ))
        type = int(self.get_argument( "type", 0 ))
        nRetMsg = OX_GOLD_OX_RET_MSG()
        weight, goldnum, nexttime, maxgoldnum, sparetime, gettime, daymaxgold = self.ComputerOxWeight( uID )
        #print ( "%d %d %d %d %d %d %d " %(weight, goldnum, nexttime, maxgoldnum, sparetime, gettime, daymaxgold ) )
        nRetMsg.nRet = 1
        nRetMsg.weight = weight
        nRetMsg.goldnum = goldnum
        nRetMsg.nexttime = nexttime
        nRetMsg.maxgoldnum = maxgoldnum
        nRetMsg.sparetime = sparetime
        nRetMsg.daymaxgoldnum = daymaxgold
        #print( "type =%d" %(type) )
        #print( "uID =%d" %(uID) )
        if type == 2:
            #领取
            if nRetMsg.goldnum > 0:
                data = self.getoxgold( uID, nRetMsg.goldnum, gettime )
                if data[0][0] != 0:
                    #领取错误
                    nRetMsg.nRet = 0
                else:
                    nRetMsg.goldnum = data[0][1]
            else:
                nRetMsg.nRet = 0

        retstr = nRetMsg.SerializeToString()
        self.write(  retstr )

    def post(self):
        msg = OX_GOLD_OX_MSG()
        msg.ParseFromString( self.request.body )
        uID = msg.uID
        nRetMsg = OX_GOLD_OX_RET_MSG()
        weight, goldnum, nexttime, maxgoldnum, sparetime, gettime, daymaxgold = self.ComputerOxWeight( uID )
        nRetMsg.nRet = 1
        nRetMsg.weight = weight
        nRetMsg.goldnum = goldnum
        nRetMsg.nexttime = nexttime
        nRetMsg.maxgoldnum = maxgoldnum
        nRetMsg.sparetime = sparetime
        nRetMsg.daymaxgoldnum = daymaxgold
        type = msg.type
        if type == 2:
            #领取
            if nRetMsg.goldnum > 0:
                data = self.getoxgold( uID, nRetMsg.goldnum, gettime )
                if data[0][0] != 0:
                    #领取错误
                    nRetMsg.nRet = 0
                else:
                    nRetMsg.goldnum = data[0][1]
            else:
                nRetMsg.nRet = 0

        retstr = nRetMsg.SerializeToString()
        self.write(  retstr )


    def ComputerOxWeight(self, uID):
        oxweight = 0
        oxgold = 0
        newgettime = 0
        #当前时间
        curtime = long(time.time())
        #领取时间
        gettime = 0
        daymaxgold = 0
        #获取金牛重量
        data = self.SelectOXWeight( uID )
        #0.25 * a + 0.2 * b + 0.15 * c + 0.1 * d + 0.05 *e + 0.01 *f
        #a,b,c,d,e分别的重量区间为0-20-40-60-80-100   100以上的部分的产量系数为0.01
        wsection = (0, 20, 40, 60, 80, 100 )
        #wxishu = ( 0.25, 0.2, 0.15, 0.1, 0.05, 0.01 )
        wxishu = ( 0.5, 0.4, 0.3, 0.2, 0.1, 0.05 )
        maxgoldlist = (6000, 10000, 13000, 15000, 16000)

        maxgold = 0
        rechargeNum = 0
        isfirstget = 0
        #print data
        if data:
            gettime = data[0][2]
            isfirstget = data[0][3]
            if data[0][0] >=  0:
                oxweight = oxweight + 2
                rechargeNum = data[0][1]
                index = int( rechargeNum/20 )
                if index >= 5:
                    maxgold = maxgoldlist[4]
                else:
                    maxgold = maxgoldlist[index]

                #print( "------rechargeNum = %d maxgold = %d" %(rechargeNum,maxgold) )
                #print index
                #print ( "---------------------" )
                for i in range( 0, 5 ):
                    #print(" index = %d i = %d" %(index, i))
                    if index >  i:
                        oxweight = oxweight + (wsection[i+1]-wsection[i])*wxishu[i]
                        if (i == 4) and  (index >= 5):
                            oxweight = oxweight + (rechargeNum-wsection[5])*wxishu[5]
                            #print(" index = %d oxweight = %f 100:%f" %(index, oxweight, (rechargeNum-wsection[5])*wxishu[5]))
                            break;
                    elif index == i:
                        oxweight = oxweight + (rechargeNum - wsection[i])*wxishu[i]
                        #print(" index = %d oxweight = %d" %(index, oxweight))
                        break
                    #print( "oxweight = %d " %(oxweight) )
            else:
                return ( 0, 0, 0, 0, 0, 0, 0 )
            #print ( "---------------------" )
        #通过重量计算金币数
        if gettime == 0 :
            return ( 0, 0, 0, 0, 0, 0, 0 )

        #测试用
        GETTIME = 600
        #GETTIME = 60
        #print curtime
        #print gettime
        #print curtime - gettime
        #大于一小时则有金币
        if curtime - gettime >= GETTIME:
            oxgold = int( ((800 + 20*(oxweight-2))/6 )*((curtime - gettime)/GETTIME) )
            nexttime = curtime + GETTIME
        else:
            nexttime = gettime + GETTIME
        daymaxgold = int( (800 + 20*(oxweight-2))*24)
        sparetime = GETTIME - (curtime - gettime)%GETTIME
        #print( "oxgold=%d maxgold = %d" %(oxgold, maxgold))

        vindex = int( rechargeNum/20 )
        if vindex >=4:
            vindex = 4

        oxgold = oxgold + isfirstget* maxgoldlist[vindex]

        if oxgold > maxgold:
            oxgold = maxgold
            newgettime = long( time.time() )
        else:
            newgettime = gettime + int((curtime - gettime)/GETTIME)*GETTIME


        #print( "curtime - gettime = %d" %(curtime - gettime) )
        #print( "oxweight=%d oxgold = %d" %(oxweight, oxgold))
        #print( "newgettime = %d" %(newgettime))

        return ( oxweight, oxgold, nexttime, maxgold, sparetime,newgettime, daymaxgold )



    #查询金牛重量
    def SelectOXWeight( self, uID ):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_GetRechargeFund', uID )
        data = sqlhandler.sql_fetchall()
        #print( data )
        return data


    def getoxgold(self, uID, goldnum, gettime ):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        utoken = int(self.get_argument( "token", 0 ))
        #print ("gettime=%d" %(gettime))
        sqlhandler.sql_callproc( 'SP_TaurusDayPrsent', uID, goldnum, utoken, gettime )
        data = sqlhandler.sql_fetchall()
        return data


    def compute_etag(self):
        return None

