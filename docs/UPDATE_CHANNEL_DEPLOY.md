# 更新通道部署说明（update.ycqinnan.cn）

> 状态：**已上线**（2026-10-29），承载 Desktop Cleaner 的自动更新清单与安装包分发。
> 本文记录真实部署结果，可直接照此重建。

## 1. 为什么需要这份文档

2026-08-31 的审计（P1-1）发现更新通道与真实发布地不一致：应用从
`https://update.ycqinnan.cn/update/latest.json` 拉清单，但该域名在服务器上
**没有 nginx 站点、也没有证书**，服务端自测 `/update/latest.json` 与
`/releases/DesktopCleaner-1.2.0.exe` 均返回 404。

结论：自 1.2.0 起，线上 EXE 的「检查更新」从未成功过。它按设计静默失败
（不阻塞主功能），因此长期未被察觉。

2026-10-29 补齐了站点、证书与产物，通道现为可用状态。

## 2. 现状

| 项 | 值 |
|---|---|
| 域名 | `update.ycqinnan.cn` |
| DNS A 记录 | `111.229.225.123`（腾讯云，Ubuntu 24.04） |
| SSH | 端口 `2222`，root |
| 站点根目录 | `/data/update` |
| 清单路径 | `/data/update/update/latest.json` → `https://update.ycqinnan.cn/update/latest.json` |
| 安装包目录 | `/data/update/releases/` → `https://update.ycqinnan.cn/releases/DesktopCleaner-<ver>.exe` |
| 证书 | Let's Encrypt，`/etc/letsencrypt/live/update.ycqinnan.cn/`，到期 2027-01-27，certbot 自动续期 |
| HTTP 行为 | 301 重定向到 HTTPS |

**为什么是 `/update/update/` 这层嵌套**：URL 路径是 `/update/latest.json`，
站点根为 `/data/update`，所以文件落在 `/data/update/update/latest.json`。
这是刻意保持的：应用侧的 `UPDATE_MANIFEST_URL` 已固化为该路径。

## 3. nginx 配置

文件：`/etc/nginx/sites-available/update`（软链到 `sites-enabled/update`）。

初始为纯 HTTP，`certbot --nginx` 会自动补上 443 与 301 跳转。手工重建时
先放下面的 80 版本，再跑 certbot。

```nginx
# Desktop Cleaner — update channel (update.ycqinnan.cn)
# Static host for the update manifest and versioned release artifacts.
# Layout: /update/latest.json  and  /releases/DesktopCleaner-<ver>.exe
server {
    listen 80;
    listen [::]:80;
    server_name update.ycqinnan.cn;

    root /data/update;

    # Exact-path files only: a static host with no directory listing.
    location / {
        try_files $uri =404;
    }

    access_log /var/log/nginx/update.access.log;
    error_log  /var/log/nginx/update.error.log;
}
```

启用与证书：

```bash
ln -sf /etc/nginx/sites-available/update /etc/nginx/sites-enabled/update
nginx -t && systemctl reload nginx
certbot --nginx -d update.ycqinnan.cn --redirect --non-interactive --agree-tos --keep-until-expiring
```

> `nginx -t` 会输出 softlib / vc 两条 `protocol options redefined for :443` 告警。
> 那是既有站点的历史问题，与本站点无关，不影响 reload。

## 4. 发布一个新版本

以 1.2.1 → 1.2.2 为例。

### 4.1 本地：构建并统一元数据

```bash
cd <项目根>
"D:/Software/Python313/python" -m PyInstaller --noconfirm --clean build.spec
mv dist/DesktopCleaner.exe dist/DesktopCleaner-1.2.2.exe
```

> **必须显式指定解释器**。`build.bat` 内部调用裸 `python`，而 PATH 上可能
> 是未安装 PySide6/PyInstaller 的解释器；本项目真实构建环境是
> `D:\Software\Python313`（Python 3.13.14 / PySide6 6.12.0 / PyInstaller 6.22.3）。

更新 `src/version.py`、`SHA256SUMS.txt`、`update_manifest.json` 三处，保持
`exe == manifest.sha256 == SHA256SUMS` 且 `manifest.latest_version == src`。

### 4.2 上传

```bash
scp -P 2222 -i ~/.ssh/id_ed25519_tencent \
    dist/DesktopCleaner-1.2.2.exe \
    root@111.229.225.123:/data/update/releases/

scp -P 2222 -i ~/.ssh/id_ed25519_tencent \
    update_manifest.json \
    root@111.229.225.123:/data/update/update/latest.json
```

### 4.3 校验远端哈希（不要跳过）

```bash
ssh -p 2222 -i ~/.ssh/id_ed25519_tencent root@111.229.225.123 \
    'sha256sum /data/update/releases/DesktopCleaner-1.2.2.exe'
```

与本地 `SHA256SUMS.txt` 对应行比对。40 MB 传输偶发截断，必须比对。

### 4.4 端到端验证

```bash
"D:/Software/Python313/python" tools/release_validate.py --check-remote
```

期望：`RESULT: PASS`，其中 `remote artifact  remote SHA-256 == local EXE`
表示真的下载了远端包并哈希一致。只跑不带 `--check-remote` 的版本时，
`download artifact` 只做 HTTP 状态检查。

## 5. 关键约束与坑

- **应用读的是服务器，不是仓库**。`src/update/constants.py` 的
  `UPDATE_MANIFEST_URL` 指向本域名；把 `update_manifest.json` 提交进 Git
  **不会**让用户收到更新提示，必须部署到本文第 2 节的路径。
- **`minimum_supported_version` 是强制更新门槛**，改动它会让低于该版本的
  客户端被强制升级。非必要不动（当前 `1.1.1`）。
- **下载 URL 受白名单限制**：`is_allowed_download_url` 只允许 HTTPS +
  `update.ycqinnan.cn` + 默认 443 端口。换域名或加端口会让更新链路直接失效。
- **不要开目录列表**。`try_files $uri =404` 保证只有确切路径可访问。
- **证书续期**：certbot 已注册定时任务；若 80 端口被安全组关掉，HTTP-01
  续期会失败，证书到期后更新检查随之失效。
