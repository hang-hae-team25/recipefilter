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

# 로그인
@app.route('/sign_in', methods=['POST'])
def sign_in():
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

# 회원가입
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
    # 회원정보 등록처리
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})

# 중복체크
@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})


#요청한 데이터를 상황에 맞게 필터링해서 보내주는 helping function 입니다.
def view_recipes_help(filterKeyword, recipes, parsedRecipes):

    # DB의 전체 레시피 데이터를 for loop으로 조회
    for i in range(0, len(recipes)):
        output = {'title': recipes[i]['title'], 'hyperlink': recipes[i]['hyperlink'], 'image': recipes[i]['image']}

        # description이 없는 경우도 있어서 확인하는 유효성 검사
        if 'description' in recipes[i]:
            output['description'] = recipes[i]['description']
        ingredients = []
        category = []

        # category가 1 ~ 5까지 해물, 고기, 유제품, 탄수화물, 채소류로 나뉘어 있는데
        # 어떤 카테고리에 포함된 레시피 데이터인지 확인
        for j in range(0, 5):
            key = 'category' + str(j + 1)
            if key in recipes[i]:
                category.append(recipes[i][key])
        categorys = ''
        for j in range(0, len(category)):
            categorys += category[j] + ' '

        # 재료는 레시피 별로 몇개가 들어 있는지 알수 없어서 무한루프로 확인후
        # 키가 없다고 나올때 멈추게 했습니다.
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

        # filter 카테고리를 받아서 레시피가 해당 카테고리에 포함되면
        # key값으로 표시를 해서 넣어준다.
        if len(filterKeyword) > 0:
            for keyword in filterKeyword:
                if keyword in recipes[i]:
                    output['filter'] = 'Y'
                    break;

        # parsedRecipe에 넣어 주면 다른 API 함수에서 client 에 전송해준다
        parsedRecipes.append(output)

#code block #1
# DB에 들어있는 모든 데이터를 메인 화면에 뿌려주는 API
@app.route('/recipes', methods=['GET'])
def view_recipes():
    recipes = list(db.dbrecipefilter.find({}, {'_id': False}))
    parsedRecipes = []

    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    user_info = db.users.find_one({"username": payload["id"]})
    # 크롤링한 데이터에 카테고리가 포함이 되지 않아 카테고리를 다섯개로 지정
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


#검색바에 검색한 키워드를 DB데이터와 비교해 응답해주는 API
@app.route('/search/<keyword>', methods=['GET'])
def search_recipes(keyword):
    recipes = list(db.dbrecipefilter.find({}, {'_id': False}))
    searchedRecipe = []
    parsedRecipe = []

    #DB의 모든 레시피 마다의 재료들을 키워드와 비교하여 키워드가 포함되었으면
    #찾은 레시피 데이터를 따로 분류한다.
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

# 카테고리 버튼을 나눠서 선택한 재료가 포함된 레시피를 보내주는 API
@app.route('/filter/<keyword>', methods=['POST'])
def filter_recipes(keyword):

    recipes = list(db.dbrecipefilter.find({}, {'_id': False}))
    parsedRecipes = []
    keylist = []
    keylist.append(keyword)
    view_recipes_help(keylist, recipes, parsedRecipes)

    return jsonify({'recipes': parsedRecipes})

#찜목록가기
@app.route('/wishlist')
def mywish():
    #토큰확인 후 없으면 login으로
    token_receive = request.cookies.get('mytoken')
    if token_receive is not None:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_id = payload["id"]
        return render_template("mypage_wishlist.html",user_info=user_id)
    else:
        return render_template('login.html')

#code block #1
#찜하기
@app.route('/wishlistplus', methods=['GET'])
def wishplus():
    #로그인 중인지 확인
    token_receive = request.cookies.get('mytoken')
    #로그인 중이면
    if token_receive is not None:
        #아이디를 playload에서 빼온다
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_id =payload["id"]
        #html에서 전달된 title로 db에서 find

        title = request.args.get('title')
        print(title)
        mywish_ing = list(db.myrecipe.find({'title': title}, {'_id': False}))
        wishIdlist = []
        for ing in mywish_ing:
            wishIdlist.append(ing['user_id'])
        if mywish_ing:
            # 로그인된 아이디가 이미 찜에 추가한 경우
            if user_id in wishIdlist:
                flash("이미 추가된 레시피입니다.")
            #다른 사용자가 찜에 추가해놓은 경우
            else:
                recipe = db.dbrecipefilter.find_one({'title': title}, {'_id': False})
                recipe['user_id'] =user_id
                #print(recipe)
                db.myrecipe.insert_one(recipe)
                flash("찜완료!")
        # mywish_ing가 빈 리스트이면->db.myrecipe에 넣기
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

#찜목록에서 삭제
@app.route('/wishlistminus', methods=['GET'])
def wishminus():
    title = request.args.get('title')
    db.myrecipe.delete_one({'title':title})
    flash("찜삭제 완료!")
    return redirect("/wishlist")
#찜목록페이지에 myrecipe데이터 뿌리기
@app.route('/myrecipeview', methods=['GET'])
def my_recipe_view():
    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    #db에서 레시피 찾기
    recipes = list(db.myrecipe.find({'user_id':payload["id"]}, {'_id': False}))
    parsedRecipes = []
    for i in range(0, len(recipes)):
        output = {'title': recipes[i]['title'], 'hyperlink': recipes[i]['hyperlink'], 'image': recipes[i]['image']}
        #description이 있는지
        if 'description' in recipes[i]:
            output['description'] = recipes[i]['description']
        ingredients = []
        #어느 category에 포함되는지
        category = []
        for j in range(0, 5):
            key = 'category' + str(j)
            if key in recipes[i]:
                category.append(recipes[i][key])
        categorys = ''
        for j in range(0, len(category)):
            categorys += category[j] + ' '
        #재료는 몇개인지 모름으로key값이 없을 때까지 무한루프
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
        # 개인정보 수정처리
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
