    def get_streams(self, imdb_id):
        """الوظيفة الرئيسية: بحث -> جلب الصفحة -> فك الحماية -> إرجاع الروابط (مع دعم المشغلات الخارجية)"""
        stremio_streams = []
        
        movie_url = self.search_movie(imdb_id)
        if not movie_url:
            return stremio_streams

        try:
            res = self.session.get(self.get_proxied_url(movie_url), timeout=15)
            soup = BeautifulSoup(res.text, "html.parser")
            
            iframe = soup.find("iframe", {"id": "main-video-frame"}) or soup.find("iframe", {"data-crypt": True})
            player_url = None
            
            if iframe:
                if iframe.get("data-crypt"):
                    player_url = self.decode_base64(iframe["data-crypt"])
                elif iframe.get("src"):
                    player_url = iframe.get("src")
            
            if player_url:
                player_res = self.session.get(self.get_proxied_url(player_url), timeout=15)
                inertia_json = self._extract_inertia(player_res.text)
                
                if inertia_json:
                    # 🟢 المسار الأول: مشغل Megatuktuk (استخراج السيرفرات المباشرة)
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
                else:
                    # 🟠 المسار الثاني: مشغل خارجي مكشوف (ok.ru, vidoza, etc.)
                    domain = player_url.split('/')[2] if '//' in player_url else "External Server"
                    stremio_streams.append({
                        "name": "TukTuk",
                        "title": f"🎬 {domain}\n🌐 Web Player (External)",
                        "externalUrl": player_url # سيقوم Stremio بفتح هذا الرابط في المتصفح الداخلي
                    })
                        
        except Exception as e:
            print(f"❌ خطأ أثناء جلب البث: {e}")
            
        return stremio_streams
