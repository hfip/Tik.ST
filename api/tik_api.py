# -*- coding: utf-8 -*-
import re
import json
import html
import requests
import logging
from bs4 import BeautifulSoup
from urllib.parse import quote
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TukTukLogger")

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

    def resolve_movie_name(self, id_str):
        """دالة ذكية تحول id الفيلم (سواء tmdb أو imdb) إلى اسم الفيلم"""
        try:
            # إذا كان المعرف من نوع tmdb:603
            if id_str.startswith("tmdb:"):
                tmdb_id = id_str.split(":")[1]
                # تحويل عبر cinemeta tmdb endpoint
                meta_url = f"https://v3-cinemeta.strem.io/meta/movie/tmdb:{tmdb_id}.json"
                res = requests.get(meta_url, timeout=5)
                if res.status_code == 200 and res.headers.get("content-type", "").startswith("application/json"):
                    return res.json().get("meta", {}).get("name")
                
                # خطة بديلة لطلب Cinemeta بالعنوان العادي
                meta_url_alt = f"https://v3-cinemeta.strem.io/catalog/movie/top/search={tmdb_id}.json"
                res_alt = requests.get(meta_url_alt, timeout=5)
                if res_alt.status_code == 200:
                    metas = res_alt.json().get("metas", [])
                    if metas: return metas[0].get("name")

            # إذا كان المعرف IMDb العادي tt0133093
            else:
                meta_url = f"https://v3-cinemeta.strem.io/meta/movie/{id_str}.json"
                res = requests.get(meta_url, timeout=5)
                if res.status_code == 200 and "application/json" in res.headers.get("content-type", ""):
                    return res.json().get("meta", {}).get("name")
        except Exception as e:
            logger.error(f"❌ خطأ جلب اسم الفيلم لـ {id_str}: {e}")
        return None

    def _extract_direct_stream(self, player_url):
        try:
            res = self.session.get(self.get_proxied_url(player_url), timeout=5)
            match = re.search(r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*)', res.text)
            if match:
                return match.group(1).replace("\\/", "/")
        except Exception as e:
            logger.warning(f"⚠️ فشل استخراج المباشر من {player_url}: {e}")
        return None

    def search_movie(self, id_str):
        logger.info(f"🔍 [1/3] بدء البحث عن المعرف: {id_str}")
        movie_name = self.resolve_movie_name(id_str)
        
        if not movie_name:
            logger.error("❌ لم نتمكن من الوصول لاسم الفيلم من Cinemeta.")
            return None
            
        logger.info(f"📌 [Cinemeta] اسم الفيلم المكتشف: '{movie_name}'")
        
        try:
            search_url = f"https://zx33.tuktuk-sa.online/?s={quote(movie_name)}"
            logger.info(f"🌐 [Search URL] جاري البحث: {search_url}")
            
            res = self.session.get(self.get_proxied_url(search_url), timeout=8)
            soup = BeautifulSoup(res.text, "html.parser")
            
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/فيلم-" in href or "/movie" in href or "%D9%81%D9%8A%D9%84%D9%85" in href:
                    if "/category/" not in href and "/page/" not in href:
                        logger.info(f"✅ [Search Hit] تم العثور على رابط الفيلم: {href}")
                        return href
            logger.error("❌ [Search Failed] لم يظهر رابط فيلم في نتائج البحث!")
        except Exception as e:
            logger.error(f"❌ [Search Error] خطأ أثناء البحث: {e}")
        return None

    def get_streams(self, id_str):
        logger.info("==========================================")
        logger.info(f"🚀 [NEW REQUEST] طلب بث جديد لـ: {id_str}")
        logger.info("==========================================")
        
        stremio_streams = []
        movie_url = self.search_movie(id_str)
        if not movie_url:
            logger.error("🚨 توقف العمل: تعذر إيجاد رابط الفيلم.")
            return stremio_streams

        try:
            logger.info(f"🔍 [2/3] جلب صفحة الفيلم: {movie_url}")
            res = self.session.get(self.get_proxied_url(movie_url), timeout=8)
            soup = BeautifulSoup(res.text, "html.parser")
            players = []
            
            # 1. المشغل الرئيسي
            main_iframe = soup.find("iframe", {"id": "main-video-frame"}) or soup.find("iframe", {"data-crypt": True})
            if main_iframe:
                if main_iframe.get("data-crypt"):
                    decoded = self.decode_base64(main_iframe["data-crypt"])
                    if decoded: players.append(decoded)
                elif main_iframe.get("src"):
                    players.append(main_iframe["src"])

            # 2. أزرار السيرفرات الفرعية
            for el in soup.find_all(["li", "button", "a", "div"]):
                if el.get("data-crypt"):
                    decoded = self.decode_base64(el["data-crypt"])
                    if decoded and decoded not in players:
                        players.append(decoded)
                for attr in ["data-link", "data-url", "data-src"]:
                    val = el.get(attr)
                    if val and val.startswith("http") and val not in players:
                        players.append(val)

            logger.info(f"📊 [3/3] إجمالي المشغلات المستخرجة: {len(players)}")

            for idx, p_url in enumerate(players, 1):
                domain = p_url.split('/')[2] if '//' in p_url else "Server"
                direct_url = self._extract_direct_stream(p_url)
                
                if direct_url:
                    logger.info(f"   ├─ 🔥 بث مباشر مكتشف: {direct_url[:50]}...")
                    stremio_streams.append({
                        "name": "TukTuk",
                        "title": f"🎬 {domain}\n🌐 M3U8 Direct",
                        "url": self.get_proxied_url(direct_url)
                    })
                else:
                    logger.info(f"   ├─ 🌐 مشغل مدمج متوافق مع Forward: {p_url}")
                    stremio_streams.append({
                        "name": "TukTuk",
                        "title": f"🎬 {domain}\n🌐 Web Player",
                        "url": p_url,          # إرسال الرابط كـ url ليتعرف عليه Forward
                        "webVideo": p_url,      # دعم خاص بـ Forward و Stremio Web
                        "externalUrl": p_url   # دعم احتياطي
                    })

        except Exception as e:
            logger.error(f"❌ [Stream Error] خطأ رئيسي أثناء جلب البث: {e}")
            
        logger.info(f"🏁 [RESPONSE READY] عدد الروابط المرجعة: {len(stremio_streams)}")
        return stremio_streams
