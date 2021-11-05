# -- coding: utf-8 --
from pymongo import MongoClient
import jwt
import datetime
import hashlib
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

SECRET_KEY = 'SPARTA'
app.secret_key = SECRET_KEY
client = MongoClient('mongodb://test:test@localhost', 27017)
db = client.dbrecipefilter


@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        #print(user_info) 토큰으로 받아온 값 확인
        return render_template('index.html', user_info=payload["id"])
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)


@app.route('/sign_in', methods=['POST'])
def sign_in():
    # 로그인
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']

    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    result = db.users.find_one({'username': username_receive, 'password': pw_hash})

    if result is not None:
        payload = {
            'id': username_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256').decode('utf-8')

        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


@app.route('/sign_up/save', methods=['POST'])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    nickname_receive = request.form['nickname_give']
    meat_receive = request.form['meat_give']
    seafood_receive = request.form['seafood_give']
    vegetable_receive = request.form['vegetable_give']
    grain_receive = request.form['grain_give']
    dairy_receive = request.form['dairy_give']
    doc = {
        "username": username_receive,  # 아이디
        "password": password_hash,  # 비밀번호
        "nickname": nickname_receive,  # 닉네임
        "meat": meat_receive,  # 육류
        "seafood": seafood_receive,  # 해산물
        "vegetable": vegetable_receive,  # 채소
        "grain": grain_receive,  # 곡류
        "dairy": dairy_receive,  # 유제품
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})


@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})


def view_recipes_help(filterKeyword, recipes, parsedRecipes):

    for i in range(0, len(recipes)):
        output = {'title': recipes[i]['title'], 'hyperlink': recipes[i]['hyperlink'], 'image': recipes[i]['image']}
        if 'description' in recipes[i]:
            output['description'] = recipes[i]['description']
        ingredients = []
        category = []
        for j in range(0, 5):
            key = 'category' + str(j + 1)
            if key in recipes[i]:
                category.append(recipes[i][key])
        categorys = ''
        for j in range(0, len(category)):
            categorys += category[j] + ' '

        ingreIndex = 1
        while True:
            key = 'ingredient' + str(ingreIndex)
            if key in recipes[i]:
                ingredients.append(recipes[i][key])
            else:
                break
            ingreIndex += 1

        allIngredients = ''
        for j in range(0, len(ingredients)):
            allIngredients += ingredients[j] + ' '

        output['ingredient'] = allIngredients
        output['category'] = categorys
        if len(filterKeyword) > 0:
            for keyword in filterKeyword:
                if keyword in recipes[i]:
                    output['filter'] = 'Y'
                    break;
        parsedRecipes.append(output)


@app.route('/recipes', methods=['GET'])
def view_recipes():
    recipes = list(db.dbrecipefilter.find({}, {'_id': False}))
    parsedRecipes = []

    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    user_info = db.users.find_one({"username": payload["id"]})
    keyword = []
    if user_info['meat'] == '육류':
        keyword.append('category1')
    if user_info['seafood'] == '해산물':
        keyword.append('category2')
    if user_info['vegetable'] == '채소':
        keyword.append('category5')
    if user_info['grain'] == '곡류':
        keyword.append('category4')
    if user_info['dairy'] == '유제품':
        keyword.append('category3')

    view_recipes_help(keyword, recipes, parsedRecipes)
    return jsonify({'recipes': parsedRecipes})


@app.route('/search/<keyword>', methods=['GET'])
def search_recipes(keyword):
    recipes = list(db.dbrecipefilter.find({}, {'_id': False}))
    searchedRecipe = []
    parsedRecipe = []
    for i in range(0, len(recipes)):
        ingreIndex = 1
        while True:
            key = 'ingredient' + str(ingreIndex)
            if key in recipes[i]:
                if keyword in recipes[i][key] or recipes[i][key] in keyword:
                    searchedRecipe.append(recipes[i])
                    break
            else:
                break
            ingreIndex += 1
    view_recipes_help([], searchedRecipe, parsedRecipe)
    return jsonify({'recipes': parsedRecipe})


@app.route('/filter/<keyword>', methods=['POST'])
def filter_recipes(keyword):
    # category_receive = request.form['category_give']
    recipes = list(db.dbrecipefilter.find({}, {'_id': False}))
    parsedRecipes = []
    keylist = []
    keylist.append(keyword)
    view_recipes_help(keylist, recipes, parsedRecipes)

    return jsonify({'recipes': parsedRecipes})


