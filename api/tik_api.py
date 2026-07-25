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
        meta_url = f"https://v3-cinemeta.strem.io/meta/movie/{imdb_id}.json"
        try:
            meta_res = requests.get(meta_url).json()
            movie_name = meta_res.get("meta", {}).get("name", "")
            if not movie_name: return None
            
            search_url = f"https://zx33.tuktuk-sa.online/?s={quote(movie_name)}"
            res = self.session.get(self.get_proxied_url(search_url), timeout=15)
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
            res = self.session.get(self.get_proxied_url(movie_url), timeout=15)
            soup = BeautifulSoup(res.text, "html.parser")
            
            # جلب كافة المشغلات المتاحة (سواء المباشرة أو من أزرار السيرفرات)
            players_to_check = []
            
            # 1. المشغل الرئيسي
            main_iframe = soup.find("iframe", {"id": "main-video-frame"}) or soup.find("iframe", {"data-crypt": True})
            if main_iframe:
                if main_iframe.get("data-crypt"):
                    decoded = self.decode_base64(main_iframe["data-crypt"])
                    if decoded: players_to_check.append(decoded)
                elif main_iframe.get("src"):
                    players_to_check.append(main_iframe["src"])

            # 2. أزرار السيرفرات المتبقية في الصفحة (Server Tabs)
            for el in soup.find_all(["li", "button", "a"], attrs={"data-crypt": True}):
                decoded = self.decode_base64(el["data-crypt"])
                if decoded and decoded not in players_to_check:
                    players_to_check.append(decoded)

            # معالجة كل مشغل تم اصطياده
            for player_url in players_to_check:
                try:
                    player_res = self.session.get(self.get_proxied_url(player_url), timeout=10)
                    inertia_json = self._extract_inertia(player_res.text)
                    
                    if inertia_json:
                        # مسار Inertia (سيرفرات مباشرة)
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
                        
                        partial_res = self.session.get(self.get_proxied_url(player_url), headers=headers, timeout=10)
                        servers = self._find_all_servers(partial_res.json())
                        
                        for srv in servers:
                            driver_name = srv.get("driver", srv.get("symbol", "Server"))
                            raw_link = srv.get("link", "").replace("\\/", "/")
                            if raw_link.startswith("//"): raw_link = "https:" + raw_link
                            
                            stremio_streams.append({
                                "name": "TukTuk",
                                "title": f"🎬 {driver_name}\n🌐 Direct Stream",
                                "url": self.get_proxied_url(raw_link)
                            })
                    else:
                        # مسار السيرفر الخارجي (ok.ru, vidoza, etc.)
                        domain = player_url.split('/')[2] if '//' in player_url else "External"
                        stremio_streams.append({
                            "name": "TukTuk",
                            "title": f"🎬 {domain}\n🌐 External Player",
                            "externalUrl": player_url
                        })
                except Exception as inner_e:
                    continue

        except Exception as e:
            print(f"❌ خطأ جلب البث: {e}")
            
        return stremio_streams
