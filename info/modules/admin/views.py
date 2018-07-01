from datetime import datetime, timedelta
import time
from flask import abort
from flask import current_app
from flask import g, jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for

from info import constants
from info.models import *
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import admin_blu


@admin_blu.route("/news_type", methods=["POST", "GET"])
def news_type():
    """分类管理功能"""
    # 判断用户的请求方式
    if request.method == "GET":
        categories = []
        # 查询分类的记录
        categories = Category.query.all()
        # 记录转字典的模型
        category_list = []
        for category in categories:
            category_list.append(category.to_dict())

        # 删除最新的分类
        # category_list.pop(0)

        data = {

            "categories": category_list
        }

        return render_template("admin/news_type.html", data=data)

    # post请求

    category_id = request.json.get("id")
    category_name = request.json.get("name")
    if not category_name:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    # 判断是否有分类id
    if category_id:
        try:
            category = Category.query.get(category_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询数据失败")

        if not category:
            return jsonify(errno=RET.NODATA, errmsg="未查询到分类信息")

        category.name = category_name
    else:
        # 如果没有分类id，则是添加分类
        category = Category()
        category.name = category_name
        db.session.add(category)

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")

    return jsonify(errno=RET.OK, errmsg="保存数据成功")


@admin_blu.route("/news_edit_detail", methods=["POST", "GET"])
def news_edit_detail():
    """编辑功能"""
    # 判断用户的请求行为
    if request.method == "GET":
        # 获取参数
        news_id = request.args.get("news_id")
        # 参数检验
        if not news_id:
            return render_template("admin/news_review_detail.html", data={"errmsg": "未查到此新闻"})

        news = None
        # 查询新闻的记录
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)

        if not news:
            return render_template("admin/news_review_detail.html", data={"errmsg": "未查到此条新闻"})

        # 获取分类数据
        categories = []
        try:
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)

        category_list = []
        c_dict = None
        # 模型记录转成字典的格式
        for category in categories:
            c_dict = category.to_dict()
            c_dict["is_selected"] = False
            if category.id == news.category_id:
                c_dict["is_selected"] = True
            category_list.append(c_dict)

        data = {
            "news": news.to_dict(),
            "categories": category_list
        }

        return render_template("admin/news_edit_detail.html", data=data)

    # post请求,编辑的内容重新提交数据库
    # 获取数据,通过表单获取
    news_id = request.form.get("news_id")
    title = request.form.get("title")
    digest = request.form.get("digest")
    content = request.form.get("content")
    index_image = request.files.get("index_image")
    category_id = request.form.get("category_id")
    # 1.1 判断数据是否有值
    if not all([title, digest, content, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到新闻数据")

    # 1.2 尝试读取图片
    if index_image:
        try:
            index_image = index_image.read()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

        # 2. 将标题图片上传到七牛
        try:
            key = storage(index_image)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.THIRDERR, errmsg="上传图片错误")
        news.index_image_url = constants.MY_QINIU_DOMIN_PREFIX + key
    # 3. 设置相关数据
    news.title = title
    news.digest = digest
    news.content = content
    news.category_id = category_id

    # 4. 保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")
    # 5. 返回结果
    return jsonify(errno=RET.OK, errmsg="编辑成功")


@admin_blu.route("/news_edit")
def news_edit():
    # 获取参数
    page = request.args.get("p", 1)
    keywords = request.args.get("keywords", "")

    # 校验参数
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    # 获取参数
    news = None
    news_li = []
    current_page = 1
    total_page = 1
    try:
        filters = []
        if keywords:
            # 如果查询的关键字存在,就增加查询条件
            filters.append(News.title.contains(keywords))
        # 查询需要审核的新闻
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page,
                                                                                          constants.HOME_PAGE_MAX_NEWS,
                                                                                          False)
        news_li = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    # 转成字典的格式
    news_list = []

    for news in news_li:
        news_list.append(news.to_review_dict())

    data = {
        "news_list": news_list,
        "current_page": current_page,
        "total_page": total_page,
        "keywords": keywords
    }

    return render_template("admin/news_edit.html", data=data)


@admin_blu.route("/news_review_detail", methods=["POST", "GET"])
def news_review_detail():
    """新闻审核"""
    if request.method == "GET":
        # 获取参数
        news_id = request.args.get("news_id")
        # 参数检验
        if not news_id:
            return render_template("admin/news_review_detail.html", data={"errmsg": "未查到此新闻"})

        news = None
        # 查询新闻的记录
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)

        if not news:
            return render_template("admin/news_review_detail.html", data={"errmsg": "未查到此条新闻"})

        data = {
            "news": news.to_dict()
        }

        return render_template("admin/news_review_detail.html", data=data)

    # post请求
    # 获取参数
    news_id = request.json.get("news_id")
    action = request.json.get("action")

    # 校验参数
    if not all(["news_id", "action"]):
        return jsonify(errno=RET.NODATA, errmsg="数据错误")

    if action not in ("accept", "reject"):
        return jsonify(errno=RET.PARAMERR, errmsg="数据错误")

    # 判断新闻是否存在
    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询失败")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查到此条新闻")

    # 判断用户的行为
    if action == "accept":
        news.status = 0
    else:
        reason = request.json.get("reason")
        if not reason:
            return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
        news.reason = reason
        news.status = -1

    # 提交数据库
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据操作失败")

    # 返回数据
    return jsonify(errno=RET.OK, errmsg="发表成功")


