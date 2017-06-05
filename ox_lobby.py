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

#������ͨ��
from serverthread import ServerSendThread
from serverthread import g_wg_msg

#ȫ�ֱ������� QQ �� ��������ζ�ȡ�ļ�
ox_help_qq = None
ox_help_mail = None
ox_award_totalgold = 0
ox_award_reqgold = 0
#ȫ�ֱ��������̳���Ϣ,����ÿ���û���Ҫ�����ݿ� ����̳����ݷ���������Ҫ����WEB������
g_goods_msg = OX_MALL_GOODS_DATA()
g_goods_msg_init_flag = 0
g_mallbillingnum = 0
g_otherbillingnum = 0
g_birthday = 0
#adress: /lobby?id=XXXXXXXXX
# /lobby?id=XXXXX&platform=X
#360�û������ַ:platform=1
#��ȡ��ţ�Ľ��
#adress:/lobby?id=XXXXXXXXX&token=1&gold=xxxxxx

# 1. ����齱ȯ��һ���汾���Ե�����
# /lobby?id=XXXXX&qudao=X&birthday=1&ver=1
# 2. ����̳ǽ�
# /lobby?id=XXXXX&qudao=X&birthday=1&ver=1&mall=2
# 2.0�İ汾ver=2
# /lobby?id=XXXXX&qudao=X&birthday=1&ver=2&mall=2
# 3. ���������Ͱ汾���������̳���Ϣ ver�ɴ���200��λ�����,��汾��2.0��200 2.11��211
# /lobby?id=XXXXX&qudao=X&birthday=1&ver=200&mall=2
# 4. ������Ϸid  Ĭ��Ϊ1 ������Ϊ 2
# /lobby?id=XXXXX&qudao=X&birthday=1&ver=200&mall=2&gameid=x
# 5. ��Ѷ��������mid����
# /lobby?id=XXXXX&qudao=X&birthday=1&ver=200&mall=2&gameid=x&mid=xxxxxxxxxx
# 6. ���붹ID
# /lobby?id=XXXXX&qudao=X&birthday=1&ver=200&mall=2&gameid=x&mid=xxxxxxxxxx&douid=xxxx

#������������
#�׳�˵��
#type: 1��ţ  2VIP  3�齱�� 4���ƿ� 5���ƿ� 6��ɱ�� 7��������  8��Ϸ��ʾ   9����������    10���ͽ��  11����ȯ  12��   13vip���  14Ԫ��
#num:   ��         ��    ��               ��              ��                ��               ��                    ��                       ��                               ��                     ��               ��            ��                ��
g_sc_data = ( (1, 7), (7, 7), (8,7),(13,7) )


#������
#kctype----1:��������  2:�м�����  3:�߼���  4:���߳� 5:������
#kcjes-----��Ӧ���
g_kc_data = ( (1,(2)), (2,(4)), (3,(6)), (4,(6)), (5,(6)) )
g_kc_v300_data = ( (1,(4)), (2,(6)), (3,(8)), (4,(6)), (5,(6)) )
#�˳�����  vip���û�  vip���û� vip�����û� ����  ����
#��������Ҫ���ý����
#type: 1��ţ  2VIP  3�齱�� 4���ƿ� 5���ƿ� 6��ɱ�� 7��������  8��Ϸ��ʾ   9����������    10���ͽ��  11����ȯ  12��   13vip���
#num:   ��     ��    ��       ��      ��      ��        ��          ��           ��              ��         ��       ��        ��
g_vip_new_exit_type =   ( (13,1), (11,5), (3,1) )
g_vip_old_exit_type =   ( (13,1), (7,20), (8,0), (3,1) )
g_vip_gq_exit_type =   ( (9,1000), (3,1) )
g_new_exit_type = ( (1,1), (11,5), (3,1) )
g_old_exit_type =   ( (9,1000), (3,1) )

#��Щ��������ʾ������
g_nodisp_ylt = ( 0,11,  17, 19, 14, 22, 26, 4,88 )
g_nodisp_rank=(88,)


#��Щ����������ʾ������ʾ
g_normalPay=(99967636,99977400)#douid
g_normalPay_qudao=(999,998)
g_noyltDouId=(99967636,99977400 )#douid
#ʹ�ó�ֵ��ʽ
g_sms_fee_qudao = ( 0, )
g_third_fee_qudao = ( 0, )

