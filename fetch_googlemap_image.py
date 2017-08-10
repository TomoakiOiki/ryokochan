# -*- coding: utf-8 -*-
import urllib
import urllib.request
from urllib.parse import urlparse

from PIL import Image
from io import BytesIO
import uuid
from selenium import webdriver


def fetch_googlemap_url(route):
    url = str('https://www.google.co.jp/maps/dir')
    for point in route:
        url += str('/')
        url += urllib.parse.quote_plus(point, encoding='utf-8')
    return url

def fetch_googlemap_image(route):
    url= fetch_googlemap_url(route)
    # Open Web Browser & Resize 720P
    driver = webdriver.PhantomJS(desired_capabilities={'phantomjs.page.settings.resourceTimeout': str(1)})
    driver.set_window_size(1024, 768)
    driver.get(url)
    img = driver.get_screenshot_as_png()
    driver.quit()
    img = Image.open(BytesIO(img))
    img = img.crop((400, 100, 1024, 650))
    map_id = uuid.uuid4().hex
    img.save('./images/maps/googlemap_{}.png'.format(map_id), 'png', quality=100, optimize=True)
    return map_id
