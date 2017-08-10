# -*- coding: utf-8 -*-
'''
databaseにmap_id textを追加
documentsディレクトリを作成
'''
import datetime
from datetime import date
import sys
sys.path.append('./vendor')
import re
import os
import uuid

from PIL import Image
import io
import psycopg2
import urllib.parse as urlparse
import makeCalenderImage
import htmlParse
import makeSiori
import makeDescription
import fetch_googlemap_image
from flask import Flask, request, abort, send_file

days = {1:31,2:28,3:31,4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31}

from linebot import (
    LineBotApi, WebhookHandler,
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    JoinEvent,MessageEvent, PostbackEvent, TextMessage, TextSendMessage, MessageImagemapAction, ImagemapArea,ImageSendMessage, ImagemapSendMessage, BaseSize, \
    TemplateSendMessage, TemplateAction, ButtonsTemplate, CarouselTemplate, CarouselColumn, URITemplateAction, PostbackTemplateAction, MessageTemplateAction
)

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get('LINE_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))
url = urlparse.urlparse(os.environ.get('DATABASE_URL'))

dbname = url.path[1:]
user = url.username
password = url.password
host = url.hostname
port = url.port

lengths = {'１日':480,'半日':300}
columns = ['state', 'date', 'region', 'area', 'plan', 'move','year','month','user_id','group_id','length']
regions = ['#北海道','#関東','#関西','#九州・沖縄']
moves = {}
spots_dict = {}
styles = {'いろいろ楽しむ':1,'のんびり行こう':2,'文化を知りたい':3,'子どもとめぐる':4}
nextState = [1,4]

@app.route("/", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

def validMessage(event,cur,connection,id):
    message = event.message.text
    cur.execute("SELECT state FROM ryokochan WHERE group_id='{}';".format(id))
    state = cur.fetchone()[0]
    if state == 0:
        if re.match('[0-9]+/[0-9]+/[0-9]+',message) or message == "来月" or message == "先月":
            return True
    elif state == 1:
        if message[1:] in lengths:
            return True
    elif state == 2:
        if message in regions:
            return True
    elif state == 3:
        cur.execute("SELECT area FROM areas;")
        area = cur.fetchall()
        for i in range(len(area)):
            area[i] = area[i][0]
        if message[1:] in area:
            return True
    elif state == 4:
        cur.execute("SELECT area FROM ryokochan WHERE group_id='{}'".format(id))
        area = cur.fetchone()[0]
        cur.execute("SELECT move_way FROM areas WHERE area='{}'".format(area))
        move_way = cur.fetchone()[0]
        for i in range(move_way):
            cur.execute("SELECT way{} FROM areas WHERE area='{}'".format(i+1,area))
            way = cur.fetchone()[0]
            moves['{}'.format(way)] = i+1
        if message[1:] in moves:
            return True
    elif state == 5:
        if message[1:] in styles:
            return True
    elif state == 6:
        if message == '#はい' or message == '#いいえ':
            return True
        if message == '#地方選択から' or message == '#エリア選択から' or message == '#交通手段選択から' or message == '#旅行スタイル選択から':
            return True
    elif state == 7:
        cur.execute("SELECT map_id FROM ryokochan WHERE group_id='{}';".format(id))
        map_id = cur.fetchone()[0]
        spottxt = open('./documents/spots/spotdescription_{}.txt'.format(map_id),'r')
        spots = []
        for line in spottxt:
            words = line.split(' ')
            spots_dict[words[0]] = words[1]
            spots.append(words[0])
        spots.append('終わる')
        if message[1:] in spots:
            return True
    elif state == 8:
        if message == '#はい' or message == '#いいえ':
            return True
    elif state == 9:
        if message == '#地方選択から' or message == '#エリア選択から' or message == '#交通手段選択から' or message == '#旅行スタイル選択から' or message == '#もうプランは決まった！':
            return True
    elif state == 10:
        if message == '#はい' or message == '#いいえ':
            return True
    return False

def area_carousel(choice, region,baseNum):
    '''
        エリアの選択肢の配列を入力に受け取り、CarouselTemplateをreturnする。
        ただし受け取れる配列は最大15個
    '''
    thumbnail_url_base = 'https://' + request.host + '/images/area_thumbnail/'
    thumbnail_url = None
    n_choice = len(choice)

    if n_choice % 3 == 1:
        choice.append(' ')
        choice.append(' ')
    elif n_choice % 3 == 2:
        choice.append(' ')

    columns = []
    i = 0

    # 選択肢している地方によってサムネイルのリンクを取得
    if region == '関東':
        thumbnail_url_base = thumbnail_url_base + 'kanto/kanto'
    elif region == '関西':
        thumbnail_url_base = thumbnail_url_base + 'kansai/kansai'
    elif region == '北海道':
        thumbnail_url_base = thumbnail_url_base + 'hokkaido/hokkaido'
    elif region == '九州・沖縄':
        thumbnail_url_base = thumbnail_url_base + 'kyushu/kyushu'
    else:
        thumbnail_url_base = None

    while n_choice > 0:
        if thumbnail_url_base is not  None:
            thumbnail_url = thumbnail_url_base + str(i+1+baseNum) + '.jpg/' + uuid.uuid4().hex
        actions = []

        if region == '関西':
            for j in range(3):
                actions.append(
                    MessageTemplateAction(
                        label='{}'.format(choice[i*3+j]),
                        text='#{}'.format(choice[i*3+j]),
                    )
                )
            columns.append(
                CarouselColumn(
                    thumbnail_image_url=thumbnail_url,
                    title='どこに行きまっか？',
                    text='行きたいエリアを選んでな！',
                    actions=actions,
                )
            )
        else:
            for j in range(3):
                actions.append(
                    MessageTemplateAction(
                        label='{}'.format(choice[i*3+j]),
                        text='#{}'.format(choice[i*3+j]),
                    )
                )
            columns.append(
                CarouselColumn(
                    thumbnail_image_url=thumbnail_url,
                    title='いいね！！具体的には？',
                    text='行きたいエリアを選んでね！',
                    actions=actions,
                )
            )
        n_choice -= 3
        i += 1

    if region == '関西':
        res = TemplateSendMessage(
                alt_text='行きたいエリアを選んでね！',
                template=CarouselTemplate(columns=columns)
                )
    else:
        res = TemplateSendMessage(
                alt_text='行きたいエリアを選んでな！',
                template=CarouselTemplate(columns=columns)
                )
    return res

def spot_carousel(choice):
    n_choice = len(choice)

    if n_choice % 3 == 1:
        choice.append(' ')
        choice.append(' ')
    elif n_choice % 3 == 2:
        choice.append(' ')

    columns = []
    i = 0

    while n_choice > 0:
        actions = []
        for j in range(3):
            actions.append(
                MessageTemplateAction(
                    label='{}'.format(choice[i*3+j]),
                    text='#{}'.format(choice[i*3+j]),
                )
            )
        columns.append(
            CarouselColumn(
                title='どのスポットの説明がみたいかな？',
                text=' ',
                actions=actions,
            )
        )
        n_choice -= 3
        i += 1
        res = TemplateSendMessage(
                alt_text='説明が見たいスポットを選んでね！',
                template=CarouselTemplate(columns=columns)
                )
    return res

def isPast(year,month,day):
    if year < datetime.date.today().year:
        return True
    else:
        if month < datetime.date.today().month:
            return True
        else:
            if day < datetime.date.today().day:
                return True

    return False


def execute(event, id, isGroup=False):
    connection = psycopg2.connect(dbname=dbname,
                user=user,
                password=password,
                host=host,
                port=port)
    cur = connection.cursor()
    # グループ特有の処理：グループの各ユーザーに対し、最後の発言時間を保存しておく
    print(event.message.text)
    if isGroup:
        user_id = event.source.user_id
        now = datetime.datetime.today().strftime('%s')

        # group_id, user_id, 最終発言時間をDBに保存
        cur.execute("SELECT group_id FROM time_management WHERE group_id = '{}';".format(id))
        if cur.fetchone() is None:
            # 新しいグループの場合
            cur.execute("INSERT INTO time_management (group_id, user_id, last_remark) values('{}', '{}', {});".format(id, user_id, now))
            connection.commit()
        else:
            cur.execute("SELECT user_id FROM time_management WHERE group_id = '{}' AND user_id = '{}';".format(id, user_id))
            # 既存グループで新しいユーザーの場合
            if cur.fetchone() is None:
                cur.execute("INSERT INTO time_management (group_id, user_id, last_remark) values('{}', '{}', {});".format(id, user_id, now))
                connection.commit()
            # 既存グループで既存ユーザーの場合
            else:
                cur.execute("UPDATE time_management SET last_remark = {} WHERE group_id = '{}' AND user_id = '{}';".format(now, id, user_id))
                connection.commit()
        # Push message用
        if event.type == "message":
            if event.message.type == "text":
                if event.message.text == '#まだいる！':
                    line_bot_api.push_message(id, TextSendMessage(text='ありがとう！また言うね！'))
                    # DBの通知フラグをオンに変更
                    cur.execute("UPDATE time_management SET notification = TRUE WHERE group_id = '{}';".format(id))
                    connection.commit()
                elif event.message.text == '#もういらない！':
                    line_bot_api.push_message(id,TextSendMessage(text='わかった！もう言わない！'))
                    # DBの通知フラグをオフに変更
                    cur.execute("UPDATE time_management SET notification = FALSE WHERE group_id = '{}';".format(id))
                    connection.commit()


    if event.type == "message":
        if event.message.type == "text":
            if event.message.text == "もどる":
                cur.execute("SELECT user_id FROM ryokochan WHERE group_id = '{}';".format(id))
                user_id = cur.fetchone()[0]
                if user_id == event.source.user_id or isGroup == False:
                    cur.execute("SELECT state FROM ryokochan WHERE group_id = '{}';".format(id))
                    state = cur.fetchone()[0]
                    if state > 0:
                        state -= 1
                        cur.execute("UPDATE ryokochan SET state = {} WHERE group_id = '{}';".format(state, id))
                        connection.commit()
                        line_bot_api.push_message(id,TextSendMessage(text='一個前の選択肢に戻るね！'))
                    else:
                        line_bot_api.push_message(id,TextSendMessage(text='最初の選択肢なんだけど・・・？なに？'))
                else:
                    state = -1
                    line_bot_api.push_message(id,TextSendMessage(text='りょうこちゃんを呼んだ人以外無効です！'))

            elif event.message.text == "ちゅうし":

                state = -1
                cur.execute("DELETE FROM ryokochan WHERE group_id = '{}';".format(id))
                connection.commit()
                line_bot_api.reply_message(event.reply_token, [TextSendMessage(text="旅行プランの作成を中止するね。また用があるときは呼んでね。")])

            elif event.message.text == "りょうこちゃん" or event.message.text == "りょうこ":
                cur.execute("SELECT * FROM ryokochan WHERE group_id = '{}';".format(id))
                if cur.fetchone() is None:
                    state = 0
                    if isGroup:
                        cur.execute("INSERT INTO ryokochan (user_id,group_id, state) values('{}','{}', {});".format(event.source.user_id,id, state))
                    else:
                        cur.execute("INSERT INTO ryokochan (group_id, state) values('{}', {});".format(id, state))
                    connection.commit()
                    # emoji = io.BytesIO(emoji)
                    line_bot_api.reply_message(event.reply_token, [TextSendMessage(text='はーい！早速旅行プランを立てよう')])
                    line_bot_api.push_message(id,TextSendMessage(text="旅行日時を選んでね！"))
                else:
                    state = -1
                    line_bot_api.push_message(id,TextSendMessage(text='今はプランニング中だよ！\n中止したいときは「ちゅうし」と言ってね！'))
            elif event.message.text == '#その他' or event.message.text == '#1ページ目に戻る':
                cur.execute("SELECT state FROM ryokochan WHERE group_id = '{}';".format(id))
                state = cur.fetchone()[0]
                if state != 3:
                    state = -1

            elif event.message.text == 'はい':
                cur.execute("SELECT state FROM ryokochan WHERE group_id = '{}';".format(id))
                state = cur.fetchone()[0]


            elif validMessage(event,cur,connection,id) == True:
                cur.execute("SELECT group_id FROM ryokochan WHERE group_id = '{}';".format(id))
                if cur.fetchone() is None:
                    state = 0
                    cur.execute("INSERT INTO ryokochan (group_id, state) values('{}', {});".format(id, state))
                    connection.commit()

                cur.execute("SELECT state FROM ryokochan WHERE group_id = '{}';".format(id))
                state = cur.fetchone()[0]
                if state == 0:
                    if re.match('[0-9]+/[0-9]+/[0-9]+',event.message.text):
                        cur.execute("UPDATE ryokochan SET date = '{}' WHERE group_id = '{}';".format(event.message.text, id))
                elif state == 1:
                    cur.execute("UPDATE ryokochan SET length = '{}' WHERE group_id = '{}';".format(event.message.text[1:], id))
                elif state == 2:
                    cur.execute("UPDATE ryokochan SET region = '{}' WHERE group_id = '{}';".format(event.message.text[1:], id))
                elif state == 3:
                    cur.execute("UPDATE ryokochan SET area = '{}' WHERE group_id = '{}';".format(event.message.text[1:], id))
                elif state == 4:
                    cur.execute("UPDATE ryokochan SET move = '{}' WHERE group_id = '{}';".format(event.message.text[1:], id))
                elif state == 5:
                    cur.execute("UPDATE ryokochan SET plan = '{}' WHERE group_id = '{}';".format(event.message.text[1:], id))
                elif state == 6:
                    if event.message.text == '#いいえ':
                        state = 8
                    if event.message.text == '#地方選択から':
                        cur.execute("UPDATE ryokochan SET state = '{}' WHERE group_id = '{}';".format(2, id))
                        connection.commit()
                        state = 1
                    elif event.message.text == '#エリア選択から':
                        cur.execute("UPDATE ryokochan SET state = '{}' WHERE group_id = '{}';".format(3, id))
                        connection.commit()
                        state = 2
                    elif event.message.text == '#交通手段選択から':
                        cur.execute("UPDATE ryokochan SET state = '{}' WHERE group_id = '{}';".format(4, id))
                        connection.commit()
                        state = 3
                    elif event.message.text == '#旅行スタイル選択から':
                        cur.execute("UPDATE ryokochan SET state = '{}' WHERE group_id = '{}';".format(5, id))
                        connection.commit()
                        state = 4

                elif state == 8:
                    if event.message.text == '#はい':
                        state = 6
                    if event.message.text == '#いいえ':
                        state = 8
                        # print('ok')
                elif state == 9:
                    if event.message.text == '#地方選択から':
                        cur.execute("UPDATE ryokochan SET state = '{}' WHERE group_id = '{}';".format(2, id))
                        connection.commit()
                        state = 1
                    elif event.message.text == '#エリア選択から':
                        cur.execute("UPDATE ryokochan SET state = '{}' WHERE group_id = '{}';".format(3, id))
                        connection.commit()
                        state = 2
                    elif event.message.text == '#交通手段選択から':
                        cur.execute("UPDATE ryokochan SET state = '{}' WHERE group_id = '{}';".format(4, id))
                        connection.commit()
                        state = 3
                    elif event.message.text == '#旅行スタイル選択から':
                        cur.execute("UPDATE ryokochan SET state = '{}' WHERE group_id = '{}';".format(5, id))
                        connection.commit()
                        state = 4
                    elif event.message.text == '#もうプランは決まった！':
                        line_bot_api.push_message(id,TextSendMessage(text='よかったね！'))
                elif state == 10:
                    if event.message.text == '#はい':
                        # ryokochan->travel_reminderをオンにする
                        cur.execute("UPDATE ryokochan SET travel_reminder = TRUE WHERE group_id='{}';".format(id))
                        connection.commit()
                        line_bot_api.push_message(id,TextSendMessage(text='リマインダー設定完了だよ！旅行前日にお知らせするね！楽しみだね！'))
                    elif event.message.text == '#いいえ':
                        # ryokochan->travel_reminderをオフにする
                        cur.execute("UPDATE ryokochan SET travel_reminder = FALSE WHERE group_id='{}';".format(id))
                        connection.commit()
                        line_bot_api.push_message(id,TextSendMessage(text='リマインドはしないんだね！わかった！'))
                    line_bot_api.push_message(id,TextSendMessage(text="お疲れ様！\nプランを変えたくなったら一旦「ちゅうし」してまた呼んでね！"))
                else:
                    pass

                if event.message.text != '来月' and event.message.text != '先月':
                    state += 1
                    cur.execute("UPDATE ryokochan SET state = {} WHERE group_id = '{}';".format(state, id))
                    connection.commit()
                    # 方言チェック
                    if state < 7:
                        try:
                            cur.execute("SELECT region FROM ryokochan WHERE group_id='{}'".format(id))
                            region = cur.fetchone()[0]
                        except:
                            region = ''
                        if state in nextState:
                            if region == '関西':
                                line_bot_api.push_message(id, [TextSendMessage(text="ほな、次いくでっ！")])
                            else:
                                line_bot_api.push_message(id, [TextSendMessage(text="おっけー！\nじゃあつぎのステップに進むね！")])
            else:
                state = -1
            print(state)
            if state == 0:
                year = datetime.date.today().year
                month = datetime.date.today().month
                today = datetime.date.today().day
                if event.message.text == "来月":
                    line_bot_api.push_message(id,TextSendMessage(text='来月のカレンダーを表示するよ！ちょっとまってね！'))
                elif event.message.text == "先月":
                    line_bot_api.push_message(id,TextSendMessage(text='先月のカレンダーを表示するよ！ちょっとまってね！'))

                cur.execute("SELECT year,month FROM ryokochan WHERE group_id='{}'".format(id))
                if cur.fetchone() != (None,None):
                    cur.execute("SELECT year FROM ryokochan WHERE group_id='{}'".format(id))
                    year = cur.fetchone()[0]
                    cur.execute("SELECT month FROM ryokochan WHERE group_id='{}'".format(id))
                    month = cur.fetchone()[0]

                    if event.message.text == "来月":
                        month += 1
                        if month >= 13:
                            year += 1
                            month = 1
                    elif event.message.text == "先月":
                        month -= 1
                        if month < 1:
                            year -= 1
                            month = 12

                    cur.execute("UPDATE ryokochan SET year={},month={} WHERE group_id='{}'".format(year,month,id))
                    connection.commit()
                else:
                    cur.execute("UPDATE ryokochan SET year={},month={} WHERE group_id='{}'".format(2017,8,id))
                    connection.commit()
                dateurl = str(year)+'/'+str(month)+'/'
                makeCalenderImage.make(year,month)
                img = Image.open("./calenders/calender.jpg")
                width,height = img.size
                wRatio,hRatio = 1024/width,1024/height
                actions = []
                actions.append(MessageImagemapAction(
                      text = '先月',
                      area = ImagemapArea(
                          x = 670*wRatio, y = 20*hRatio, width = 140, height = 105
                      )
                ))
                actions.append(MessageImagemapAction(
                      text = '来月',
                      area = ImagemapArea(
                            x = 825*wRatio, y = 20*hRatio, width = 140, height = 105
                      )
                ))
                weekday = date(year,month,1).isoweekday()
                Yaxis = 0
                for i in range(days[month]):

                    day = i + weekday
                    xpos = (140*(day%7))*wRatio
                    ypos = (105*Yaxis + 228)*hRatio
                    actions.append(MessageImagemapAction(
                          text = '{}/{}/{}'.format(year,month,i+1),
                          area = ImagemapArea(
                                x = xpos, y = ypos, width = 140, height = 105
                          )
                    ))
                    if (day+1)%7 == 0:
                        Yaxis += 1

                message = ImagemapSendMessage(
                    base_url = 'https://' + request.host + '/calender/'+dateurl + uuid.uuid4().hex, # prevent cache
                    alt_text = 'カレンダー',
                    base_size = BaseSize(height=1040, width=1040),
                    actions = actions
                )
                line_bot_api.push_message(id,message)
            elif state == 1:

                buttons_template = ButtonsTemplate(
                    title='旅行時間はどうする？',
                    text='プランの長さを選んでね！',
                    actions=[
                        MessageTemplateAction(
                            label='１日',
                            text='#１日'
                            ),
                        MessageTemplateAction(
                            label='半日',
                            text='#半日'
                            )
                        ])
                template_message = TemplateSendMessage(
                    alt_text='プランの長さを選んでね！',
                    template=buttons_template)
                line_bot_api.push_message(id, template_message)
            # state 1: 日付の確認と地方の決
            elif state == 2:
                # Question with buttons
                buttons_template = ButtonsTemplate(
                    title='どこに行く予定なの？',
                    text='行きたい地方を選んでね！',
                    actions=[
                        MessageTemplateAction(
                            label='北海道',
                            text='#北海道'
                            ),
                        MessageTemplateAction(
                            label='関東',
                            text='#関東'
                            ),
                        MessageTemplateAction(
                            label='関西',
                            text='#関西'
                            ),
                        MessageTemplateAction(
                            label='九州・沖縄',
                            text='#九州・沖縄'
                            )
                        ])
                template_message = TemplateSendMessage(
                    alt_text='行きたい地方を選んでね！',
                    template=buttons_template)

                line_bot_api.push_message(id, template_message)
            elif state == 3:
                # DBに接続して、エリア一覧を取得
                # 地方を取得
                cur.execute("SELECT region FROM ryokochan WHERE group_id='{}'".format(id))
                region = cur.fetchone()[0]
                # 地方に含まれるエリアをリストアップ
                cur.execute("SELECT area FROM areas WHERE region='{}'".format(region))
                areas = cur.fetchall()
                # cur.fetchall()で取得した結果はタプルのリストになるので整形
                areas = [a[0] for a in areas]
                sharp_areas = ['#'+a for a in areas]
                # エリア選択
                # エリア候補が15個以下ならそのままカルーセルを生成
                if len(areas) <= 15:
                    template_message = area_carousel(areas, region, 0)
                else:
                    # その他を選択していた場合は次の選択肢
                    if event.message.text == '#その他':
                        template_message = area_carousel(areas[14:] + ['1ページ目に戻る'], region,5)
                    else:
                        template_message = area_carousel(areas[:14] + ['その他'], region,0)

                line_bot_api.push_message(id, template_message)
            # state 3: 交通手段
            elif state == 4:
                # Question with buttons
                action = []
                cur.execute("SELECT area FROM ryokochan WHERE group_id='{}'".format(id))
                area = cur.fetchone()[0]
                cur.execute("SELECT move_way FROM areas WHERE area='{}'".format(area))
                move_way = cur.fetchone()[0]
                for i in range(move_way):
                    cur.execute("SELECT way{} FROM areas WHERE area='{}'".format(i+1,area))
                    way = cur.fetchone()[0]
                    moves['{}'.format(way)] = i+1
                    action.append(MessageTemplateAction(
                        label='{}'.format(way),
                        text='#{}'.format(way)
                        ))
                # 方言チェック
                cur.execute("SELECT region FROM ryokochan WHERE group_id='{}'".format(id))
                region = cur.fetchone()[0]
                if region == '関西':
                    buttons_template = ButtonsTemplate(
                        title='現地での交通手段はどれにするん？',
                        text='予定の交通手段を選んでな！',
                        actions=action
                        )
                    template_message = TemplateSendMessage(
                        alt_text='予定の交通手段を選んでな！',
                        template=buttons_template)
                else:
                    buttons_template = ButtonsTemplate(
                        title='うんうん！\nどうやって移動したいの？',
                        text='予定の交通手段を選んでね！',
                        actions=action
                        )
                    template_message = TemplateSendMessage(
                        alt_text='予定の交通手段を選んでね！',
                        template=buttons_template)

                line_bot_api.push_message(id, template_message)

            elif state == 5:
                # 方言チェック
                cur.execute("SELECT region FROM ryokochan WHERE group_id='{}'".format(id))
                region = cur.fetchone()[0]
                if region == '関西':
                    buttons_template = ButtonsTemplate(
                        title='旅行スタイルどうするん？',
                        text='グループにあった旅行スタイルを選んでな！',
                        actions=[
                            MessageTemplateAction(
                                label='いろいろ楽しむ',
                                text='#いろいろ楽しむ'
                                ),
                            MessageTemplateAction(
                                label='のんびり行こう',
                                text='#のんびり行こう'
                                ),
                            MessageTemplateAction(
                                label='文化を知りたい',
                                text='#文化を知りたい'
                                ),
                            MessageTemplateAction(
                                label='子どもとめぐる',
                                text='#子どもとめぐる'
                                )
                            ])
                    template_message = TemplateSendMessage(
                        alt_text='グループにあった旅行スタイルを選んでな！',
                        template=buttons_template)
                else:
                    buttons_template = ButtonsTemplate(
                        title='どんな旅行スタイルにする？',
                        text='グループにあった旅行スタイルを選んでね！',
                        actions=[
                            MessageTemplateAction(
                                label='いろいろ楽しむ',
                                text='#いろいろ楽しむ'
                                ),
                            MessageTemplateAction(
                                label='のんびり行こう',
                                text='#のんびり行こう'
                                ),
                            MessageTemplateAction(
                                label='文化を知りたい',
                                text='#文化を知りたい'
                                ),
                            MessageTemplateAction(
                                label='子どもとめぐる',
                                text='#子どもとめぐる'
                                )
                            ])
                    template_message = TemplateSendMessage(
                        alt_text='グループにあった旅行スタイルを選んでね！',
                        template=buttons_template)

                line_bot_api.push_message(id, template_message)
            elif state == 6:
                cur.execute("SELECT * FROM ryokochan WHERE group_id = '{}';".format(id))
                data = cur.fetchone()
                profile = {}
                for i in range(len(columns)):
                    profile[columns[i]] = data[i]
                # 方言チェック
                cur.execute("SELECT region FROM ryokochan WHERE group_id='{}'".format(id))
                region = cur.fetchone()[0]
                if region == '関西':
                    message = 'プランの長さ:{}\n地方:{}\nエリア:{}\n交通手段:{}\n旅行スタイル:{}\nこの条件でプラン検索するわ！ウチにまかせとき！'.format(profile['length'],profile['region'],profile['area'],profile['move'],profile['plan'])
                else:
                    message = 'プランの長さ:{}\n地方:{}\nエリア:{}\n交通手段:{}\n旅行スタイル:{}'.format(profile['length'],profile['region'],profile['area'],profile['move'],profile['plan'])

                line_bot_api.push_message(id, [TextSendMessage(text=message)])
                line_bot_api.push_message(id, [TextSendMessage(text='この条件で旅行プランを作るよ！ちょっと待っててね！')])

                cur.execute("SELECT start_id FROM areas WHERE area = '{}';".format(profile['area']))
                start_id = cur.fetchone()[0]
                cur.execute("SELECT * FROM ryokochan WHERE group_id = '{}';".format(id))
                data = cur.fetchone()
                cur.execute("SELECT area_id FROM areas WHERE area = '{}';".format(profile['area']))
                area = cur.fetchone()[0]
                url = 'http://ctplanner.jp/ctp5/CTPlanner5.7_main.html?place={}&lang=jp&planType={}&start={}&goal={}&defaultTourTime={}'.format(area, styles['{}'.format(profile['plan'])], start_id, start_id, lengths['{}'.format(profile['length'])])
                [travelPlan,planHtml] = htmlParse.outputPlan(url)
                if travelPlan != []:
                    spotlen = len(travelPlan[2:-1])
                    if spotlen >= 15:
                        travelPlan = travelPlan[:2] +travelPlan[2:16]+[travelPlan[-1]]
                    makeSiori.makeImage(url,profile,travelPlan,area)
                    message = ImageSendMessage(
                        original_content_url='https://' + request.host + '/images/siori/'+area+'/'+str(styles[profile['plan']])+'/' + uuid.uuid4().hex,
                        preview_image_url='https://' + request.host + '/images/siori/thumb/'+area+'/'+str(styles[profile['plan']])+'/' + uuid.uuid4().hex
                    )
                    line_bot_api.push_message(id,message)
                    line_bot_api.push_message(id, [TextSendMessage(text='おまたせ！これが旅行のしおりだよ！')])
                    line_bot_api.push_message(id, [TextSendMessage(text='旅行ルートの地図を作るから、しおりを見て待っててね！')])
                    [descriptions,spots] = makeDescription.makeDes(planHtml)
                    if spotlen >= 15:
                        spots = spots[:14]
                    map_id = fetch_googlemap_image.fetch_googlemap_image(spots)
                    outputtxt = open('./documents/spots/spotdescription_{}.txt'.format(map_id),'w')
                    for i in range(len(spots)):
                        line = spots[i] + ' ' + descriptions[spots[i]]+'\n'
                        outputtxt.write(line)
                    outputtxt.close()
                    cur.execute("UPDATE ryokochan SET map_id = '{}' WHERE group_id = '{}';".format(map_id, id))
                    connection.commit()
                    message = ImageSendMessage(
                        original_content_url='https://' + request.host + '/images/maps/{}'.format(map_id) + '/' + uuid.uuid4().hex,
                        preview_image_url='https://' + request.host + '/images/maps/thumb/{}'.format(map_id) + '/' + uuid.uuid4().hex
                    )
                    line_bot_api.push_message(id,message)
                    line_bot_api.push_message(id, [TextSendMessage(text='おまたせ〜！これが旅行ルートの地図だよ！')])
                    buttons_template = ButtonsTemplate(
                        title='各スポットの説明を見たい？',
                        text='プランにある各スポットの情報を簡単に説明するよ！',
                        actions=[
                            MessageTemplateAction(
                                label='はい',
                                text='#はい'
                                ),
                            MessageTemplateAction(
                                label='いいえ',
                                text='#いいえ'
                                )
                            ])
                    template_message = TemplateSendMessage(
                        alt_text='プランにある各スポットの情報を簡単に説明するよ！',
                        template=buttons_template)

                    line_bot_api.push_message(id, template_message)
                else:
                    line_bot_api.push_message(id,TextSendMessage(text="ごめんね・・・この旅行スタイルのプランは見つからなかったよ。条件を変えてもう一度試してみてね！"))
                    buttons_template = ButtonsTemplate(
                        title='他の条件で検索してみる？',
                        text='好きな所から再検索できるよ！',
                        actions=[
                            MessageTemplateAction(
                                label='地方選択から',
                                text='#地方選択から'
                            ),
                            MessageTemplateAction(
                                label='エリア選択から',
                                text='#エリア選択から'
                            ),
                            MessageTemplateAction(
                                label='交通手段選択から',
                                text='#交通手段選択から'
                            ),
                            MessageTemplateAction(
                                label='旅行スタイル選択から',
                                text='#旅行スタイル選択から'
                            )
                            ])
                    template_message = TemplateSendMessage(
                        alt_text='他の条件で検索してみる？',
                        template=buttons_template)
                    line_bot_api.push_message(id, template_message)

            elif state == 7:
                cur.execute("SELECT map_id FROM ryokochan WHERE group_id='{}';".format(id))
                map_id = cur.fetchone()[0]
                spottxt = open('./documents/spots/spotdescription_{}.txt'.format(map_id),'r')
                spots = []
                for line in spottxt:
                    words = line.split(' ')
                    spots_dict[words[0]] = words[1]
                    spots.append(words[0])
                # spots.append('終わる')
                template_message = spot_carousel(spots)
                line_bot_api.push_message(id, template_message)
            elif state == 8:
                flag = False
                # if event.message.text[1:] == '終わる':
                #     flag = True
                #     line_bot_api.push_message(id,TextSendMessage(text="使ってくれてありがとう！また用事があったら呼んでね！"))
                #     cur.execute("DELETE FROM ryokochan WHERE group_id='{}';".format(id))
                #     connection.commit()
                # else:
                #     line_bot_api.push_message(id,[TextSendMessage(text="{}の説明はこれだよ！".format(event.message.text[1:])),TextSendMessage(text="{}".format(spots_dict[event.message.text[1:]]))])
                line_bot_api.push_message(id,[TextSendMessage(text="{}の説明はこれだよ！".format(event.message.text[1:])),TextSendMessage(text="{}".format(spots_dict[event.message.text[1:]][:-1]))])
                if flag == False:
                    buttons_template = ButtonsTemplate(
                        title='他のスポットの説明も見る？',
                        text='簡単にだけど説明しちゃうよ！',
                        actions=[
                            MessageTemplateAction(
                                label='はい',
                                text='#はい'
                                ),
                            MessageTemplateAction(
                                label='いいえ',
                                text='#いいえ'
                                )
                            ])
                    template_message = TemplateSendMessage(
                        alt_text='簡単にだけど説明しちゃうよ！',
                        template=buttons_template)

                    line_bot_api.push_message(id, template_message)

            # プラン再検索
            elif state == 9:
                carousel_template = CarouselTemplate(
                                        columns=[
                                                CarouselColumn(
                                                    title='他の条件で検索してみる？',
                                                    text='好きな所から再検索できるよ！',
                                                    actions=[
                                                        MessageTemplateAction(
                                                            label='地方選択から',
                                                            text='#地方選択から'
                                                        ),
                                                        MessageTemplateAction(
                                                            label='エリア選択から',
                                                            text='#エリア選択から'
                                                        ),
                                                        MessageTemplateAction(
                                                            label='交通手段選択から',
                                                            text='#交通手段選択から'
                                                        ),
                                                    ]
                                                ),
                                                CarouselColumn(
                                                    title='他の条件で検索してみる？',
                                                    text='好きな所から再検索できるよ！',
                                                    actions=[
                                                        MessageTemplateAction(
                                                            label='旅行スタイル選択から',
                                                            text='#旅行スタイル選択から'
                                                        ),
                                                        MessageTemplateAction(
                                                            label='もうプランは決まった！',
                                                            text='#もうプランは決まった！'
                                                        ),
                                                        MessageTemplateAction(
                                                            label=' ',
                                                            text=' '
                                                        ),
                                                    ]
                                                )
                                            ]
                                        )
                template_message = TemplateSendMessage(
                    alt_text='好きな所から再検索できるよ！',
                    template=carousel_template)
                line_bot_api.push_message(id, template_message)
            # リマインドするか決定
            elif state == 10:
                # プランは決まってるので、2,4週間前の催促をオフ ryokochan->reminder
                # そのグループの全員の個人催促もオフ time_management -> user_notification
                # グループ催促は変えない
                cur.execute("UPDATE ryokochan SET reminder = FALSE WHERE group_id='{}';".format(id))
                connection.commit()
                cur.execute("UPDATE time_management SET user_notification = FALSE WHERE group_id='{}';".format(id))
                connection.commit()

                buttons_template = ButtonsTemplate(
                    title='リマインドする？',
                    text='よかったら旅行のリマインドするよ！',
                    actions=[
                        MessageTemplateAction(
                            label='はい',
                            text='#はい'
                            ),
                        MessageTemplateAction(
                            label='いいえ',
                            text='#いいえ'
                            )
                        ])
                template_message = TemplateSendMessage(
                    alt_text='よかったら旅行のリマインドするよ！',
                    template=buttons_template)
                line_bot_api.push_message(id, template_message)



@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    if event.source.type == 'user':
        execute(event, event.source.user_id)
    elif event.source.type == 'group':
        execute(event, event.source.group_id, isGroup=True)
    elif event.source.type == 'room':
        execute(event, event.source.room_id, isGroup=True)

@app.route("/calender/<year>/<month>/<uniqid>/<size>/", methods=['GET'])
def calender(uniqid, size,year,month):
    img = Image.open("./calenders/calender_{}_{}.png".format(year,month))
    img_resize = img.resize((int(size), int(size)))
    img_io = io.BytesIO()
    img_resize.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route("/images/siori/<area>/<plan>/<uniqid>", methods=['GET'])
def siori(area,plan,uniqid):
    img = Image.open("./images/siori/siori{}_{}.png".format(area,plan))
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route("/images/siori/thumb/<area>/<plan>/<uniqid>", methods=['GET'])
def siori_thumb(area,plan,uniqid):
    img = Image.open("./images/siori/siori{}_{}.png".format(area,plan))
    img_resize = img.resize((240,240))
    img_io = io.BytesIO()
    img_resize.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route("/images/maps/<url>/<uniqid>", methods=['GET'])
def map(url,uniqid):
    img = Image.open("./images/maps/googlemap_{}.png".format(url))
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route("/images/maps/thumb/<url>/<uniqid>", methods=['GET'])
def map_thumb(url,uniqid):
    img = Image.open("./images/maps/googlemap_{}.png".format(url))
    img_resize = img.resize((240,240))
    img_io = io.BytesIO()
    img_resize.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route("/images/area_thumbnail/<area>/<image>/<uniqid>", methods=['GET'])
def thumbnail(area,image,uniqid):
    img = Image.open("./images/area_thumbnail/"+area+'/'+image)
    img_io = io.BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/jpg')

@handler.add(JoinEvent)
def handle_event(event):
    # グループ追加時のあいさつ
    if event.type == 'join':
        line_bot_api.push_message(event.source.group_id, TextSendMessage(text='りょうこを仲間に入れてくれてありがとう！！みんなの日帰り国内旅行計画をサポートするよ！一緒に楽しい旅行計画を考えよう！'))
        line_bot_api.push_message(event.source.group_id, TextSendMessage(text='【りょうこちゃん】って呼びかけてくれれば、プランを一緒に考えるよ！プランを考えてるときに間違えちゃったら【もどる】で戻れるよ！計画をやめたいときには【ちゅうし】って言ってね。'))


if __name__ == "__main__":
    app.debug = True
    app.run()
