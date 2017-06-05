# -*- coding:utf-8 -*-
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web


import  CMySQLPort

import os
import time
import log
import ConfigParser
import sys
sys.path.append("./mall/")
from ox_gift_msg_pb2 import OX_GIFT_MSG
from ox_lobby_msg_pb2 import OX_LOBBY_MSG
from ox_mall_msg_pb2 import OX_MALL_RECHARGE_RECORD
from ox_mall_msg_pb2 import OX_MALL_GOODS
from ox_mall_msg_pb2 import OX_MALL_GOODS_DATA
from ox_lobby_msg_pb2 import OX_LOBBY_GET_GOLD
from ox_lobby_msg_pb2 import ox_mall2_data
from ox_lobby_msg_pb2 import ox_mall2_goods_data
from ox_lobby_msg_pb2 import OX_New_Active_Content
from ox_lobby_msg_pb2 import OX_New_Active_Tips


from log import MyLog

from log import OXTRACE
from ox_define import LOG_MODE
from ox_define import LOG_FILE

from ox_cjq_modual import OxCJQModual

#服务器通信
from serverthread import ServerSendThread
from serverthread import g_wg_msg

#全局变量保存 QQ 和 邮箱避免多次读取文件
ox_help_qq = None
ox_help_mail = None
ox_award_totalgold = 0
ox_award_reqgold = 0
#全局变量保存商城信息,避免每个用户都要读数据库 如果商城数据发生变量则要重启WEB服务器
g_goods_msg = OX_MALL_GOODS_DATA()
g_goods_msg_init_flag = 0
g_mallbillingnum = 0
g_otherbillingnum = 0
g_birthday = 0
#adress: /lobby?id=XXXXXXXXX
# /lobby?id=XXXXX&platform=X
#360用户请求地址:platform=1
#领取金牛的金币
#adress:/lobby?id=XXXXXXXXX&token=1&gold=xxxxxx

# 1. 解决抽奖券第一个版本不对的问题
# /lobby?id=XXXXX&qudao=X&birthday=1&ver=1
# 2. 解决商城金豆
# /lobby?id=XXXXX&qudao=X&birthday=1&ver=1&mall=2
# 2.0的版本ver=2
# /lobby?id=XXXXX&qudao=X&birthday=1&ver=2&mall=2
# 3. 根据渠道和版本号来区分商城信息 ver由大于200三位数组成,如版本是2.0则传200 2.11则传211
# /lobby?id=XXXXX&qudao=X&birthday=1&ver=200&mall=2
# 4. 加入游戏id  默认为1 斗地主为 2
# /lobby?id=XXXXX&qudao=X&birthday=1&ver=200&mall=2&gameid=x
# 5. 腾讯渠道增加mid传入
# /lobby?id=XXXXX&qudao=X&birthday=1&ver=200&mall=2&gameid=x&mid=xxxxxxxxxx
# 6. 加入豆ID
# /lobby?id=XXXXX&qudao=X&birthday=1&ver=200&mall=2&gameid=x&mid=xxxxxxxxxx&douid=xxxx

#大厅数据配置
#首充说明
#type: 1金牛  2VIP  3抽奖卡 4换牌卡 5看牌卡 6秒杀卡 7互动道具  8游戏提示   9连续登入金币    10赠送金币  11参赛券  12金豆   13vip礼包  14元宝
#num:   天         天    张               张              张                张               个                    次                       个                               个                     个               个            天                个
g_sc_data = ( (1, 7), (7, 7), (8,7),(13,7) )


#房间快充
#kctype----1:初级房间  2:中级房间  3:高级房  4:道具场 5:比赛场
#kcjes-----对应金额
g_kc_data = ( (1,(2)), (2,(4)), (3,(6)), (4,(6)), (5,(6)) )
g_kc_v300_data = ( (1,(4)), (2,(6)), (3,(8)), (4,(6)), (5,(6)) )
#退出挽留  vip新用户  vip老用户 vip过期用户 新手  老手
#连续登入要配置金币数
#type: 1金牛  2VIP  3抽奖卡 4换牌卡 5看牌卡 6秒杀卡 7互动道具  8游戏提示   9连续登入金币    10赠送金币  11参赛券  12金豆   13vip礼包
#num:   天     天    张       张      张      张        个          次           个              个         个       个        个
g_vip_new_exit_type =   ( (13,1), (11,5), (3,1) )
g_vip_old_exit_type =   ( (13,1), (7,20), (8,0), (3,1) )
g_vip_gq_exit_type =   ( (9,1000), (3,1) )
g_new_exit_type = ( (1,1), (11,5), (3,1) )
g_old_exit_type =   ( (9,1000), (3,1) )

#哪些渠道不显示娱乐厅
g_nodisp_ylt = ( 0,11,  17, 19, 14, 22, 26, 4,88 )
g_nodisp_rank=(88,)


