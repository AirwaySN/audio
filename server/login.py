# 处理mumble的登录逻辑
# https://airwaysn.org/api/v1/public/auth
# json:{ "cid":"1000", "password": "1234"}
# 正确返回200，错误返回400
import sys
import Ice
import Murmur
import requests
import json
import traceback

class AuthenticatorI(Murmur.ServerAuthenticator):
    def __init__(self, server, adapter , serverprx=None):
        self.serverprx = serverprx
        self.server = server
        self.adapter = adapter
        self.online_users = {}  # 存储在线用户的session

    def authenticate(self, name, pw, certificates, certhash, certstrong, current=None):
        try:
            print(f"认证用户: {name}")
            if login(name, pw):
                if name in self.online_users:
                    old_session = self.online_users[name]
                    try:
                        self.serverprx.kickUser(old_session, "您的账号在其他位置登录")
                    except Exception as e:
                        print(f"踢出用户失败: {e}")
                return (int(name), name, [])
            return (-1, "", [])
        except Exception as e:
            print(f"认证异常: {e}")
            traceback.print_exc()
            return (-1, "", [])

    def nameToId(self, name, current=None):
        try:
            return int(name)
        except:
            return -2

    def idToName(self, id, current=None):
        return str(id)

    def userConnected(self, user, current=None):
        self.online_users[user.name] = user.session
        print(f"用户 {user.name} 已连接，session: {user.session}")

    def userDisconnected(self, user, current=None):
        if user.name in self.online_users:
            del self.online_users[user.name]
        print(f"用户 {user.name} 已断开连接")

    def getInfo(self, id, current=None):
        return (False, {})

    def idToTexture(self, id, current=None):
        return []

def login(cid, password):
    url = "https://airwaysn.org/api/v1/public/auth"
    headers = {
        "Content-Type": "application/json",
    }
    data = {
        "cid": str(cid),
        "password": str(password),
    }
    print(f"登录请求: {data}")
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            print (f"登录成功: {response.status_code}, {response.text}")
            return True
        
        else:
            print (f"登录失败: {response.status_code}, {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return False

def main():
    with Ice.initialize(sys.argv) as communicator:
        # 设置Ice连接
        base = communicator.stringToProxy("Meta:tcp -h 127.0.0.1 -p 6502")
        meta = Murmur.MetaPrx.checkedCast(base)
        if not meta:
            print("无法连接到Murmur服务器")
            return

        # 使用正确的ice secret
        context = {"secret": "yoyo14185721"}
        server = meta.getServer(1, context)

        serverprx = Murmur.ServerPrx.checkedCast(server)
        if not serverprx:
            print("无法获取服务器代理")
            return
        
        if not server:
            print("无法获取服务器实例")
            return

        # 创建Ice适配器
        adapter = communicator.createObjectAdapterWithEndpoints(
            "Authenticator", "tcp -h 127.0.0.1")
        adapter.activate()

        # 创建并注册认证器
        auth = AuthenticatorI(server, adapter, serverprx)
        auth_prx = adapter.addWithUUID(auth)
        server_auth = Murmur.ServerAuthenticatorPrx.checkedCast(auth_prx)



        # 设置认证器
        try:
            server.setAuthenticator(server_auth, context)
            print("认证器已设置")
            
            # 保持程序运行
            communicator.waitForShutdown()
        except Ice.Exception as e:
            print(f"Ice异常: {e}")
        finally:
            # 清理
            try:
                server.setAuthenticator(None, context)
            except:
                pass

if __name__ == "__main__":
    main()