class OxLobby(tornado.web.RequestHandler):
    #def __init__(self):
        #config = ConfigParser.ConfigParser()
        #config.readfp(open("ox.ini"))
        #mallbillingnum = config.get( "billing", "qq" )
        #otherbillingnum = config.get( "billing", "mail" )
        #pass

    #������Ϸ������ͨ���߳�
    g_wg_msg.setDaemon(True)
    g_wg_msg.setName( "ox-wg-msg" )
    g_wg_msg.start()

    #��������
    def __init_msg__(self):
        global ox_help_qq
        global ox_help_mail
        global g_mallbillingnum
        global g_otherbillingnum
        global g_birthday

        if ox_help_qq is None:
            #��ȡ���ݿ���Ϣ
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
        smsAmount=int(self.get_argument( "maxAmount", 0 ))#ͨ�������

        douID = int( self.get_argument( "douid", "0" ) )
        if smsAmount>8:
            smsAmount=8
        #��ţ�����ȡ
        if token != 0:
            getgold = OX_LOBBY_GET_GOLD()
            getgold.bsuccess = -1;
            oxgoldnum = 0
            #��������ڼ���һ��
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

        #�����Ǵ�����ȡ����
        #print( "userID = %d" %(uID) )
        global ox_award_totalgold
        global ox_award_reqgold
        if ox_award_totalgold == 0:
            config = ConfigParser.ConfigParser()
            config.readfp(open("ox.ini"))
            ox_award_totalgold = int( config.get( "award", "totalgold" ) )
            ox_award_reqgold = int( config.get( "award", "reqgold" ) )
        #��ʼ��������Ϣ
        self.__init_msg__()

        lobby_msg.totalgold = ox_award_totalgold
        lobby_msg.reqgold = ox_award_reqgold

        #��ȡ�û��Ƿ��״γ�ֵ
        rechargenum = self.SelectClientRecharge(uID)
        if rechargenum > 0:
            lobby_msg.isrecharge = 1
        else:
            lobby_msg.isrecharge = 0

        #�Ƿ���ʾQQ
        if rechargenum >= 5 :
            if ox_help_qq.strip() != '':
                lobby_msg.disp = 1
                lobby_msg.qq = ox_help_qq
                lobby_msg.mail = ox_help_mail

        #��ʼ���̳���Ʒ��Ϣ
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
                        #˵����ʽ   ��������Ʒ����   �һ�˵��   �ͻ�����ʾ����
                        # 1 Ԫ���һ����	1 - 4
                        # 2 ����Ҷһ�Ԫ�� 8 - 10
                        # 3 Ԫ���һ�����	6
                        # 4 Ԫ���һ�VIP	5
                        # 5 ��Ҷһ�T�˿�	11
                        # 6 ��Ҷһ���   12
                        # 7 ��Ҷһ�������   13
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
                        #Ԫ������
                        goods.num1 = d[2]
                        #�һ���������
                        goods.num2 = d[3]

        #��ȡ�µ���Ʒ����
        if (vervalue >= 200) or (gameid == 2):
            data = self.GetDataFromDateBase( 'SP_ShoppingGiftInfo', qudao, 310 )
            #print( "SP_ShoppingGiftInfo" , data,  qudao, vervalue )
            if data:
                #�°汾ʹ���µ��̳�
                if(qudao==88):
                    lobby_msg.malldistype = 2
                    lobby_msg.mall2data.czyhnum.append( 8 )
                    lobby_msg.mall2data.czyhnum.append( 78 )
                    lobby_msg.mall2data.yhratenum = 10
                    lobby_msg.mall2data.yhtips.append( "27����Ϸ��".decode("gb2312").encode( "utf-8" ) )
                    lobby_msg.mall2data.yhtips.append( "(��18Ԫ\nԭ��27)".decode("gb2312").encode( "utf-8" )  )
                else:
                    lobby_msg.malldistype = 2
                    lobby_msg.mall2data.czyhnum.append( 8 )
                    lobby_msg.mall2data.czyhnum.append( 78 )
                    lobby_msg.mall2data.yhratenum = 10
                    lobby_msg.mall2data.yhtips.append( "25����+VIP".decode("gb2312").encode( "utf-8" ) )
                    lobby_msg.mall2data.yhtips.append( "(�ۼ�20\nԭ��33)".decode("gb2312").encode( "utf-8" )  )

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

        #��ȡ��ֵ��Ϣ
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
                    #��ֵ״̬
                    if d[0] == '\x01':
                        record.status = 1
                    else:
                        record.status = 0

                    #�Ƿ��״γ�ֵ
                    if d[4] == '\x01':
                        record.bisfirst = 1
                    else:
                        record.bisfirst = 0

                    record.weathnum = d[2]

        #��ȡ����
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
        #����Ҫ�������Ͱ汾,����д�ļ���
        curtime = int(time.time())
        endtime = time.mktime(time.strptime("2015-7-31 23:59:59",'%Y-%m-%d %H:%M:%S'))
        if (curtime <= endtime) and (vervalue < 320) and (qudao!=88):
            lobby_msg.actives = "��������iphone6��\n�������״����������°汾����ң�����1����+5�齱ȯ+1�ҽ�ȯ����ֹ7.31�Ÿ����ȡ3�������iphone6��\n���ͷ���\n�ͷ��绰��028-69605999���ͷ�QQ��2990262726��".decode("gbk").encode("utf-8")
        else:
            #Ĭ�Ϲ���
            lobby_msg.actives = "���ͷ���\n�ͷ�QQ��2962286122��".decode("gbk").encode("utf-8")

        #��ȡ��ţ����
        #�°汾��1������ȡ
        lobby_msg.oxget = -2
        lobby_msg.oxweight,  lobby_msg.oxgold = self.ComputerOxWeight( uID )
        if lobby_msg.oxweight > 0:
            if vervalue >= 2:
                if lobby_msg.oxweight > 0:
                    lobby_msg.oxget = 1
                else:
                    lobby_msg.oxget = 0
            else:
                #�ɰ汾��0������ȡ
                if lobby_msg.oxgold > 0:
                    lobby_msg.oxget = 0
                else:
                    lobby_msg.oxget = -1


        #print( "-------------" )
        #print lobby_msg.oxweight
        #print lobby_msg.oxgold
        #print( "-------------" )
        #ϵͳ����
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

        #�������뽱��  �����¾ɰ汾
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

        #�Ƿ����״ε��� �������ӽ�ȯ
        data = self.GetFirstLogonGods( uID )
        #print "self.GetFirstLogonCjq"
        #print data
        vipGrade = 0
        lobby_msg.firstlogon = 0
        #�״ε���
        if data[0][0] == 1:
            lobby_msg.firstlogon = 1

        #VIP����
        if data[0][1] == 1:
            vipGrade = data[0][2]

        if qudao != 6 :
            #��ȯ����
            lobby_msg.lotterynum = self.getlottery( uID )
            #�״ε���
            if data[0][0] == 1:
                lobby_msg.csqnum = data[0][3]
                cjqdata = [ 0 ]*6
                m_cjq = OxCJQModual()
                #�״ε���
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
                #�����״ε���
                data = self.GetCJQData( uID )
                for i in range (0, 6):
                    #print ( "add cjq %d  %d" %( i, data[0][i] ) )
                    lobby_msg.cjqTotalNum = lobby_msg.cjqTotalNum + data[0][i+1]
                    #print lobby_msg.cjqTotalNum

        if g_birthday == 1:
            #��ȡ����
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

        #��ȡ������
        data = self.GetGoldBean(uID)
        if data:
            lobby_msg.goldbean = data[0][0]
        if vervalue == 0:
            lobby_msg.cjqGetNum = 0

        #��ֵ��ʽ����
        lobby_msg.smsfeeflag = 3
        for d in g_sms_fee_qudao:
            if qudao == d :
                lobby_msg.smsfeeflag = 0
                break
        #�Ƿ�
        for d in g_third_fee_qudao:
            if qudao == d :
                lobby_msg.smsfeeflag = 3
                break

        #�׳�����
        if lobby_msg.smsfeeflag == 3:
            lobby_msg.scjes.append(1)#����
            lobby_msg.scjes.append(1)#����
            lobby_msg.scjes.append(1)#�м�
            lobby_msg.scjes.append(1)#�߼�
            lobby_msg.scjes.append(1)#թ��ţ
            lobby_msg.scjz = 7
        else:
            lobby_msg.scjes.append(6)#����
            lobby_msg.scjes.append(2)#����
            lobby_msg.scjes.append(4)#�м�
            lobby_msg.scjes.append(6)#�߼�
            lobby_msg.scjes.append(4)#թ��ţ
            lobby_msg.scjz = 5

        #�׳�˵��
        #sclptype: 1��ţ  2VIP  3�齱�� 4���ƿ� 5���ƿ� 6��ɱ��
        #sclpnum:  ͷ     ��    ��       ��      ��      ��
        #print( "sc data------------" )
        for i in range( 0, len(g_sc_data) ):
            #print( "i = %d type=%d  num=%d" %(i, g_sc_data[i][0], g_sc_data[i][1]) )
            lobby_msg.sclptype.append(g_sc_data[i][0])
            lobby_msg.sclpnum.append(g_sc_data[i][1])
        #print( "sc data------------" )

        #����������
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
        #�˳�����
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

        #ע������
        data = self.GetDataFromDateBase( "SP_UserRegisterDay", uID )
        lobby_msg.registerday = data[0][0]

        #����������
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
            #�°�
            if(qudao!=88):
                lobby_msg.activetips.title = "��������iphone6��".decode("gbk").encode("utf-8")
                lobby_msg.activetips.content = "�������״����������°汾����ң�����1����+5�齱ȯ+1�ҽ�ȯ����ֹ7.31�Ÿ����ȡ3�������iphone6��".decode("gbk").encode("utf-8")
                actTail = lobby_msg.activedetail.add()
                actTail.title = "��������iphone6��".decode("gbk").encode("utf-8")
                actTail.time = "7��4��-7��6��".decode("gbk").encode("utf-8")
                actTail.distxt = "�ϰ���Ǯ���ԣ�iphone6���һ�þ���3�������쿪ʼ�����ǵ�һ�����������°汾100%���㡰1����+5�齱ȯ+1�ҽ�ȯ������ֹ7.31�Ÿ����ȡ3�������iphone6���ϵ���ָһ�㣬�磬���������I6���������Ͽ������ɡ�".decode("gbk").encode("utf-8")
                actTail.introduction = "�ϰ���Ǯ���ԣ�iphone6���һ�þ���3����1����+5�齱ȯ+1�ҽ�ȯֱ�Ӿ��͸��㰡���Ͽ������汾��".decode("gbk").encode("utf-8")
                actTail.picaddress = "http://211.155.89.98:9000/active18.png"             
            else:
                lobby_msg.activetips.title = "��ţţҲ���".decode("gbk").encode("utf-8")
                lobby_msg.activetips.content = "������,�׳����˫����Ϸ�ҡ�,��������,��ţ".decode("gbk").encode("utf-8")            
                actTail = lobby_msg.activedetail.add()
                actTail.title = "��ţţҲ���".decode("gbk").encode("utf-8")
                actTail.time = "7��4��-7��21��".decode("gbk").encode("utf-8")
                actTail.distxt = "������,�׳����˫����Ϸ�ҡ���������,��ţ".decode("gbk").encode("utf-8")
                actTail.introduction = "������,�׳����˫����Ϸ�ҡ���������,��ţ".decode("gbk").encode("utf-8")
                actTail.picaddress = "http://211.155.89.98:9000/active18.png"
            #actTail = lobby_msg.activedetail.add()
            #actTail.title = "����ʱ��ֵ���".decode("gbk").encode("utf-8")
            #actTail.time = "4��1��-4��6��".decode("gbk").encode("utf-8")
            #actTail.distxt = "���˽ڣ������ˣ�һ������ţ~4��1�ա�4��6�գ���֧������ֵ���������ң���߿ɻ�50����������伸�Σ���ü��Σ��������ܳ�Ϊ�����ĸо��ɣ�".decode("gbk").encode("utf-8")
            #actTail.picaddress = "http://211.155.89.98:9000/active6.png"
            #actTail.introduction = "���˽ڣ������ˣ�4��1�ա�4��6�գ���֧������ֵ���������ң���߿ɻ�50��������".decode("gbk").encode("utf-8")

        endtime = time.mktime(time.strptime("2015-5-10 23:59:59",'%Y-%m-%d %H:%M:%S'))
        if (curtime <= endtime) and (vervalue >= 301):
            actTail1 = lobby_msg.activedetail.add()
            actTail1.title = "����ţţ����������VIP��Ȩ��".decode("gbk").encode("utf-8")
            actTail1.time = "5��1�ա�5��10��".decode("gbk").encode("utf-8")
            actTail1.distxt = "����ţ��ţţ�ø���ţ�����죡5��1�ա�5��10�գ��ڱ�����������Ϸ���ۼ�Ӯȡ���������ҿɻ��������VIP��Ȩ����������5��15������12��ǰ������һ������ţţ��~".decode("gbk").encode("utf-8")
            actTail1.introduction = "5��1�ա�5��10�գ�ͨ��������������Ϸ���ۼ�Ӯȡ���������ҿɻ��������VIP��Ȩ��".decode("gbk").encode("utf-8")
            actTail1.picaddress = "http://211.155.89.98:9000/active20.png"
        #���ٿ�ʼ
        lobby_msg.ksroomgold.append(1000)
        lobby_msg.ksroomgold.append(200000)
        lobby_msg.ksroomgold.append(2000000)
        lobby_msg.ksroomgold.append(-1)

        #���������Ӯ�����
        data = self.GetDataFromDateBase( "SP_CompetitionWinScore", uID )
        if data:
            lobby_msg.bsgoldnum = data[0][0]

        #���汾�ŵ�������
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

        #��Ѷmid
        umid = self.get_argument( "mid", None )
        if umid != None:
            self.GetDataFromDateBase( "TX_InsertUserMid", uID, umid )
        #print( "lobby_msg.malldistype=%d" %(lobby_msg.malldistype) )

        #����
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

        #�ݱ�
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

        #���а�
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
            if(vervalue>325):	#ios���ģʽ
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





    #��ֵ���Ѳ�ѯ
    def SelectRechange( self, uID ):
        #print( "select recharge infomation" )
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_PayOrderLatestRecord', uID )
        data = sqlhandler.sql_fetchall()
        return data


    #��ѯ��ţ����
    def SelectOXWeight( self, uID ):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_GetRechargeFund', uID )
        data = sqlhandler.sql_fetchall()
        #print( data )
        return data

    #��ѯ�û��Ƿ��ֵ��
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

    #��ȡϵͳ����
    def getoxspeaker(self,qudao):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        if(qudao!=88):
            sqlhandler.sql_callproc( 'SP_GetSystemSpeakerData' )
        else:
            sqlhandler.sql_callproc( 'SP_GetSystemSpeakerData2' )
        data = sqlhandler.sql_fetchall()
        return data

    #������������
    def getdaynum( self, uID ):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_LogonSevDays', uID )
        data = sqlhandler.sql_fetchall()
        return data

    #��ѯ��ȯ����
    def getlottery( self, uID ):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_VoucherCount', uID )
        data = sqlhandler.sql_fetchall()
        return data[0][0]

    #��ȡ�û�ˮ����Ϣ
    def getuserfruit(self, uID):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_GetUserFruit', uID )
        data = sqlhandler.sql_fetchall()
        return data

    #�Ƿ����״ε���
    def GetFirstLogonGods(self, uID):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_FirstLogin', uID )
        data = sqlhandler.sql_fetchall()
        return data

    #д��齱ȯ
    def WriteCJQData(self, uID, token, *cjqdata ):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        #print( "cjqdata = %d %d %d %d %d %d %d" %(cjqdata[0][0], cjqdata[0][1], cjqdata[0][2],cjqdata[0][3],cjqdata[0][4],cjqdata[0][5], token) )
        sqlhandler.sql_callproc( 'SP_DrawCard_write', uID, cjqdata[0][0], cjqdata[0][1], cjqdata[0][2],cjqdata[0][3],cjqdata[0][4],cjqdata[0][5], token )
        data = sqlhandler.sql_fetchall()
        #print data
        return data


    #��ȡ�齱ȯ����
    def GetCJQData(self, uID):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_DrawCard_read', uID)
        data = sqlhandler.sql_fetchall()
        #print data
        return data

    #��ȡ����
    def GetBirthday(self, uID):
        sqlhandler = CMySQLPort.CMySQLPort()
        sqlhandler.sql_reset()
        sqlhandler.sql_callproc( 'SP_User_Birthday_Read', uID)
        data = sqlhandler.sql_fetchall()
        #print data
        return data

    #��ȡ����
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
        #��ǰʱ��
        curtime = long(time.time())
        #��ȡʱ��
        gettime = 0
        daymaxgold = 0
        #��ȡ��ţ����
        data = self.SelectOXWeight( uID )
        #0.25 * a + 0.2 * b + 0.15 * c + 0.1 * d + 0.05 *e + 0.01 *f
        #a,b,c,d,e�ֱ����������Ϊ0-20-40-60-80-100   100���ϵĲ��ֵĲ���ϵ��Ϊ0.01
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
        #ͨ��������������
        if gettime == 0 :
            return ( oxweight, 0 )

        #������
        GETTIME = 600
        #GETTIME = 10
        #print curtime
        #print gettime
        #print curtime - gettime
        #����һСʱ���н��
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