@admin_blu.route("/news_review")
def news_review():
    # 获取参数
    page = request.args.get("p", 1)
    keywords = request.args.get("keywords", "")

    # 校验参数
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    # 获取参数
    news = None
    news_li = []
    current_page = 1
    total_page = 1
    try:
        filters = []
        if keywords:
            # 如果查询的关键字存在,就增加查询条件
            filters.append(News.title.contains(keywords))
        # 查询需要审核的新闻
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page,
                                                                                          constants.HOME_PAGE_MAX_NEWS,
                                                                                          False)
        news_li = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    # 转成字典的格式
    news_list = []

    for news in news_li:
        news_list.append(news.to_review_dict())

    data = {
        "news_list": news_list,
        "current_page": current_page,
        "total_page": total_page,
        "keywords": keywords
    }

    return render_template("admin/news_review.html", data=data)


@admin_blu.route("/user_list")
def user_list():
    # 获取参数
    page = request.args.get("p", 1)

    # 校验参数
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    # 获取参数
    user = None
    user_li = []
    current_page = 1
    total_page = 1
    try:
        paginate = User.query.filter(User.is_admin == 0).order_by(User.create_time.desc()).paginate(page,
                                                                                                    constants.HOME_PAGE_MAX_NEWS,
                                                                                                    False)
        user_li = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    # 转成字典的格式
    user_list = []

    for user in user_li:
        user_list.append(user.to_admin_dict())

    data = {
        "users": user_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("admin/user_list.html", data=data)


@admin_blu.route("/user_count")
def user_count():
    user_count = 0

    # 查询总人数
    try:
        user_count = User.query.filter(User.is_admin == 0).count()
    except Exception as e:
        current_app.logger.error(e)
        abort(404)

    # 查询月新增人数
    mon_count = 0
    # 获取到当前时间的
    now = time.localtime()
    try:
        # 格式化时间的格式
        mon_begin_day = "%d-%02d-01" % (now.tm_year, now.tm_mon)
        # 转成能进行比较的形式
        begin_day = datetime.strptime(mon_begin_day, "%Y-%m-%d")
        # 查询数据
        mon_count = User.query.filter(User.is_admin == 0, User.create_time > begin_day).count()
    except Exception as e:
        current_app.logger.error(e)

    # 查询日新增人数
    day_count = 0
    try:
        # 获取当天的时间的00:00:00
        day_begin = "%d-%02d-%02d" % (now.tm_year, now.tm_mon, now.tm_mday)
        # 字符串转成时间的格式
        day_begin_time = datetime.strptime(day_begin, "%Y-%m-%d")
        # 查询数据
        day_count = User.query.filter(User.is_admin == 0, User.create_time > day_begin_time).count()
    except Exception as e:
        current_app.logger.error(e)

    # 获取图表的数据
    # 获取本月的每一天的时间
    now_date = datetime.now()
    now_date = datetime.strptime(now_date.strftime("%Y-%m-%d"), "%Y-%m-%d")

    # 自定义活跃的数目列表和活跃时间的列表
    active_date = []
    active_count = []
    count = 0
    for i in range(1, 31):
        begin_day = now_date - timedelta(days=i)
        end_day = now_date - timedelta(days=(i - 1))
        active_date.append(begin_day.strftime("%Y-%m-%d"))

        try:
            # 最后一次登录的时间为活跃的
            count = User.query.filter(User.is_admin == 0, User.last_login > begin_day,
                                      User.last_login < end_day).count()
        except Exception as e:
            current_app.logger.error(e)

        active_count.append(count)

    # 列表反转,进行数据的正常显示
    active_count.reverse()
    active_date.reverse()

    data = {
        "user_count": user_count,
        "mon_count": mon_count,
        "day_count": day_count,
        "active_count": active_count,
        "active_date": active_date
    }

    return render_template("admin/user_count.html", data=data)


@admin_blu.route('/logout', methods=["POST"])
def logout():
    session.pop("user_id")
    session.pop("nick_name")
    session.pop("is_admin")

    return jsonify(errno=RET.OK, errmsg="发表成功")


@admin_blu.route('/index', methods=["POST", "GET"])
@user_login_data
def admin_index():
    # 获取用户的信息
    user = g.user

    return render_template("admin/index.html", user=user.to_dict())


@admin_blu.route('/login', methods=["POST", "GET"])
@user_login_data
def admin_login():
    # 获取用户信息
    user = g.user
    # 判断登录状态
    if request.method == "GET":
        user_id = session.get("user_id", None)
        is_admin = session.get("is_admin", False)
        if user_id and is_admin:
            return redirect(url_for("admin.admin_index"))
        return render_template("admin/login.html")

    # 登录post请求，获取参数
    username = request.form.get("username")
    password = request.form.get("password")

    # 校验参数
    if not all([username, password]):
        return jsonify(errno=RET.NODATA, errmsg="数据错误")

    try:
        user = User.query.filter(User.mobile == username).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="读取失败")

    if not user and user.check_passowrd(password):
        return jsonify(errno=RET.DATAERR, errmsg="用户或密码错误")

    if not user.is_admin:
        return jsonify(errno=RET.DATAERR, errmsg="非管理员用户")

    # 保持状态
    session["nick_name"] = username
    # session["mobile"] = username
    session["user_id"] = user.id
    session["is_admin"] = True

    # 返回数据
    return redirect(url_for("admin.admin_index"))