#哪些渠道正常显示付费提示
g_normalPay=(99967636,99977400)#douid
g_normalPay_qudao=(999,998)
g_noyltDouId=(99967636,99977400 )#douid
#使用充值方式
g_sms_fee_qudao = ( 0, )
g_third_fee_qudao = ( 0, )

class OxLobby(tornado.web.RequestHandler):
    #def __init__(self):
        #config = ConfigParser.ConfigParser()
        #config.readfp(open("ox.ini"))
        #mallbillingnum = config.get( "billing", "qq" )
        #otherbillingnum = config.get( "billing", "mail" )
        #pass

    #启动游戏服务器通信线程
    g_wg_msg.setDaemon(True)
    g_wg_msg.setName( "ox-wg-msg" )
    g_wg_msg.start()

    #请求数据
    def __init_msg__(self):
        global ox_help_qq
        global ox_help_mail
        global g_mallbillingnum
        global g_otherbillingnum
        global g_birthday

        if ox_help_qq is None:
            #读取数据库信息
            config = ConfigParser.ConfigParser()
            config.readfp(open("ox.ini"))
            ox_help_qq = config.get( "help", "qq" )
            ox_help_mail = config.get( "help", "mail" )
            g_mallbillingnum = int( config.get( "billing", "mallbillingnum" ) )
            g_otherbillingnum = int( config.get( "billing", "otherbillingnum" ) )
            g_birthday = int( config.get( "birthday", "birthdayflag" ) )


    def get(self):
        global ox_help_qq
        global ox_help_mail
        global g_mallbillingnum
        global g_otherbillingnum
        global g_birthday
        global g_sc_data
        global g_kc_data
        global g_vip_new_exit_type
        global g_vip_old_exit_type
        global g_vip_gq_exit_type
        global g_new_exit_type
        global g_old_exit_type
        global g_nodisp_ylt
        global g_sms_fee_qudao
        global g_third_fee_qudao
        global g_normalPay
        global g_normalPay_qudao
        global g_noyltDouId
        global g_nodisp_rank
        lobby_msg = OX_LOBBY_MSG()
        lobby_msg.hasylt = 1
        lobby_msg.disp = 0
        lobby_msg.isrecharge = 0
        lobby_msg.nRet = 0
        lobby_msg.totalgold = 0
        lobby_msg.reqgold = 0
        lobby_msg.oxweight = 0
        lobby_msg.oxgold = 0

        #print( "lobby msg---------------" )
        uID = int(self.get_argument( "id", 0 ))
        token = int(self.get_argument( "token", 0 ))
        qudao = int(self.get_argument( "qudao", 0 ))
        malltype = int(self.get_argument( "mall", 0 ))
        vervalue = int(self.get_argument( "ver", 0 ))
        gameid = int(self.get_argument( "gameid", 0 ))
        smsAmount=int(self.get_argument( "maxAmount", 0 ))#通道最大金额

        douID = int( self.get_argument( "douid", "0" ) )
        if smsAmount>8:
            smsAmount=8
        #金牛金币领取
        if token != 0:
            getgold = OX_LOBBY_GET_GOLD()
            getgold.bsuccess = -1;
            oxgoldnum = 0
            #金币数量在计算一次
            goldweight, oxgoldnum = self.ComputerOxWeight( uID )
            if oxgoldnum > 0 :
                data = self.getoxgold( uID, oxgoldnum )
                #print( "Get Gold Num: %d %d" %(data[0][0], data[0][1]) )
                if data:
                    if data[0][0] == 0:
                        getgold.bsuccess = data[0][0]
                        getgold.goldnum = data[0][1]

            retstr = getgold.SerializeToString()

            #print( "get ox gold-----------" )
            #print( data )
            #print( "len(retstr)=%d", len(retstr) )

            self.write(  retstr )
            return

        #下面是大厅获取数据
        #print( "userID = %d" %(uID) )
        global ox_award_totalgold
        global ox_award_reqgold
        if ox_award_totalgold == 0:
            config = ConfigParser.ConfigParser()
            config.readfp(open("ox.ini"))
            ox_award_totalgold = int( config.get( "award", "totalgold" ) )
            ox_award_reqgold = int( config.get( "award", "reqgold" ) )
        #初始化帮助信息
        self.__init_msg__()

        lobby_msg.totalgold = ox_award_totalgold
        lobby_msg.reqgold = ox_award_reqgold

        #获取用户是否首次充值
        rechargenum = self.SelectClientRecharge(uID)
        if rechargenum > 0:
            lobby_msg.isrecharge = 1
        else:
            lobby_msg.isrecharge = 0

        #是否显示QQ
        if rechargenum >= 5 :
            if ox_help_qq.strip() != '':
                lobby_msg.disp = 1
                lobby_msg.qq = ox_help_qq
                lobby_msg.mail = ox_help_mail

        #初始化商城商品信息
        global g_goods_msg
        global g_goods_msg_init_flag

        lobby_msg.malldistype = 1
        if 1:
            data = self.GetDataFromDateBase( 'SP_StoreExchangeInfo', qudao )
            #OXTRACE( LOG_FILE, data )
            if data:
                for d in data:
                    if (  (malltype == 0)  and ( d[4] <= 5 ) ) \
                            or ( (malltype ==1)   and ( d[4] <= 6 ) )\
                            or (malltype >= 2):
                        goods = lobby_msg.gods.add()
                        goods.index = d[0]
                        #说明格式   服务器商品类型   兑换说明   客户端显示类型
                        # 1 元宝兑换金币	1 - 4
                        # 2 人民币兑换元宝 8 - 10
                        # 3 元宝兑换喇叭	6
                        # 4 元宝兑换VIP	5
                        # 5 金币兑换T人卡	11
                        # 6 金币兑换金豆   12
                        # 7 金币兑换参赛卡   13
                        if d[4] == 1:
                            goods.changetype = 1
                            if d[2] <= 2:
                                goods.type  = 1
                            elif d[2] <= 18:
                                goods.type  = 3
                            else:
                                goods.type  = 4
                        elif d[4] == 2:
                            goods.changetype = 2
                            if d[2] <= 8:
                                goods.type  = 8
                            elif d[2] <= 30:
                                goods.type  = 9
                            else:
                                goods.type  = 10
                        elif d[4] == 3:
                            goods.changetype = 1
                            goods.type  = 6
                        elif d[4] == 4:
                            goods.changetype = 1
                            goods.type  = 5
                        elif d[4] == 5:
                            goods.changetype = 3
                            goods.type  = 11
                        elif d[4] == 6:
                            goods.changetype = 3
                            goods.type  = 12
                        elif d[4] == 7:
                            goods.changetype = 3
                            goods.type  = 13
                        else:
                            goods.changetype = 3
                            goods.type  = 100
                        #元宝数量
                        goods.num1 = d[2]
                        #兑换道具数量
                        goods.num2 = d[3]

        #获取新的商品数据
        if (vervalue >= 200) or (gameid == 2):
            data = self.GetDataFromDateBase( 'SP_ShoppingGiftInfo', qudao, 310 )
            #print( "SP_ShoppingGiftInfo" , data,  qudao, vervalue )
            if data:
                #新版本使用新的商城
                if(qudao==88):
                    lobby_msg.malldistype = 2
                    lobby_msg.mall2data.czyhnum.append( 8 )
                    lobby_msg.mall2data.czyhnum.append( 78 )
                    lobby_msg.mall2data.yhratenum = 10
                    lobby_msg.mall2data.yhtips.append( "27万游戏币".decode("gb2312").encode( "utf-8" ) )
                    lobby_msg.mall2data.yhtips.append( "(售18元\n原价27)".decode("gb2312").encode( "utf-8" )  )
                else:
                    lobby_msg.malldistype = 2
                    lobby_msg.mall2data.czyhnum.append( 8 )
                    lobby_msg.mall2data.czyhnum.append( 78 )
                    lobby_msg.mall2data.yhratenum = 10
                    lobby_msg.mall2data.yhtips.append( "25万金币+VIP".decode("gb2312").encode( "utf-8" ) )
                    lobby_msg.mall2data.yhtips.append( "(售价20\n原价33)".decode("gb2312").encode( "utf-8" )  )

                iconindex = 0
                for d in data :
                    goodsdata = lobby_msg.mall2data.goods.add()
                    goodsdata.goodsid = d[0]
                    goodsdata.iconid = d[1]
                    goodsdata.giftname = d[2].encode( "utf-8" )
                    goodsdata.buytype = d[3]
                    goodsdata.buynum = d[4]
                    goodsdata.iconindex = iconindex
                    iconindex = iconindex + 1
                    #print goodsdata

        #获取充值信息
        lobby_msg.nRet = 0
        data = self.SelectRechange( uID )
        #print( "recharge record" )
        #print( data )
        #print( "----------------" )
        if data:
            if data[0][0] == '\x01':
                nRet = 1
            else:
                nRet = 0

            if nRet == 1:
                #print( "data[0][0] == 1" )
                lobby_msg.nRet = nRet
                for d in data:
                    #print( "d in data" )
                    record = lobby_msg.record.add()
                    record.weathnum = 0
                    #充值状态
                    if d[0] == '\x01':
                        record.status = 1
                    else:
                        record.status = 0

                    #是否首次充值
                    if d[4] == '\x01':
                        record.bisfirst = 1
                    else:
                        record.bisfirst = 0

                    record.weathnum = d[2]

        #读取公告活动
        #activefile = "active.txt"
        #if qudao == 11:
        #    activefile = 'oppo_active.txt'
        #if os.path.isfile( activefile ):
        #    file_object = open( activefile )
        #    try:
        #        lobby_msg.actives = file_object.read( )
        #        file_object.close( )
        #    finally:
        #        file_object.close( )
        #公告要分渠道和版本,不在写文件了
        curtime = int(time.time())
        endtime = time.mktime(time.strptime("2015-7-31 23:59:59",'%Y-%m-%d %H:%M:%S'))
        if (curtime <= endtime) and (vervalue < 320) and (qudao!=88):
            lobby_msg.actives = "【升级送iphone6】\n即日起，首次升级到最新版本的玩家，奖励1万金币+5抽奖券+1兑奖券。截止7.31号更会抽取3名玩获赠iphone6！\n【客服】\n客服电话：028-69605999，客服QQ：2990262726。".decode("gbk").encode("utf-8")
        else:
            #默认公告
            lobby_msg.actives = "【客服】\n客服QQ：2962286122。".decode("gbk").encode("utf-8")

        #获取金牛重量
        #新版本是1可以领取
        lobby_msg.oxget = -2
        lobby_msg.oxweight,  lobby_msg.oxgold = self.ComputerOxWeight( uID )
        if lobby_msg.oxweight > 0:
            if vervalue >= 2:
                if lobby_msg.oxweight > 0:
                    lobby_msg.oxget = 1
                else:
                    lobby_msg.oxget = 0
            else:
                #旧版本是0可以领取
                if lobby_msg.oxgold > 0:
                    lobby_msg.oxget = 0
                else:
                    lobby_msg.oxget = -1


        #print( "-------------" )
        #print lobby_msg.oxweight
        #print lobby_msg.oxgold
        #print( "-------------" )
        #系统喇叭
        data= self.getoxspeaker(qudao)
        if data:
            for d in data:
                speakerData = lobby_msg.speaker.add()
                speakerData.content = d[1]
                speakerData.interval = d[2]
                speakerData.time = d[3]

        #print( "**************************" )
        lobby_msg.mallbillingnum = g_mallbillingnum
        lobby_msg.otherbillingnum = g_otherbillingnum

        #连续登入奖励  区分新旧版本
        if vervalue < 2:
            data = self.getdaynum( uID )
            if data[0][0] >= 0:
                lobby_msg.daynum = data[0][2]
                lobby_msg.goldnum = data[0][3]
        else:
            data = self.GetDataFromDateBase( "SP_ContinueLogon", uID )
            if data[0][0] >= 0:
                lobby_msg.daynum = data[0][2]
                lobby_msg.goldnum = data[0][3]
            else:
                lobby_msg.daynum = data[0][2]
                lobby_msg.goldnum = 0
            #print data
            #print( "get glodnum :%d  daynum:%d" %(lobby_msg.goldnum, lobby_msg.daynum) )

        data = self.getuserfruit( uID );
        #print ( data )
        lobby_msg.fruittips = 0
        if data:
            if data[0][0] == 1:
                lobby_msg.fruittips = 1

        #是否是首次登入 如果是则加奖券
        data = self.GetFirstLogonGods( uID )
        #print "self.GetFirstLogonCjq"
        #print data
        vipGrade = 0
        lobby_msg.firstlogon = 0
        #首次登入
        if data[0][0] == 1:
            lobby_msg.firstlogon = 1

        #VIP升级
        if data[0][1] == 1:
            vipGrade = data[0][2]

        if qudao != 6 :
            #奖券数量
            lobby_msg.lotterynum = self.getlottery( uID )
            #首次登入
            if data[0][0] == 1:
                lobby_msg.csqnum = data[0][3]
                cjqdata = [ 0 ]*6
                m_cjq = OxCJQModual()
                #首次登入
                cjqtype = m_cjq.GetCJQByCondition( 3, 0 )
                #print( "frist logon type= %d" %cjqtype )
                cjqdata[cjqtype - 1] = 1
                lobby_msg.cjqGetNum = 1
                if vipGrade > 0:
                    m_cjq = OxCJQModual()
                    #print( "frist logon vip vipGrade= %d" %vipGrade )
                    cjqtype = m_cjq.GetCJQByCondition( 1, vipGrade )
                    #print( "frist logon vip type= %d" %cjqtype )
                    cjqdata[cjqtype - 1] = cjqdata[cjqtype - 1] + 1
                    lobby_msg.cjqGetNum = 2
                lobby_msg.cjqTotalNum = 0
                data = self.WriteCJQData( uID, token, cjqdata )
                for i in range (0, 6):
                    #print ( "add cjq %d  %d" %( i, data[0][i] ) )
                    lobby_msg.cjqTotalNum = lobby_msg.cjqTotalNum + data[0][i+1]
            else:
                #不是首次登入
                data = self.GetCJQData( uID )
                for i in range (0, 6):
                    #print ( "add cjq %d  %d" %( i, data[0][i] ) )
                    lobby_msg.cjqTotalNum = lobby_msg.cjqTotalNum + data[0][i+1]
                    #print lobby_msg.cjqTotalNum

        if g_birthday == 1:
            #获取日期
            birthday = int(self.get_argument( "birthday", 0 ))
            if birthday == 1:
                data = self.GetBirthday(uID)
                if data:
                    lobby_msg.badult = data[0][0]
                    lobby_msg.birthday = data[0][1]

        lobby_msg.vipup = vipGrade
        #print "lobby_msg.vipup"
        #print lobby_msg.vipup
        #print "-----------------------------"
        #print lobby_msg.cjqTotalNum

        #获取金豆数量
        data = self.GetGoldBean(uID)
        if data:
            lobby_msg.goldbean = data[0][0]
        if vervalue == 0:
            lobby_msg.cjqGetNum = 0

        #充值方式开关
        lobby_msg.smsfeeflag = 3
        for d in g_sms_fee_qudao:
            if qudao == d :
                lobby_msg.smsfeeflag = 0
                break
        #是否
        for d in g_third_fee_qudao:
            if qudao == d :
                lobby_msg.smsfeeflag = 3
                break

        #首充配置
        if lobby_msg.smsfeeflag == 3:
            lobby_msg.scjes.append(1)#大厅
            lobby_msg.scjes.append(1)#初级
            lobby_msg.scjes.append(1)#中级
            lobby_msg.scjes.append(1)#高级
            lobby_msg.scjes.append(1)#诈金牛
            lobby_msg.scjz = 7
        else:
            lobby_msg.scjes.append(6)#大厅
            lobby_msg.scjes.append(2)#初级
            lobby_msg.scjes.append(4)#中级
            lobby_msg.scjes.append(6)#高级
            lobby_msg.scjes.append(4)#诈金牛
            lobby_msg.scjz = 5

        #首充说明
        #sclptype: 1金牛  2VIP  3抽奖卡 4换牌卡 5看牌卡 6秒杀卡
        #sclpnum:  头     天    张       张      张      张
        #print( "sc data------------" )
        for i in range( 0, len(g_sc_data) ):
            #print( "i = %d type=%d  num=%d" %(i, g_sc_data[i][0], g_sc_data[i][1]) )
            lobby_msg.sclptype.append(g_sc_data[i][0])
            lobby_msg.sclpnum.append(g_sc_data[i][1])
        #print( "sc data------------" )

        #房间快充配置
        #print( "kc data------------" )
        kc_data = g_kc_data
        if (vervalue >= 300) :
            kc_data = g_kc_v300_data
        for kcdata in kc_data:
            if 0:
                for num in kcdata[1]:
                    lobby_msg.kctype.append(kcdata[0])
                    lobby_msg.kcjes.append(num)
            else:
                    lobby_msg.kctype.append(kcdata[0])
                    lobby_msg.kcjes.append(kcdata[1])

        #print( "kc data------------" )
        global g_vip_new_exit_type
        global g_vip_old_exit_type
        global g_vip_gq_exit_type
        #退出挽留
        for exitdata in g_vip_new_exit_type:
            if (qudao != 6) or (exitdata[0] != 3):
                lobby_msg.vipnewexittype.append(exitdata[0])
                lobby_msg.vipnewexitnum.append(exitdata[1])

        for exitdata in g_vip_old_exit_type:
            if (qudao != 6) or (exitdata[0] != 3):
                lobby_msg.vipoldexittype.append(exitdata[0])
                if exitdata[0] == 9:
                    data = self.GetDataFromDateBase( "SP_LogoutSaty", uID )
                    lobby_msg.vipoldexitnum.append(data[0][0])
                else:
                    lobby_msg.vipoldexitnum.append(exitdata[1])

        for exitdata in g_vip_gq_exit_type:
            if (qudao != 6) or (exitdata[0] != 3):
                lobby_msg.vipgqexittype.append(exitdata[0])
                if exitdata[0] == 9:
                    data = self.GetDataFromDateBase( "SP_LogoutSaty", uID )
                    lobby_msg.vipgqexitnum.append(data[0][0])
                else:
                    lobby_msg.vipgqexitnum.append(exitdata[1])

        for exitdata in g_new_exit_type:
            if (qudao != 6) or (exitdata[0] != 3):
                lobby_msg.newexittype.append(exitdata[0])
                lobby_msg.newexitnum.append(exitdata[1])

        for exitdata in g_old_exit_type:
            if (qudao != 6) or (exitdata[0] != 3):
                lobby_msg.oldexittype.append(exitdata[0])
                if exitdata[0] == 9:
                    data = self.GetDataFromDateBase( "SP_LogoutSaty", uID )
                    lobby_msg.oldexitnum.append(data[0][0])
                else:
                    lobby_msg.oldexitnum.append(exitdata[1])

        #注册天数
        data = self.GetDataFromDateBase( "SP_UserRegisterDay", uID )
        lobby_msg.registerday = data[0][0]

        #比赛场奖励
        data = self.GetDataFromDateBase( "SP_CompetitonReward", uID )
        lobby_msg.bsmc = -1
        #print( "jl data = " )
        #print data
        if data:
            lobby_msg.bsmc = data[0][0]
            if data[0][0]  != -1:
                lobby_msg.bsmc = data[0][1]
                lobby_msg.bsjltype.append(1)
                lobby_msg.bsjlnum.append(data[0][2])

        endtime = time.mktime(time.strptime("2015-7-31 23:59:59",'%Y-%m-%d %H:%M:%S'))
        if (curtime <= endtime) and (vervalue >= 301) and (vervalue < 320):
            #新版活动
            if(qudao!=88):
                lobby_msg.activetips.title = "【升级送iphone6】".decode("gbk").encode("utf-8")
                lobby_msg.activetips.content = "即日起，首次升级到最新版本的玩家，奖励1万金币+5抽奖券+1兑奖券。截止7.31号更会抽取3名玩获赠iphone6！".decode("gbk").encode("utf-8")
                actTail = lobby_msg.activedetail.add()
                actTail.title = "【升级送iphone6】".decode("gbk").encode("utf-8")
                actTail.time = "7月4日-7月6日".decode("gbk").encode("utf-8")
                actTail.distxt = "老板有钱任性，iphone6随便一拿就是3部！今天开始，凡是第一次升级到最新版本100%送你“1万金币+5抽奖券+1兑奖券”，截止7.31号更会抽取3名玩获赠iphone6！老道掐指一算，哥，你今天有中I6的命啊，赶快升级吧。".decode("gbk").encode("utf-8")
                actTail.introduction = "老板有钱任性，iphone6随便一拿就是3部。1万金币+5抽奖券+1兑奖券直接就送给你啊！赶快升级版本吧".decode("gbk").encode("utf-8")
                actTail.picaddress = "http://211.155.89.98:9000/active18.png"             
            else:
                lobby_msg.activetips.title = "【牛牛也疯狂】".decode("gbk").encode("utf-8")
                lobby_msg.activetips.content = "即日起,首充就送双倍游戏币、,互动道具,金牛".decode("gbk").encode("utf-8")            
                actTail = lobby_msg.activedetail.add()
                actTail.title = "【牛牛也疯狂】".decode("gbk").encode("utf-8")
                actTail.time = "7月4日-7月21日".decode("gbk").encode("utf-8")
                actTail.distxt = "即日起,首充就送双倍游戏币、互动道具,金牛".decode("gbk").encode("utf-8")
                actTail.introduction = "即日起,首充就送双倍游戏币、互动道具,金牛".decode("gbk").encode("utf-8")
                actTail.picaddress = "http://211.155.89.98:9000/active18.png"
            #actTail = lobby_msg.activedetail.add()
            #actTail.title = "【限时充值活动】".decode("gbk").encode("utf-8")
            #actTail.time = "4月1日-4月6日".decode("gbk").encode("utf-8")
            #actTail.distxt = "愚人节，不愚人！一起来斗牛~4月1日—4月6日，用支付宝充值任意金额即赠金币，最高可获50倍奖励！多充几次，多得几次，快来享受成为土豪的感觉吧！".decode("gbk").encode("utf-8")
            #actTail.picaddress = "http://211.155.89.98:9000/active6.png"
            #actTail.introduction = "愚人节，不愚人！4月1日—4月6日，用支付宝充值任意金额即赠金币，最高可获50倍奖励！".decode("gbk").encode("utf-8")

        endtime = time.mktime(time.strptime("2015-5-10 23:59:59",'%Y-%m-%d %H:%M:%S'))
        if (curtime <= endtime) and (vervalue >= 301):
            actTail1 = lobby_msg.activedetail.add()
            actTail1.title = "【玩牛牛，得三个月VIP特权】".decode("gbk").encode("utf-8")
            actTail1.time = "5月1日—5月10日".decode("gbk").encode("utf-8")
            actTail1.distxt = "股市牛，牛牛得更得牛气冲天！5月1日—5月10日，在比赛场进行游戏，累计赢取金币最多的玩家可获得三个月VIP特权。名单将在5月15日中午12点前公布。一起来玩牛牛吧~".decode("gbk").encode("utf-8")
            actTail1.introduction = "5月1日—5月10日，通过“比赛场”游戏，累计赢取金币最多的玩家可获得三个月VIP特权。".decode("gbk").encode("utf-8")
            actTail1.picaddress = "http://211.155.89.98:9000/active20.png"
        #快速开始
        lobby_msg.ksroomgold.append(1000)
        lobby_msg.ksroomgold.append(200000)
        lobby_msg.ksroomgold.append(2000000)
        lobby_msg.ksroomgold.append(-1)

        #当天比赛输赢金币数
        data = self.GetDataFromDateBase( "SP_CompetitionWinScore", uID )
        if data:
            lobby_msg.bsgoldnum = data[0][0]

        #传版本号到服务器
        if vervalue == 2:
            #print( "vervalue = %d" %(vervalue) )
            self.GetDataFromDateBase( "SP_LoginVersion", uID, 200 )
        else:
            #print( "---------vervalue = %d" %(vervalue) )
            self.GetDataFromDateBase( "SP_LoginVersion", uID, vervalue )

        data = self.GetDataFromDateBase( "SP_CompetitionNotice" )
        if data:
            for d in data:
                lobby_msg.nickname.append(d[0].encode("utf-8"))
                lobby_msg.jlgold.append(d[1])
        lobby_msg.productaddr = "http://211.155.89.187:8100"
        lobby_msg.hasrank = 1
        print g_nodisp_ylt
        for d in g_nodisp_ylt:
            if d == qudao:
                lobby_msg.hasylt = 0

        for d in g_normalPay:
            if d== douID:
                lobby_msg.hasylt = 0
        for d in g_nodisp_rank:
            if d == qudao:
                lobby_msg.hasrank = 0
        lobby_msg.ziboflag = 1
        lobby_msg.zibogold = 10000
        lobby_msg.jfexchangeflag = 1

        #腾讯mid
        umid = self.get_argument( "mid", None )
        if umid != None:
            self.GetDataFromDateBase( "TX_InsertUserMid", uID, umid )
        #print( "lobby_msg.malldistype=%d" %(lobby_msg.malldistype) )

        #荣誉
        lobby_msg.honordata.curheroid = 0
        lobby_msg.honordata.curtaskid = 0
        data = self.GetDataFromDateBase( "List_ToGetHeroFlag", uID )
        if data and (data[0][0] != -1):
            for d in data:
                herohonor = lobby_msg.honordata.herohonor.add()
                herohonor.hid = d[0]
                herohonor.num = d[1]
                if d[2] == 1:
                    lobby_msg.honordata.curheroid = d[0]

        data = self.GetDataFromDateBase( "List_ToGetHonorflag", uID )
        if data and (data[0][0] != -1):
            for d in data:
                herohonor = lobby_msg.honordata.taskhonor.add()
                herohonor.hid = d[0]
                herohonor.num = d[1]
                if d[2] == 1:
                    lobby_msg.honordata.curtaskid = d[0]

        testFlg=1;
        utype=0;


        for d in g_normalPay:
            if d== douID:
                utype=200;
        #OXTRACE(LOG_FILE,str(testFlg)+str(smsAmount))

        if(qudao==88):
            """
             data1 = self.GetDataFromDateBase( 'Charge_IosGiftContent', uID, 1,0, )
             if(data1):
                 OXTRACE(LOG_FILE,"in this")
                 usertype=data1[0][0]
                 data=data1;
                 if(usertype%100!=1):
                     data = self.GetDataFromDateBase( 'Charge_IosGiftContent', uID, 1,6 )

                 lobby_msg.gifts.usertype=data[0][0]
                 if(lobby_msg.gifts.usertype<100):
                     lobby_msg.gifts.usertype=lobby_msg.gifts.usertype+200;
                 lobby_msg.gifts.amount=data[0][1]
                 if(lobby_msg.gifts.amount==smsAmount):
                     lobby_msg.gifts.paytype=0
                 else:
                     lobby_msg.gifts.paytype=1
                 lobby_msg.gifts.productid=data[0][2]
                 for i in range(3,10,1):
                     lobby_msg.gifts.giftvaule.append(data[0][i])
                 for d in data[0]:
                     OXTRACE(LOG_FILE,d)
                 """
        elif(testFlg and smsAmount>0 and qudao!=7):
            data = self.GetDataFromDateBase( 'Charge_GiftContent', uID, 1,smsAmount )
            if(data):
                #OXTRACE(LOG_FILE,"in this")
                lobby_msg.gifts.usertype=data[0][0]
                if(lobby_msg.gifts.usertype<100):
                    lobby_msg.gifts.usertype=lobby_msg.gifts.usertype+utype;
                lobby_msg.gifts.amount=data[0][1]
                if(lobby_msg.gifts.amount==smsAmount):
                    lobby_msg.gifts.paytype=0
                else:
                    lobby_msg.gifts.paytype=1
                lobby_msg.gifts.productid=data[0][2]
                for i in range(3,8,1):
                    lobby_msg.gifts.giftvaule.append(data[0][i])
                for d in data[0]:
                    OXTRACE(LOG_FILE,d)
        data = self.GetDataFromDateBase( 'Charge_recordFirstInRoom', uID,0)
        if(data):
            lobby_msg.firstInRoom=data[0][0];

        #捷报
        data = self.GetDataFromDateBase( 'List_GetUserList_Last', uID )
        print  data
        if data:
            for d in data:
                rankingdata = lobby_msg.userrankingdata.add()
                rankingdata.index = d[0]
                rankingdata.nickname = d[2].encode("utf-8")
                rankingdata.num = d[3]
                rankingdata.headerid = d[4]
                rankingdata.order = d[5]

        #排行榜
        #data = (("aa",500),("bb",100),("vv",122),("dd",300) )
        data = self.GetDataFromDateBase( 'List_GetAllList_Last' )
        if data:
            for d in data:
                rankingdata = lobby_msg.rankingdata.add()
                rankingdata.index = d[0]
                rankingdata.nickname = d[2].encode("utf-8")
                rankingdata.num = d[3]
                rankingdata.headerid = d[4]


        if(qudao==88):
            if(vervalue>325):	#ios提测模式
                lobby_msg.iosadress="https://sandbox.itunes.apple.com/verifyReceipt"
                lobby_msg.paytype=1
                lobby_msg.hasrank = 0
                lobby_msg.hasylt = 0
            else:
                lobby_msg.iosadress="https://buy.itunes.apple.com/verifyReceipt"
                lobby_msg.paytype=3
                lobby_msg.hasrank = 1
                lobby_msg.hasylt = 1
            
            lobby_msg.ioscalladress="iapbilling"
            
            OXTRACE(LOG_FILE,lobby_msg.paytype)
        #ddzinfo
        if 1:
            lobby_msg.ddzinfo.addr = "http://lapk.cmge.com/zrddzmty_v1.3.0_42100.apk"
            lobby_msg.ddzinfo.packagename = "com.zrddz.mty.cmge"
        retstr = lobby_msg.SerializeToString()
        #print( "len(retstr)=%d", len(retstr) )
        self.write(  retstr )





    #充值提醒查询
    def SelectRechange( self, uID ):
        #print( "select recharge infomation" )
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_PayOrderLatestRecord', uID )
        data = sqlhandler.sql_fetchall()
        return data


    #查询金牛重量
    def SelectOXWeight( self, uID ):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_GetRechargeFund', uID )
        data = sqlhandler.sql_fetchall()
        #print( data )
        return data

    #查询用户是否充值过
    def SelectClientRecharge( self, uID ):
        #print( "SelectClientRecharge" )
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_UserPayFunLog', uID )
        data = sqlhandler.sql_fetchall()
        return data[0][0]

    def getoxgold(self, uID, goldnum ):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        utoken = int(self.get_argument( "token", 0 ))

        #print( uID )
        #print( goldnum  )
        #print( utoken  )
        curtime = long(time.time())
        sqlhandler.sql_callproc( 'SP_TaurusDayPrsent', uID, goldnum, utoken, curtime )
        data = sqlhandler.sql_fetchall()
        return data

    #获取系统喇叭
    def getoxspeaker(self,qudao):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        if(qudao!=88):
            sqlhandler.sql_callproc( 'SP_GetSystemSpeakerData' )
        else:
            sqlhandler.sql_callproc( 'SP_GetSystemSpeakerData2' )
        data = sqlhandler.sql_fetchall()
        return data

    #连续登入天数
    def getdaynum( self, uID ):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_LogonSevDays', uID )
        data = sqlhandler.sql_fetchall()
        return data

    #查询奖券数量
    def getlottery( self, uID ):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_VoucherCount', uID )
        data = sqlhandler.sql_fetchall()
        return data[0][0]

    #获取用户水果信息
    def getuserfruit(self, uID):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_GetUserFruit', uID )
        data = sqlhandler.sql_fetchall()
        return data

    #是否是首次登入
    def GetFirstLogonGods(self, uID):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_FirstLogin', uID )
        data = sqlhandler.sql_fetchall()
        return data

    #写入抽奖券
    def WriteCJQData(self, uID, token, *cjqdata ):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        #print( "cjqdata = %d %d %d %d %d %d %d" %(cjqdata[0][0], cjqdata[0][1], cjqdata[0][2],cjqdata[0][3],cjqdata[0][4],cjqdata[0][5], token) )
        sqlhandler.sql_callproc( 'SP_DrawCard_write', uID, cjqdata[0][0], cjqdata[0][1], cjqdata[0][2],cjqdata[0][3],cjqdata[0][4],cjqdata[0][5], token )
        data = sqlhandler.sql_fetchall()
        #print data
        return data


    #获取抽奖券数量
    def GetCJQData(self, uID):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_DrawCard_read', uID)
        data = sqlhandler.sql_fetchall()
        #print data
        return data

    #获取生日
    def GetBirthday(self, uID):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_User_Birthday_Read', uID)
        data = sqlhandler.sql_fetchall()
        #print data
        return data

    #获取生日
    def GetGoldBean(self, uID):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_JinDow_Get', uID)
        data = sqlhandler.sql_fetchall()
        #print data
        return data

    def GetDataFromDateBase(self, spName, *args):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( spName, *args)
        data = sqlhandler.sql_fetchall()
        #print data
        return data

    def compute_etag(self):
        return None


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
                oxweight = 2
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
                            #print(" index = %d oxweight = %d" %(index, oxweight))
                            break;
                    elif index == i:
                        oxweight = oxweight + (rechargeNum - wsection[i])*wxishu[i]
                        #print(" index = %d oxweight = %d" %(index, oxweight))
                        break
                    #print( "oxweight = %d " %(oxweight) )
            else:
                return ( 0, 0 )
            #print ( "---------------------" )
        #通过重量计算金币数
        if gettime == 0 :
            return ( oxweight, 0 )

        #测试用
        GETTIME = 600
        #GETTIME = 10
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

        return ( oxweight, oxgold )

