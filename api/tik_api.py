# -*- coding: utf-8 -*-
import re
import json
import html
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import base64

class TukTukAPI:
    def __init__(self):
        # بروكسي Cloudflare الخاص بك لتخطي الحظر
        self.proxy_url = "https://moon-29d4.h-fip.workers.dev/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15",
            "Referer": "https://zx33.tuktuk-sa.online/",
            "Accept": "application/json, text/plain, */*"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_proxied_url(self, target_url):
        target_url = target_url.strip()
        if target_url.startswith("//"): target_url = "https:" + target_url
        elif not target_url.startswith("http"): target_url = "https://" + target_url
        return f"{self.proxy_url}?targetUrl={quote(target_url, safe='')}"

    def decode_base64(self, data_str):
        missing_padding = len(data_str) % 4
        if missing_padding: data_str += "=" * (4 - missing_padding)
        return base64.b64decode(data_str).decode("utf-8")

    def _find_all_servers(self, data):
        servers = []
        if isinstance(data, dict):
            if "link" in data and ("driver" in data or "symbol" in data):
                servers.append(data)
            for value in data.values():
                servers.extend(self._find_all_servers(value))
        elif isinstance(data, list):
            for item in data:
                servers.extend(self._find_all_servers(item))
        return servers

    def _extract_inertia(self, html_content):
        match = re.search(r'data-page=(["\'])(\{.*?\})\1', html_content, re.IGNORECASE | re.DOTALL)
        if match:
            try: return json.loads(html.unescape(match.group(2)))
            except: pass
        return None

    def search_movie(self, imdb_id):
        """تحويل كود IMDB إلى اسم فيلم والبحث عنه للحصول على رابطه المباشر"""
        # 1. جلب بيانات الفيلم مجاناً من Cinemeta
        meta_url = f"https://v3-cinemeta.strem.io/meta/movie/{imdb_id}.json"
        try:
            meta_res = requests.get(meta_url).json()
            movie_name = meta_res.get("meta", {}).get("name", "")
            if not movie_name: return None
            
            print(f"🔎 جاري البحث في الموقع عن: {movie_name}")
            
            # 2. البحث في الموقع عبر البروكسي
            search_url = f"https://zx33.tuktuk-sa.online/?s={quote(movie_name)}"
            res = self.session.get(self.get_proxied_url(search_url), timeout=15)
            soup = BeautifulSoup(res.text, "html.parser")
            
            # 3. استخراج أول رابط يخص فيلم
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "tuktuk-sa.online" in href and ("/فيلم-" in href or "/movie" in href):
                    print(f"🎯 تم العثور على رابط الفيلم: {href}")
                    return href
        except Exception as e:
            print(f"❌ خطأ أثناء البحث: {e}")
        return None

    def get_streams(self, imdb_id):
        """الوظيفة الرئيسية: بحث -> جلب الصفحة -> فك الحماية -> إرجاع الروابط"""
        stremio_streams = []
        
        # جلب رابط الفيلم بناءً على معرف IMDB
        movie_url = self.search_movie(imdb_id)
        if not movie_url:
            return stremio_streams

        try:
            res = self.session.get(self.get_proxied_url(movie_url), timeout=15)
            soup = BeautifulSoup(res.text, "html.parser")
            
            iframe = soup.find("iframe", {"id": "main-video-frame"}) or soup.find("iframe", {"data-crypt": True})
            if iframe and iframe.get("data-crypt"):
                player_url = self.decode_base64(iframe["data-crypt"])
                player_res = self.session.get(self.get_proxied_url(player_url), timeout=15)
                inertia_json = self._extract_inertia(player_res.text)
                
                if inertia_json:
                    version = inertia_json.get("version", "")
                    component = inertia_json.get("component", "")
                    headers = self.headers.copy()
                    headers.update({
                        "X-Inertia": "true",
                        "X-Inertia-Version": version,
                        "X-Inertia-Partial-Data": "streams",
                        "X-Inertia-Partial-Component": component,
                        "Referer": player_url
                    })
                    
                    partial_res = self.session.get(self.get_proxied_url(player_url), headers=headers, timeout=15)
                    servers = self._find_all_servers(partial_res.json())
                    
                    for srv in servers:
                        driver_name = srv.get("driver", srv.get("symbol", "Unknown"))
                        raw_link = srv.get("link", "").replace("\\/", "/")
                        if raw_link.startswith("//"): raw_link = "https:" + raw_link
                        
                        stremio_streams.append({
                            "name": "TukTuk",
                            "title": f"🎬 {driver_name}\n🌐 Direct Stream",
                            "url": self.get_proxied_url(raw_link)
                        })
                        
        except Exception as e:
            print(f"❌ خطأ أثناء جلب البث: {e}")
            
        return stremio_streams
