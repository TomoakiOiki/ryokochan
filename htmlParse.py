import re
from selenium import webdriver

def outputPlan(url):
    ret = []
    driver = webdriver.PhantomJS()
    url = url
    driver.get(url)
    html = driver.page_source
    html = html[html.find('総旅行時間'):html.find('キーワード')]
    match = re.search('総旅行時間: [0-9]*:[0-9]*',html)
    if match == None:
        return [[], '']
    else:
        travelTime = match.group()
    spot = re.findall('[0-9]+\. [^;]*;',html)
    start = re.search('出発地[^&]*',html).group()
    goal = re.search('到着地[^&]*',html).group()
    ret.append(travelTime)
    for i in range(len(spot)):
        spot[i] = spot[i][:-6]
    spot.insert(0,start)
    spot.append(goal)
    for i in range(len(spot)):
        ret.append(spot[i])
    driver.quit()
    return [ret,html]
