import random
import re
from flask import current_app, jsonify
from flask import make_response
from flask import request
from flask import session

from info import constants, db
from info import redis_store
from info.libs.yuntongxun.sms import CCP
from info.models import User
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET
from info.modules.passport import passport_blu


@passport_blu.route('/logout', methods=["POST"])
def logout():

    session.pop("user_id", None)
    session.pop("nick_name", None)
    session.pop("is_admin", None)

    return jsonify(errno=RET.OK, errmsg="Ok")


@passport_blu.route('/login', methods=["POST"])
def login():
    # 1.获取参数
    json_data = request.json
    mobile = json_data.get("mobile")
    password = json_data.get("password")
    # 1.1 校验数据的完整性
    if not all([mobile, password]):
        return jsonify(errno=RET.NODATA, errmsg="参数错误")

    # 2.从数据库查询出指定的用户
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库读取错误")

    # 3,校验密码

    if not user or not user.check_passowrd(password):
        return jsonify(errno=RET.NODATA, errmsg="用户不存在,请先注册")

    # 4.设置session的值
    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session["is_admin"] = user.is_admin
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)

    return jsonify(errno=RET.OK, errmsg="ok")


@passport_blu.route('/register', methods=["POST"])
def register():
    # 1.获取手机号,验证码
    json_data = request.json
    mobile = json_data.get("mobile")
    sms_code = json_data.get("smscode")
    password = json_data.get("password")

    # 2验证参数的完整性
    if not all([mobile, sms_code, password]):
        return jsonify(errno=RET.DATAERR, errmsg="参数错误")

    if not re.match(r"^1[345678][0-9]{9}$", mobile):
        return jsonify(errno=RET.DATAERR, errmsg="手机号填写有误")

    # 3.对比验证码
    try:
        real_sms_code = redis_store.get("SMS_" + mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据库存储失败")

    if not real_sms_code:
        return jsonify(errno=RET.DATAERR, errmsg="数据库读取失败")

    if real_sms_code != sms_code:
        return jsonify(errno=RET.DATAERR, errmsg="验证码失败")

    # 删除短信缓存
    try:
        redis_store.delete("SMS_" + mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="删除操作失败")
    # 4. 用户注册
    try:
        user_model = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsf="数据库读取失败")

    if user_model:
        return jsonify(errno=RET.DATAEXIST, errmsg="用户已经存在")

    # 4.1 创建模型
    user = User()
    user.nick_name = mobile
    user.mobile = mobile
    # 调用了password属性方法，实现了hash加密
    user.password = password
    # 4.2 提交
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库操作错误")

    # 5.设置登录
    try:
        session['nick_name'] = mobile
        session['user_id'] = user.id
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="session 保存redis失败")

    return jsonify(errno=RET.OK, errmsg="请求成功")


@passport_blu.route('/sms_code', methods=["POST"])
def sms_code():
    """验证码功能"""
    # 1. 接收参数并判断是否有参数
    json_data = request.json
    mobile = json_data.get("mobile")
    image_code = json_data.get("image_code")
    image_code_id = json_data.get("image_code_id")

    # 校验参数的完整性
    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.DATAERR, errmsg="参数错误")

    # 判断手机号的正确性
    if not re.match(r"^1[345678][0-9]{9}$", mobile):
        return jsonify(errno=RET.DATAERR, errmsg="手机号填写错误")

    # 2.读取redis中的图片验证码
    try:
        real_image_code_id = redis_store.get("ImageCode_" + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAEXIST, errmsg="读取数据库参数失败")

    # 2.1 数据过期
    if not real_image_code_id:
        return jsonify(errno=RET.DATAEXIST, errmsg="验证码已过期")

    # 2.2 填写数据和数据库的进行比较
    if real_image_code_id.lower() != image_code.lower():
        return jsonify(errno=RET.DATAERR, errmsg="验证码或者手机号错误")

    # 3.短信验证
    result = random.randint(0, 999999)
    sms_code = "%06d" % result
    current_app.logger.debug(" 验证码是:%s" % sms_code)
    result = CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES / 60], "1")
    if result != "000000":
        return jsonify(errno=RET.NODATA, errmsg="短信发送失败")

    # 4.存储短信验证码
    try:
        redis_store.setex("SMS_" + mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="redis存储失败")

    return jsonify(errno=RET.OK, errmsg="发送成功")


@passport_blu.route("/image_code")
def get_image_code():
    # 1. 获取当前图片的验证编号
    code_id = request.args.get("code_id")
    # 生成验证码
    name, text, image = captcha.generate_captcha()
    try:
        # 保存当前生成的图片验证码内容
        redis_store.setex("ImageCode_" + code_id, constants.IMAGE_CODE_REDIS_EXPIRES, text)
    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify(errno=RET.DATAERR, errmsg="保存图片验证码失败"))
    # 返回响应内容
    resp = make_response(image)

    # 设置内容类型
    resp.headers['Content-Type'] = 'image/jpg'

    return resp
