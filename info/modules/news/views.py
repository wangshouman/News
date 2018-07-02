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


@news_blue.route('/comment_like', methods=["POST"])
@user_login_data
def set_comment_like():
    """评论点赞"""

    if not g.user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    # 获取参数
    comment_id = request.json.get("comment_id")
    news_id = request.json.get("news_id")
    action = request.json.get("action")

    # 判断参数
    if not all([comment_id, news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if action not in ("add", "remove"):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 查询评论数据
    try:
        comment = Comment.query.get(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据失败")

    if not comment:
        return jsonify(errno=RET.NODATA, errmsg="评论数据不存在")

    if action == "add":
        comment_like = CommentLike.query.filter_by(comment_id=comment_id, user_id=g.user.id).first()
        if not comment_like:
            comment_like = CommentLike()
            comment_like.comment_id = comment_id
            comment_like.user_id = g.user.id
            db.session.add(comment_like)
            # 增加点赞条数
            comment.like_count += 1
    else:
        # 删除点赞数据
        comment_like = CommentLike.query.filter_by(comment_id=comment_id, user_id=g.user.id).first()
        if comment_like:
            db.session.delete(comment_like)
            # 减小点赞条数
            comment.like_count -= 1

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="操作失败")

    return jsonify(errno=RET.OK, errmsg="操作成功")


@news_blue.route('/followed_user', methods=["POST"])
@user_login_data
def followed_user():
    """关注/取消关注用户"""
    if not g.user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    user_id = request.json.get("user_id")
    action = request.json.get("action")

    if not all([user_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if action not in ("follow", "unfollow"):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 查询到关注的用户信息
    try:
        target_user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据库失败")

    if not target_user:
        return jsonify(errno=RET.NODATA, errmsg="未查询到用户数据")

    # 根据不同操作做不同逻辑
    if action == "follow":
        if target_user.followers.filter(User.id == g.user.id).count() > 0:
            return jsonify(errno=RET.DATAEXIST, errmsg="当前已关注")
        target_user.followers.append(g.user)
    else:
        if target_user.followers.filter(User.id == g.user.id).count() > 0:
            target_user.followers.remove(g.user)

    # 保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据保存错误")

    return jsonify(errno=RET.OK, errmsg="操作成功")


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
    # 当前登录用户是否关注当前的新闻的作者
    is_followed = False
    # 已经登录
    if user:
        if news in user.collection_news:
            is_collected = True
            # 用户登录&有作者信息
    if user and news.user:
        # 判断该作者的粉丝中有我关注
        if user in news.user.followers:
            is_followed = True


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

    # 获取当前新闻的评论
    comments = None
    try:
        comments = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)

    comment_like_ids = []
    if g.user:
        # 如果当前用户已登录
        try:
            comment_ids = [comment.id for comment in comments]
            if len(comment_ids) > 0:
                # 取到当前用户在当前新闻的所有评论点赞的记录
                comment_likes = CommentLike.query.filter(CommentLike.comment_id.in_(comment_ids),
                                                         CommentLike.user_id == g.user.id).all()
                # 取出记录中所有的评论id
                comment_like_ids = [comment_like.comment_id for comment_like in comment_likes]
        except Exception as e:
            current_app.logger.error(e)

    comment_list = []
    for item in comments if comments else []:
        comment_dict = item.to_dict()
        comment_dict["is_like"] = False
        # 判断用户是否点赞该评论
        if g.user and item.id in comment_like_ids:
            comment_dict["is_like"] = True
        comment_list.append(comment_dict)

    data = {
        # 为了方便返回所需要的数据, 我们开发中一般会自定义to_dict函数
        # user有值, 就返回前面的数据, 没有值, 就返回None --> 模板就解析不出来数据
        # 模型转字典
        'user': user.to_dict() if user else None,
        "click_news_list": click_news_list,
        "news": news.to_dict(),
        "is_collected": is_collected,
        "comment_list": comment_list,
        "is_followed": is_followed
    }

    return render_template("news/detail.html", data=data)
