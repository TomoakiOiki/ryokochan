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


line_bot_api = LineBotApi(os.environ.get('LINE_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))
# line_bot_api = LineBotApi('TTX5JPqWJma6w8KOfqJQFUjXc4xQodlXZ2dtUpyBqkPgYJfHrJD5GeniIfmSo/kzSab4doEUV+HLE/667BeN6AX14rf5Fa2VjdNPOlv711M2jzf7rhKBgLiIgzqbw6C/9dSNAGwSG88yp2SHi6bmNgdB04t89/1O/w1cDnyilFU=')
# handler = WebhookHandler('9710803da82cc0d6def44481d28461fa')
#
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
    # time_managementのテーブルにある全てのグループに対し、最終発言時間から一定時間後にpush
    now = int(datetime.datetime.today().strftime('%s'))

    # テーブル内のグループidリスト
    cur.execute("SELECT DISTINCT group_id FROM time_management;")
    ids = cur.fetchall()
    ids = [id[0] for id in ids]

    # 発言のないグループを催促
    for id in ids:
        # 各グループの最終発言時間を抽出
        cur.execute("SELECT last_remark FROM time_management WHERE group_id = '{}';".format(id))
        remarks = cur.fetchall()
        remarks = [remark[0] for remark in remarks]
        last_remark = max(remarks)

        # 一定時間経過してるグループに対してはpushする
        if now - last_remark > 100:
            # 通知設定
            cur.execute("SELECT notification FROM time_management WHERE group_id = '{}';".format(id))
            isNotification = cur.fetchone()[0]
            if isNotification:
                try:
                    line_bot_api.push_message(id, TextSendMessage(text='おーい、どうなった？そろそろ決めないとやばいかも！？'))
                    # 何度も通知が来るとうざいので、pushした時刻を最終発言時刻に更新する
                    cur.execute("UPDATE time_management SET last_remark = {} WHERE group_id = '{}';".format(now, id))
                    connection.commit()

                    # 催促をまだするか確認
                    buttons_template = ButtonsTemplate(
                        title='まだ催促は必要？',
                        text='もういらないかな？',
                        actions=[
                            MessageTemplateAction(
                                label='まだいる！',
                                text='#まだいる！'
                                ),
                            MessageTemplateAction(
                                label='もういらない！',
                                text='#もういらない！'
                                )
                            ])
                    template_message = TemplateSendMessage(
                        alt_text='まだ催促は必要？',
                        template=buttons_template)
                    line_bot_api.push_message(id, template_message)
                except LineBotApiError as e:
                    pass

    # テーブル内のidリスト
    cur.execute("SELECT user_id FROM time_management;")
    user_ids = cur.fetchall()
    user_ids = [id[0] for id in user_ids]
    cur.execute("SELECT DISTINCT group_id FROM time_management;")
    group_ids = cur.fetchall()
    group_ids = [id[0] for id in group_ids]

    # 発言のないユーザーを催促
    for user_id, group_id in zip(user_ids, group_ids):
        # 各ユーザーの最終発言時間を抽出
        cur.execute("SELECT last_remark FROM time_management WHERE group_id = '{}' AND user_id = '{}';".format(group_id, user_id))
        remark = cur.fetchone()
        if remark is not None:
            remark = remark[0]
        else:
            remark = now

        # 一定時間経過してるユーザーに対しては名指しでpushする
        if now - remark > 100:
            try:
                profile = line_bot_api.get_profile(user_id)
                name = profile.display_name
                line_bot_api.push_message(group_id, TextSendMessage(text='{}さんの意見も聞きたいな！そろそろ{}さんと話したいなぁ～'.format(name, name)))
                # 何度も通知が来るとうざいので、pushした時刻を最終発言時刻に更新する
                cur.execute("UPDATE time_management SET last_remark = {} WHERE group_id = '{}' AND user_id = '{}';".format(now, roup_id, user_id))
                connection.commit()
            except:
                pass
