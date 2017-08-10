# -*- coding: utf-8 -*-
import re

def makeDes(html):
    html = re.sub('<[^>]*>'," ",html)
    spot = re.findall('[0-9]+\. [^;]*;',html)
    for i in range(len(spot)):
        spot[i] = spot[i][:-6]
        spot[i] = re.sub('[0-9]+\. ','',spot[i])
    html = re.sub('\n|\t','',html)
    html = re.sub('出発地[^&]*','',html)
    html = re.sub('到着地[^&]*','',html)
    html = re.sub('総旅行時間: [0-9]*:[0-9]*','',html)
    html = re.sub('[(]*[0-9]+:[0-9]+[)]*','',html)
    html = re.sub('-[^0-9]*','',html)
    html = re.sub('[0-9]+\. [^;]*;','',html)
    html = re.sub('&nbsp;','',html)
    html = re.sub(' [ ]+',' ',html)
    descript = html[1:-1].split(' ')
    descriptions = {}
    for i in range(len(spot)):
        line = re.sub('\n','',descript[i])
        descriptions[spot[i]] = line
    for i in range(len(spot)):
        pass
        print('{} = {}'.format(spot[i],descriptions[spot[i]]))
    return [descriptions,spot]
