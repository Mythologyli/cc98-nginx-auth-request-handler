# CC98 Nginx Auth Request 验证后端

用于给 Nginx 站点添加 CC98 验证。此后端可以同时为多个站点提供独立验证。

## 创建应用

1. 前往 [https://openid.cc98.org/App/Create](https://openid.cc98.org/App/Create) 创建应用

2. 重定向地址填写

    例如，如果你的应用部署在 `https://example.com`，则重定向地址填写 `https://example.com/oauth2/callback`

3. 授权类型选择授权码验证

4. 授权领域选择用户标识

## 部署验证后端

1. 克隆项目并安装依赖

    ```bash
    git clone https://github.com/Mythologyli/cc98-nginx-auth-request-handler.git
    cd cc98-nginx-auth-request-handler
    python3 -m venv .venv
    source .venv/bin/activate
    pip3 install -r requirements.txt
    cp config.json.example config.json
    ```

2. 编辑 `config.json`

    ```json
    {
        "host": "0.0.0.0",
        "port": 4001,
        "expires": 604800,
        "client_id": "asdfghjkl",
        "client_secret": "asdfghjkl"
    }
    ```

    + host: 绑定主机
    + port: 绑定端口
    + expires: 认证有效期，单位为秒
    + client_id: 应用标识
    + client_secret: 应用机密

3. 运行

    ```bash
    python3 main.py
    ```

## 配置 Nginx

1. 确保包含 [ngx_http_auth_request_module](http://nginx.org/en/docs/http/ngx_http_auth_request_module.html) 模块

2. 在原有站点配置中添加如下配置

    ```
    # 反向代理
    location /login {
        proxy_pass http://127.0.0.1:4001/login;
    }

    # 反向代理
    location /oauth2/callback {
        proxy_pass http://127.0.0.1:4001/oauth2/callback;
    }

    # 鉴权失败则重定向到登录页面
    location @error401 {
        return 302 https://example.com/login?url=https://$http_host$request_uri;
    }

    # 鉴权接口
    location /auth {
        internal;
        proxy_pass http://127.0.0.1:4001/auth;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
    }

    location / {
        auth_request /auth;
        error_page 401 = @error401;
    }
    ```