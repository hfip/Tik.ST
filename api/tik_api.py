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
        try:
            missing_padding = len(data_str) % 4
            if missing_padding: data_str += "=" * (4 - missing_padding)
            return base64.b64decode(data_str).decode("utf-8")
        except:
            return None

    def _extract_direct_stream(self, player_url):
        """محاولة استخراج رابط m3u8 أو mp4 مباشر من المشغلات المعروفة"""
        try:
            res = self.session.get(self.get_proxied_url(player_url), timeout=5)
            match = re.search(r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*)', res.text)
            if match:
                return match.group(1).replace("\\/", "/")
        except:
            pass
        return None

    def search_movie(self, imdb_id):
        meta_url = f"https://v3-cinemeta.strem.io/meta/movie/{imdb_id}.json"
        try:
            meta_res = requests.get(meta_url, timeout=5).json()
            movie_name = meta_res.get("meta", {}).get("name", "")
            if not movie_name: return None
            
            search_url = f"https://zx33.tuktuk-sa.online/?s={quote(movie_name)}"
            res = self.session.get(self.get_proxied_url(search_url), timeout=8)
            soup = BeautifulSoup(res.text, "html.parser")
            
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/فيلم-" in href or "/movie" in href or "%D9%81%D9%8A%D9%84%D9%85" in href:
                    if "/category/" not in href and "/page/" not in href:
                        return href
        except Exception as e:
            print(f"❌ خطأ البحث: {e}")
        return None

    def get_streams(self, imdb_id):
        stremio_streams = []
        movie_url = self.search_movie(imdb_id)
        if not movie_url:
            return stremio_streams

        try:
            res = self.session.get(self.get_proxied_url(movie_url), timeout=8)
            soup = BeautifulSoup(res.text, "html.parser")
            
            players = []
            
            # 1. المشغل الرئيسي في الصفحة
            main_iframe = soup.find("iframe", {"id": "main-video-frame"}) or soup.find("iframe", {"data-crypt": True})
            if main_iframe:
                if main_iframe.get("data-crypt"):
                    decoded = self.decode_base64(main_iframe["data-crypt"])
                    if decoded: players.append(decoded)
                elif main_iframe.get("src"):
                    players.append(main_iframe["src"])

            # 2. فحص كافة أزرار السيرفرات والعناصر التفاعلية
            for el in soup.find_all(["li", "button", "a", "div"]):
                # فحص التشفير بـ data-crypt
                if el.get("data-crypt"):
                    decoded = self.decode_base64(el["data-crypt"])
                    if decoded and decoded not in players:
                        players.append(decoded)
                # فحص الروابط الصريحة في data-link / data-url
                for attr in ["data-link", "data-url", "data-src"]:
                    val = el.get(attr)
                    if val and val.startswith("http") and val not in players:
                        players.append(val)

            # 3. معالجة القائمة إما بالبث المباشر أو المشغل المدمج
            for p_url in players:
                domain = p_url.split('/')[2] if '//' in p_url else "Server"
                
                # فحص وجود بث مباشر m3u8/mp4
                direct_url = self._extract_direct_stream(p_url)
                
                if direct_url:
                    stremio_streams.append({
                        "name": "TukTuk",
                        "title": f"🎬 {domain}\n🌐 M3U8 Direct",
                        "url": self.get_proxied_url(direct_url)
                    })
                else:
                    stremio_streams.append({
                        "name": "TukTuk",
                        "title": f"🎬 {domain}\n🌐 Web Player",
                        "externalUrl": p_url
                    })

        except Exception as e:
            print(f"❌ خطأ جلب البث: {e}")
            
        return stremio_streams
