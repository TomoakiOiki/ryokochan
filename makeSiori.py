# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont
from datetime import date
import psycopg2
import urllib.parse as urlparse
import htmlParse
from selenium import webdriver
def makeImage(url,profile,travelPlan,area_id):
    styles = {'いろいろ楽しむ':1,'のんびり行こう':2,'文化を知りたい':3,'子どもとめぐる':4}
    if len(travelPlan[2:-1]) <= 4:
        imgNum = 2
    else:
        imgNum = 1
    image = Image.open('./images/siori/siori{}.jpg'.format(imgNum),'r')
    draw = ImageDraw.Draw(image)
    area = profile['area']
    style = profile['plan']
    while len(area) < 6:
        area = '　'+area
    font = ImageFont.truetype('./fonts/yasashisa.ttf',24, encoding='unic')
    draw.text((205,102), '{}'.format(area), font=font, fill='#000')
    draw.text((375,102), '{}'.format(style), font=font, fill='#000')
    font = ImageFont.truetype('./fonts/yasashisa.ttf',20, encoding='unic')
    travelTime = travelPlan[0]
    start = travelPlan[1]
    plan = travelPlan[2:-1]
    goal = travelPlan[-1]
    ypos = 0
    draw.text((150,160+ypos), '{}'.format(travelTime), font=font, fill='#000')
    ypos += 40
    draw.text((150,160+ypos), '{}'.format(start), font=font, fill='#000')
    ypos += 40
    font = ImageFont.truetype('./fonts/yasashisa.ttf',16, encoding='unic')
    for i in range(len(plan)):
        draw.text((170,160+ypos), '{}'.format(plan[i]), font=font, fill='#000')
        ypos += 25
    ypos += 15
    font = ImageFont.truetype('./fonts/yasashisa.ttf',20, encoding='unic')
    draw.text((150,160+ypos), '{}'.format(goal), font=font, fill='#000')
    image.save('./images/siori/siori{}_{}.png'.format(area_id,styles[profile['plan']]), 'png', quality=100, optimize=True)
