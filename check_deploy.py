#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断 Cloudflare Pages 项目与部署状态。在设置了
CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN 环境变量的窗口中运行。"""
import json
import os
import sys
import urllib.request
import urllib.error

BASE = "https://api.cloudflare.com/client/v4"


def get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"success": False, "errors": json.loads(e.read().decode() or "[]")}


def main():
    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    acct = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if not token or not acct:
        print("缺少环境变量，请先设置 CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN")
        sys.exit(1)

    res = get("{}/accounts/{}/pages/projects".format(BASE, acct), token)
    print("== 账号下所有 Pages 项目 ==")
    if not res.get("success"):
        print(json.dumps(res.get("errors"), ensure_ascii=False))
        sys.exit(1)
    for p in res["result"]:
        print("  项目名: %-14s 生产分支: %-10s 域名: %s"
              % (p["name"], p.get("production_branch"), ",".join(p.get("domains", []))))

    for name in [p["name"] for p in res["result"]]:
        res2 = get("{}/accounts/{}/pages/projects/{}/deployments?per_page=3"
                   .format(BASE, acct, name), token)
        print("\n== 项目 %s 最近部署 ==" % name)
        if not res2.get("success"):
            print("  查询失败:", json.dumps(res2.get("errors"), ensure_ascii=False))
            continue
        for d in res2["result"]:
            stage = d.get("latest_stage") or {}
            print("  %s | %s | %s(%s) | %s"
                  % (d["created_on"][:19], d.get("environment"),
                     stage.get("name"), stage.get("status"), d["url"]))


if __name__ == "__main__":
    main()
