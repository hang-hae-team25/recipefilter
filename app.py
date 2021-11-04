from pymongo import MongoClient
import jwt
import datetime
import hashlib
from flask import Flask, render_template, jsonify, request, redirect, url_for,flash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

SECRET_KEY = 'SPARTA'
app.secret_key=SECRET_KEY
client = MongoClient('localhost', 27017)
db = client.dbrecipefilter


@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        return render_template('index.html')
      
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


def view_recipes_help(recipes, parsedRecipes):
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
        if 'filter' in recipes[i]:
            output['filter'] = 'Y'
        parsedRecipes.append(output)


@app.route('/recipes', methods=['GET'])
def view_recipes():
    recipes = list(db.dbrecipefilter.find({}, {'_id': False}))
    parsedRecipes = []
    view_recipes_help(recipes, parsedRecipes)
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
    view_recipes_help(searchedRecipe, parsedRecipe)
    return jsonify({'recipes': parsedRecipe})

@app.route('/filter/<keyword>', methods=['POST'])
def filter_recipes(keyword):
    # category_receive = request.form['category_give']
    recipes = list(db.dbrecipefilter.find({}, {'_id': False}))
    parsedRecipes = []
    for recipe in recipes:
        if keyword in recipe:
            recipe['filter'] = 'Y'
    view_recipes_help(recipes, parsedRecipes)

    return jsonify({'recipes': parsedRecipes})


@app.route('/wishlist')
def mywish():
    token_receive = request.cookies.get('mytoken')
    if token_receive is not None:
        return render_template("mypage_wishlist.html")
    else:
        return render_template('login.html')

@app.route('/wishlistplus', methods=['GET'])
def wishplus():
    token_receive = request.cookies.get('mytoken')
    title = request.args.get('title')
    recipe = db.dbrecipefilter.find_one({'title': title},{'_id':False})
    recipe['user']='user'
    print(recipe)

    db.myrecipe.insert_one(recipe)
    flash("찜완료!")
    return redirect("/")

@app.route('/wishlistminus', methods=['GET'])
def wishminus():
    title = request.args.get('title')
    db.myrecipe.delete_one({'title':title})
    flash("찜삭제 완료!")
    return redirect("/wishlist")

@app.route('/myrecipeview', methods=['GET'])
def my_recipe_view():
    recipes = list(db.myrecipe.find({'user':'user'}, {'_id': False}))
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

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