@app.route('/wishlist')
def mywish():
    token_receive = request.cookies.get('mytoken')
    if token_receive is not None:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_id = payload["id"]
        return render_template("mypage_wishlist.html",user_info=user_id)
    else:
        return render_template('login.html')


@app.route('/wishlistplus', methods=['GET'])
def wishplus():
    token_receive = request.cookies.get('mytoken')
    if token_receive is not None:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_id =payload["id"]
        title = request.args.get('title')
        print(title)
        mywish_ing = list(db.myrecipe.find({'title': title}, {'_id': False}))
        wishIdlist = []
        for ing in mywish_ing:
            wishIdlist.append(ing['user_id'])

        if mywish_ing:
            if user_id in wishIdlist:
                flash("이미 추가된 레시피입니다.")
            else:
                recipe = db.dbrecipefilter.find_one({'title': title}, {'_id': False})
                recipe['user_id'] =user_id
                #print(recipe)
                db.myrecipe.insert_one(recipe)
                flash("찜완료!")
        else:
            recipe = db.dbrecipefilter.find_one({'title': title}, {'_id': False})
            print(recipe)
            recipe['user_id'] = user_id
            # print(recipe)
            db.myrecipe.insert_one(recipe)
            flash("찜완료!")
        return redirect("/")
    else:
        flash("로그인해주세요!")
        return render_template("login.html")

@app.route('/wishlistminus', methods=['GET'])
def wishminus():
    title = request.args.get('title')
    db.myrecipe.delete_one({'title':title})
    flash("찜삭제 완료!")
    return redirect("/wishlist")

@app.route('/myrecipeview', methods=['GET'])
def my_recipe_view():
    token_receive = request.cookies.get('mytoken')

    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    recipes = list(db.myrecipe.find({'user_id':payload["id"]}, {'_id': False}))
    parsedRecipes = []
    for i in range(0, len(recipes)):
        output = {'title': recipes[i]['title'], 'hyperlink': recipes[i]['hyperlink'], 'image': recipes[i]['image']}
        if 'description' in recipes[i]:
            output['description'] = recipes[i]['description']
        ingredients = []
        category = []
        for j in range(0, 5):
            key = 'category' + str(j)
            if key in recipes[i]:
                category.append(recipes[i][key])
        categorys = ''
        for j in range(0, len(category)):
            categorys += category[j] + ' '

        ingreIndex = 1
        while True:
            key = 'ingredient' + str(ingreIndex)
            if key in recipes[i]:
                ingredients.append(recipes[i][key])
            else:
                break
            ingreIndex += 1

        allIngredients = ''
        for j in range(0, len(ingredients)):
            allIngredients += ingredients[j] + ' '

        output['ingredient'] = allIngredients
        output['category'] = categorys
        parsedRecipes.append(output)

    return jsonify({'recipes': parsedRecipes})


# 마이페이지(개인정보 수정) 이동
@app.route('/mypage_info', methods=['GET'])
def mypage():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        # print(user_info) 토큰으로 받아온 값 확인
        return render_template('mypage_info.html', user_info=payload["id"])
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


# 회원정보 수정
@app.route('/update_info', methods=['POST'])
def update_info():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        password_receive = request.form['password_give']
        password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
        nickname_receive = request.form['nickname_give']
        meat_receive = request.form['meat_give']
        seafood_receive = request.form['seafood_give']
        vegetable_receive = request.form['vegetable_give']
        grain_receive = request.form['grain_give']
        dairy_receive = request.form['dairy_give']

        revised_doc = {
            "password": password_hash,  # 비밀번호
            "nickname": nickname_receive,  # 닉네임
            "meat": meat_receive,  # 육류
            "seafood": seafood_receive,  # 해산물
            "vegetable": vegetable_receive,  # 채소
            "grain": grain_receive,  # 곡류
            "dairy": dairy_receive,  # 유제품
        }

        db.users.update_one({'username': payload['id']}, {'$set': revised_doc})
        # print(user_info) 토큰으로 받아온 값 확인
        return jsonify({"result": "success", 'msg': '개인정보 수정완료!'})
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


# 404 에러 처리
@app.errorhandler(404)
def page_not_found(error):
	return "페이지가 없습니다. URL를 확인 하세요", 404

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
