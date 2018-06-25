from flask import abort
from flask import current_app, jsonify
from flask import g

from flask import request
from flask import session

from info import constants
from info.models import *
from info.modules.news import news_blue
from flask import render_template

from info.utils.common import user_login_data
from info.utils.response_code import RET


@news_blue.route("/comment_delete", methods=["POST"])
@user_login_data
def comment_delete():
    # 获取用户的登录状态
    user = g.user

    # 获取参数
    news_id = request.json.get("news_id")
    comment_id = request.json.get("parent_id")

    # 校验参数
    if not all([news_id, comment_id]):
        return jsonify(errno=RET.DATAERR, errmsg="数据错误")

    # 逻辑判断
    try:
        comment = Comment.query.get(comment_id)
        db.session.delete(comment)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="读取失败")

    if not comment:
        return jsonify(errno=RET.NODATA, errmsg="已过期")

    # 删除评论
    # 提交数据库
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        abort(404)

    return jsonify(errno=RET.OK, errmsg="Ok")


@news_blue.route("/news_comment", methods=["POST"])
@user_login_data
def news_comment():
    # 判断用户是否存在
    user = g.user

    # 获取参数
    news_id = request.json.get("news_id")
    comment = request.json.get("comment")
    parent_id = request.json.get("parent_id")

    # 校验参数
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    if not all([news_id, comment]):
        return jsonify(errno=RET.DATAERR, errmsg="数据错误")

    # 逻辑判断
    # 　判断新闻是否存在
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="读取失败")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="数据错误")

    # 创建模型
    comment_model = Comment()
    comment_model.user_id = user.id
    comment_model.news_id = news.id
    comment_model.content = comment
    if parent_id:
        comment_model.parent_id = parent_id

    try:
        db.session.add(comment_model)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据库错误")

    return jsonify(errno=RET.OK, errmsg="发表成功", data=comment_model.to_dict())


@news_blue.route("/news_collect", methods=["POST"])
@user_login_data
def news_collect():
    # 判断用户是否登录
    user = g.user

    # 　获取参数
    news_id = request.json.get("news_id")
    action = request.json.get("action")

    # 校验参数
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    if not all([news_id, action]):
        return jsonify(errno=RET.NODATA, errmsg="数据错误")

    if action not in ["collect", "cancel_collect"]:
        return jsonify(errno=RET.NODATA, errmsg="数据错误")

    # 逻辑判断
    # 通过ｉｄ查找新闻
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库错误")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="数据错误")

    # 判断是否收藏
    if action == "collect":
        if news not in user.collection_news:
            user.collection_news.append(news)
    else:
        if news in user.collection_news:
            user.collection_news.remove(news)

    # 提交数据
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库错误")

    return jsonify(errno=RET.OK, errmsg="成功")


@news_blue.route("/<int:news_id>")
@user_login_data
def news_detail(news_id):
    # 从临时变量中取出user
    user = g.user

    # 点击排行榜的设置
    news_list = None

    # 数据库查询数据,点击排行榜内容
    try:
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)

    click_news_list = []

    for news in news_list if news_list else []:
        click_news_list.append(news.to_basic_dict())

    # 查询新闻内容
    news = None

    # 查询数据库获取当前新闻的内容
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        abort(404)

    if not news:
        abort(404)

    news.clicks += 1

    # 提交到数据库
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        abort(404)

    # 4.收藏
    is_collected = False
    # 已经登录
    if user:
        if news in user.collection_news:
            is_collected = True

    # 获取新闻的评论,展示在网页上
    comment_models = []

    try:
        comment_models = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)
        abort(404)

    comment_list = []

    for comment in comment_models:
        comment_list.append(comment.to_dict())

    data = {
        # 为了方便返回所需要的数据, 我们开发中一般会自定义to_dict函数
        # user有值, 就返回前面的数据, 没有值, 就返回None --> 模板就解析不出来数据
        # 模型转字典
        'user': user.to_index_dict() if user else None,
        "click_news_list": click_news_list,
        "news": news.to_dict(),
        "is_collected": is_collected,
        "comment_list": comment_list
    }

    return render_template("news/detail.html", data=data)
