from flask import current_app
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from config import *
from info import create_app, db
from info import models
from info.models import User

app = create_app(DevelopmenConfig)
manager = Manager(app)
Migrate(app, db)
manager.add_command("db", MigrateCommand)


@manager.option("-n", "-name", dest="name")
@manager.option("-p", "-password", dest="password")
def createsuperuser(name, password):
    # 参数的完整性
    if not all([name, password]):
        print("参数不足")
        return

    # 创建模型
    admin = User()
    admin.mobile = name
    admin.nick_name = name
    admin.password = password
    admin.is_admin = True

    # 提交数据库
    try:
        db.session.add(admin)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return

if __name__ == '__main__':
    # print(app.url_map)
    manager.run()
