import os
import datetime
import psycopg2
import urllib.parse as urlparse
from linebot import (
    LineBotApi, WebhookHandler,
)
from linebot.exceptions import (
    LineBotApiError
)
from linebot.models import ButtonsTemplate, TemplateSendMessage, TextSendMessage, MessageTemplateAction

days = {1:31,2:28,3:31,4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31}


line_bot_api = LineBotApi(os.environ.get('LINE_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))
# url = urlparse.urlparse('postgres://iptqobntehqehv:7daa0329638fd1c94bd2cd6344797707b3bf1c92542feb903ad820eb232c6f30@ec2-107-22-251-55.compute-1.amazonaws.com:5432/depjq2cs01ttml')
url = urlparse.urlparse(os.environ.get('DATABASE_URL'))

dbname = url.path[1:]
user = url.username
password = url.password
host = url.hostname
port = url.port
connection = psycopg2.connect(dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port)
cur = connection.cursor()

if __name__ == "__main__":
    # ryokochanのテーブルにある全てのグループに対し、最終発言時間から一定時間後にpush
    day1 = datetime.date.today() + datetime.timedelta(days=1)
    day7 = datetime.date.today() + datetime.timedelta(days=7)
    day14 = datetime.date.today() + datetime.timedelta(days=14)
    day28 = datetime.date.today() + datetime.timedelta(days=28)

    # 旅行の前日、1週間にリマインド
    # 2週間前と1ヶ月前にプランが決まっているか確認
    remind1 = str(day1.year) + '/' + str(day1.month) + '/' + str(day1.day)
    remind2 = str(day7.year) + '/' + str(day7.month) + '/' + str(day7.day)
    check1 = str(day14.year) + '/' + str(day14.month) + '/' + str(day14.day)
    check2 = str(day28.year) + '/' + str(day28.month) + '/' + str(day28.day)

    # テーブル内のidリスト
    cur.execute("SELECT group_id FROM ryokochan;")
    ids = cur.fetchall()
    ids = [id[0] for id in ids]

    for id in ids:
        # 旅行日
        cur.execute("SELECT date FROM ryokochan WHERE group_id = '{}';".format(id))
        date = cur.fetchone()[0]
        # flag
        cur.execute("SELECT reminder FROM ryokochan WHERE group_id = '{}';".format(id))
        reminder = cur.fetchone()[0]
        cur.execute("SELECT travel_reminder FROM ryokochan WHERE group_id = '{}';".format(id))
        travel_reminder = cur.fetchone()[0]
        if travel_reminder:
            if date == remind1:
                try:
                    line_bot_api.push_message(id, TextSendMessage(text='いよいよ明日だね！楽しみ～'))
                except LineBotApiError as e:
                    pass
        if reminder:
            if date == remind2:
                try:
                    line_bot_api.push_message(id, TextSendMessage(text='"もうプラン決めた？早く決めないと！来週だよ！プランを立てるときは私の名前を呼んでね☆"'))
                except LineBotApiError as e:
                    pass
            if date == check1:
                try:
                    line_bot_api.push_message(id, TextSendMessage(text='もうプランは決めた？決めてなかったら私の名前を呼んでね！'))
                except LineBotApiError as e:
                    pass
            if date == check2:
                try:
                    line_bot_api.push_message(id, TextSendMessage(text='どうどう？プラン計画は進んでる？進んでなかったら私の名前を呼んでね！'))
                except LineBotApiError as e:
                    pass
