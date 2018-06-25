from flask import abort
from flask import g
from flask import redirect
from flask import render_template
from info.utils.common import user_login_data
from . import views
from flask import current_app, jsonify
from flask import make_response
from flask import request
from flask import session
from info import constants, db
from info import redis_store
from info.models import *
from info.utils.response_code import RET
from info.modules.profile import profile_blu
from info.utils.image_storage import storage


@profile_blu.route('/news_list')
@user_login_data
def news_list():
    # 获取用户信息
    user = g.user

    # 获取参数
    page = request.args.get("p", 1)

    # 校验参数
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    news_li = []
    current_page = 1
    current_page = 1

    # 查询发布的新闻
    try:
        paginate = News.query.filter(News.user_id == user.id).paginate(page, constants.USER_COLLECTION_MAX_NEWS, False)
        news_li = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="读取数据错误")

    # 模型转字典
    news_list = []
    for news in news_li:
        news_list.append(news.to_review_dict())

    data = {
        "user": user.to_dict(),
        "news_list": news_list,
        "total_page": total_page,
        "current_page": current_page
    }

    return render_template("news/user_news_list.html", data=data)


@profile_blu.route('/news_release', methods=["POST", "GET"])
@user_login_data
def news_release():
    user = g.user
    # 判断请求方式
    if request.method == "GET":

        categories = []

        # 获取新闻的分类
        try:
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)

        # 模型转列表
        category_list = []
        for category in categories:
            category_list.append(category.to_dict())

        # 删除"最新"的分类
        category_list.pop(0)

        data = {
            "user": user.to_dict(),
            "categories": category_list
        }

        return render_template("news/user_news_release.html", data=data)

    # 发布新闻进行Post请求

    # 获取参数
    title = request.form.get("title")
    category_id = request.form.get("category_id")
    digest = request.form.get("digest")
    index_image = request.files.get("index_image")
    content = request.form.get("content")

    # 校验参数
    if not all([title, category_id, digest, index_image, content]):
        return jsonify(errno=RET.NODATA, errmsg="数据错误")

    # 判断分类id 是否存在
    try:
        category_name = Category.query.get(category_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据库错误")

    if not category_name:
        return jsonify(errno=RET.NODATA, errmsg="分类不存在")

    # 判断图片是否读取程二进制
    image_data = None
    try:
        image_data = index_image.read()
    except Exception as e:
        current_app.logger.error(e)

    # 上传骑牛云保存图片
    try:
        image_key = storage(image_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="骑牛云上传失败")

    # 逻辑判断创建模型
    news = News()
    news.title = title
    news.source = "个人中心"
    news.digest = digest
    news.category_id = category_id
    news.content = content
    news.user_id = user.id
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + image_key

    # 设置状态
    news.status = 1  # 代码正在审核中

    # 提交数据库
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="提交失败")

    return jsonify(errno=RET.OK, errmsg="发表成功")


@profile_blu.route('/collection')
@user_login_data
def collection():
    # 获取页数
    p = request.args.get("p", 1)
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    user = g.user

    collections = []
    current_page = 1
    total_page = 1

    # 查找用户收藏的新闻
    try:
        paginate = user.collection_news.paginate(p, constants.USER_FOLLOWED_MAX_COUNT, False)
        collections = paginate.items
        total_page = paginate.pages
        current_page = paginate.page
    except Exception as e:
        current_app.logger.error(e)

    # 收场列表
    collection_dict_li = []
    for news in collections:
        collection_dict_li.append(news.to_basic_dict())

    data = {
        "collections": collection_dict_li,
        "total_page": total_page,
        "current_page": current_page
    }

    return render_template("news/user_collection.html", data=data)


@profile_blu.route('/pass_info', methods=["POST", "GET"])
@user_login_data
def pass_info():
    # 获取用户
    user = g.user

    if request.method == "GET":
        return render_template("news/user_pass_info.html", data={"user": user})

    # 获取参数
    old_password = request.json.get("old_password")
    new_password = request.json.get("new_password")
    # 校验参数
    if not all([old_password, new_password]):
        return jsonify(errno=RET.NODATA, errmsg="数据错误")

    # 判断用户和密码的正确性
    if not user.check_passowrd(old_password):
        return jsonify(errno=RET.DATAERR, errmsg="密码不正确")

    user.password = new_password

    # 提交数据库
    try:

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="提交数据库失败")

    return jsonify(errno=RET.OK, errmsg="Ok")


@profile_blu.route('/pic_info', methods=["POST", "GET"])
@user_login_data
def pic_info():
    # 获取user用户
    user = g.user

    # 判断请求方式
    if request.method == "GET":
        return render_template("news/user_pic_info.html", data={"user": user, "title": constants.QINIU_DOMIN_PREFIX})

    # 获取文件信息
    try:
        image_file = request.files.get("avatar").read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据错误")

    # 上传文件
    try:
        url = storage(image_file)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="上传图片错误")

    # 将图片地址加载到数据库中
    user.avatar_url = url

    # 提交数据库
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库数据错误")

    return jsonify(errno=RET.OK, errmsg="OK", data={"avatar_url": constants.QINIU_DOMIN_PREFIX + url})


@profile_blu.route('/base_info', methods=["POST", "GET"])
@user_login_data
def base_info():
    # 判断用户的状态
    user = g.user

    if request.method == "GET":
        return render_template("news/user_base_info.html", data={"user": user.to_dict()})

    # 获取参数
    signature = request.json.get("signature")
    nick_name = request.json.get("nick_name")
    gender = request.json.get("gender")

    # 校验参数
    if not all([signature, nick_name, gender]):
        return jsonify(errno=RET.DATAERR, errmsg="数据错误")

    if gender not in (["MAN", "WOMEN"]):
        return jsonify(errno=RET.DATAERR, errmsg="数据错误")

    # 逻辑处理
    user.signature = signature
    user.nick_name = nick_name
    user.gender = gender

    # 提交数据库
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        abort(404)

        # 设置session
    session["nick_name"] = user.nick_name

    return jsonify(errno=RET.OK, errmsg="发表成功")


@profile_blu.route('/user_info')
@user_login_data
def get_user_info():
    # 判断用户的状态
    user = g.user

    if not user:
        return redirect("/")

    data = {
        "user": user.to_dict()
    }

    return render_template("news/user.html", data=data)
