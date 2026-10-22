#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把本目录的静态文件部署到 Cloudflare Pages（Direct Upload，不需要 Node/wrangler）

首次使用：
  1. https://dash.cloudflare.com/profile/api-tokens  → Create Custom Token
     权限：Account - Cloudflare Pages - Edit
     账户资源：选中你的账户
  2. Account ID 在控制台右侧栏（或 Overview 页面）复制

运行（PowerShell）：
  $env:CLOUDFLARE_ACCOUNT_ID = "你的 Account ID"
  $env:CLOUDFLARE_API_TOKEN  = "你的 API Token"
  python deploy_cloudflare.py

可选参数：
  python deploy_cloudflare.py --project jiafen --dir .
"""

import argparse
import io
import json
import os
import sys
import urllib.request
import urllib.error
import uuid

try:
    import blake3
except ImportError:
    print("缺少 blake3 库，请先运行：pip install blake3")
    sys.exit(1)

BASE = "https://api.cloudflare.com/client/v4"

# 只上传站点需要的静态文件；supabase.sql 含数据库结构，不对外发布
STATIC_FILES = ["index.html", "manifest.json", "icon.svg"]


def api(method, url, token, data=None, content_type=None, timeout=180):
    headers = {"Authorization": "Bearer " + token}
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except ValueError:
            return {"success": False, "errors": [{"message": raw[:400]}]}
    except urllib.error.URLError as e:
        return {"success": False, "errors": [{"message": "网络错误：%s" % e.reason}]}


def build_multipart(base_dir, files, branch):
    boundary = "----cfPages" + uuid.uuid4().hex

    # Cloudflare 规定：manifest = { 文件路径: BLAKE3哈希 }，
    # 文件字段的字段名 = BLAKE3哈希，值为文件内容
    manifest = {}
    contents = {}
    for rel in files:
        with open(os.path.join(base_dir, rel), "rb") as f:
            data = f.read()
        h = blake3.blake3(data).hexdigest()
        manifest[rel] = h
        contents[h] = data

    buf = io.BytesIO()

    def add_field(name, content, ctype="text/plain", filename=None):
        buf.write(("--%s\r\n" % boundary).encode("utf-8"))
        disp = 'Content-Disposition: form-data; name="%s"' % name
        if filename:
            disp += '; filename="%s"' % filename
        buf.write((disp + "\r\n").encode("utf-8"))
        buf.write(("Content-Type: %s\r\n\r\n" % ctype).encode("utf-8"))
        buf.write(content)
        buf.write(b"\r\n")

    add_field("manifest", json.dumps(manifest).encode("utf-8"), "application/json")
    # 显式声明分支，确保部署落到生产域名而不是预览域名
    add_field("branch", branch.encode("utf-8"))

    for h, data in contents.items():
        add_field(h, data, "application/octet-stream", filename=h)

    buf.write(("--%s--\r\n" % boundary).encode("utf-8"))
    return boundary, buf.getvalue()


def ensure_project(token, account_id, project):
    url = "{}/accounts/{}/pages/projects".format(BASE, account_id)
    body = json.dumps({"name": project, "production_branch": "main"}).encode("utf-8")
    res = api("POST", url, token, data=body, content_type="application/json")
    if res.get("success"):
        print("✔ 已创建 Pages 项目：%s" % project)
        return True
    codes = [e.get("code") for e in res.get("errors", [])]
    if any(c in (10502,) for c in codes) or "already exists" in json.dumps(res, ensure_ascii=False):
        return True
    print("✘ 创建项目失败：%s" % json.dumps(res.get("errors"), ensure_ascii=False))
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=os.environ.get("CF_PAGES_PROJECT", "jiafen"))
    parser.add_argument("--branch", default=os.environ.get("CF_PAGES_BRANCH", "main"))
    parser.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)))
    args = parser.parse_args()

    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if not token or not account_id:
        print("缺少凭据，请先设置环境变量：\n"
              "  $env:CLOUDFLARE_ACCOUNT_ID = \"...\"\n"
              "  $env:CLOUDFLARE_API_TOKEN  = \"...\"")
        sys.exit(1)

    base_dir = os.path.abspath(args.dir)
    missing = [f for f in STATIC_FILES if not os.path.isfile(os.path.join(base_dir, f))]
    if missing:
        print("✘ 缺少文件：%s" % ", ".join(missing))
        sys.exit(1)

    if not ensure_project(token, account_id, args.project):
        sys.exit(1)

    boundary, payload = build_multipart(base_dir, STATIC_FILES, args.branch)
    url = "{}/accounts/{}/pages/projects/{}/deployments".format(BASE, account_id, args.project)
    res = api("POST", url, token, data=payload,
              content_type="multipart/form-data; boundary=%s" % boundary)

    if not res.get("success"):
        print("✘ 部署失败：%s" % json.dumps(res.get("errors"), ensure_ascii=False))
        sys.exit(1)

    result = res.get("result", {})
    env = result.get("environment") or ("production" if result.get("production") else "preview")
    project = result.get("project_name", args.project)
    print("\n🎉 部署成功！环境：%s" % env)
    print("   本次快照：%s" % result.get("url", ""))
    print("   生产入口：https://%s.pages.dev" % project)
    if env != "production":
        print("⚠ 本次是预览部署。若生产域名 404，请到控制台确认项目的生产分支，"
              "并重跑：python deploy_cloudflare.py --branch <生产分支名>")


if __name__ == "__main__":
    main()
