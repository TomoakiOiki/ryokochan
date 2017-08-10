from PIL import Image, ImageDraw, ImageFont
from datetime import date
#140 105
def make(year,month):
    text_canvas = Image.open("./calenders/calender.jpg","r")
    draw = ImageDraw.Draw(text_canvas)
    days = {1:31,2:28,3:31,4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31}
    #うるう年かどうか
    if (year % 4 == 0 and year % 100 != 0) or year % 400 == 0:
        days[2] = 29
    #年の描画
    font = ImageFont.truetype('./fonts/yasashisa.ttf',72, encoding='unic')
    draw.text((25,30), '{}'.format(year), font=font, fill='#000')#draw year
    #月の描画
    font = ImageFont.truetype('./fonts/yasashisa.ttf',48, encoding='unic')
    draw.text((230,50), '{}'.format(month), font=font, fill='#000')#draw month

    Yaxis = 0
    #y年m月１日が何曜日か
    weekday = date(year,month,1).isoweekday()
    #日の描画
    for i in range(days[month]):
        day = i + weekday
        x = 140*(day%7) + 35
        if i+1 < 10:
            x += 20
        y = 105 * Yaxis + 280
        color = '#000000'
        if (day+1) % 7 == 0:
            color = '#0000ff'
        elif (day+1) % 7 == 1:
            color = '#ff0000'
        draw.text((x,y), '{}'.format(i+1), font=font, fill=color)
        if (day+1)%7 == 0:
            Yaxis += 1

    draw.rectangle((670, 20, 810, 125), fill=(0, 255, 0))
    draw.text((690,50), 'Prev', font=font, fill='#000')
    draw.rectangle((825, 20, 965, 125), fill=(255, 0, 0))
    draw.text((845,50), 'Next', font=font, fill='#000')
    # 保存
    text_canvas.save('./calenders/calender_{}_{}.png'.format(year,month), 'png', quality=100, optimize=True)
