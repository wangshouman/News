from flask import Blueprint
from flask import redirect
from flask import request
from flask import session
from flask import url_for

admin_blu = Blueprint('admin', __name__, url_prefix="/admin")

from . import views


@admin_blu.before_request
def before_request():
    # 判断如果不是登录页面的请求
    if not request.url.endswith(url_for("admin.admin_login")):
        user_id = session.get("user_id")
        is_admin = session.get("is_admin", False)
        # 判断当前是否有用户登录或者是管理源,如果不是直接返回首页
        if not user_id or not is_admin:
            return redirect("/")
