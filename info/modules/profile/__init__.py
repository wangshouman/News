from flask import Blueprint

# 创建蓝图，并设置蓝图的前缀
profile_blu = Blueprint("user", __name__, url_prefix="/user")

from . import views
