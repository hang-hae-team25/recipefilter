from pymongo import MongoClient
import requests
from flask import Flask, render_template, jsonify, request
from bs4 import BeautifulSoup

# app = Flask(__name__)
#
# client = MongoClient('localhost', 27017)
# db = client.dbrecipefilter

headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}


# @app.route('/')
# def home():
#    return 'This is Home!'
#
# if __name__ == '__main__':
#    app.run('0.0.0.0', port=5000, debug=True)


for i in range(0,1):
    index = i + 1
    url = f'https://www.10000recipe.com/recipe/list.html?order=reco&page={index}'
    data = requests.get(url, headers=headers)
    soup = BeautifulSoup(data.text, 'html.parser')
    trs = soup.select('#contents_area_full > ul > ul > li')
    trsText = soup.select('#contents_area_full > ul > ul > li > div.common_sp_caption > div.common_sp_caption_tit.line2')
    trsHlk = soup.select('#contents_area_full > ul > ul > li > div.common_sp_thumb > a')
    trsImg = soup.select('#contents_area_full > ul > ul > li > div.common_sp_thumb > a > img')
    # print(trs) len(trsImg)
    for i in range(0, len(trsImg)):
        text = trsText[i].text
        hlk = trsHlk[i]['href']
        url_detail = url.split("/recipe")[0] + hlk
        imgSource = trsImg[i]['src']

        print()
        print(f'title: {text}')
        print(f'hyperlink: {hlk}')
        print(f'img: {imgSource}')
        print(f'detail_info_link: {url_detail}')

        data = requests.get(url_detail, headers=headers)
        soup2 = BeautifulSoup(data.text, 'html.parser')

        trsDesc = soup2.select_one('#recipeIntro')
        if trsDesc is not None:
            desc = trsDesc.text.strip()
            print(f'description: {desc}')

        trsDetail = soup2.select('#divConfirmedMaterialArea > ul > a > li')
        if len(trsDetail) != 0:
            for elem in trsDetail:
                ingre = elem.text.strip().split("\n")[0]
                print(f'ingredient: {ingre}')

