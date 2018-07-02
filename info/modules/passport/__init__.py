from flask import Blueprint

# 创建蓝图，并设置蓝图的前缀
passport_blu = Blueprint("possport", __name__, url_prefix="/passport")

from info.modules.passport import views
