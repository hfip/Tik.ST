# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.tuktuk_api import TukTukAPI

app = FastAPI(title="TukTuk Stremio Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MANIFEST = {
    "id": "plex.abdullah.tuktuk.addon",
    "version": "1.0.0",
    "name": "TukTuk.Stremio",
    "description": "إضافة توك توك سينما المباشرة",
    "icon": "https://raw.githubusercontent.com/.../icon.png", # يمكنك وضع رابط أيقونة هنا
    "resources": ["stream"],
    "types": ["movie", "series"],
    "idPrefixes": ["tt"] # العمل باستخدام معرفات IMDB
}

tuktuk = TukTukAPI()

@app.get("/")
def home():
    return {"status": "TukTuk Engine is running! Add /manifest.json to Stremio."}

@app.get("/manifest.json")
def get_manifest():
    return MANIFEST

@app.get("/stream/{type}/{video_id}.json")
def get_streams(type: str, video_id: str):
    # ملاحظة: في النسخة النهائية نحتاج دالة تحول video_id (مثل tt1234567) إلى رابط الفيلم في توك توك
    # مؤقتاً للتجربة، سنضع رابطاً ثابتاً للفيلم الذي فحصناه
    test_movie_url = "https://zx33.tuktuk-sa.online/فيلم-the-odyssey-2026-مترجم-اون-لاين-bet/"
    
    streams = tuktuk.get_streams(test_movie_url)
    
    return {"streams": streams}
