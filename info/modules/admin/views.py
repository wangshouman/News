from flask import current_app
from flask import g, jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for

from info.models import User
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import admin_blu


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
