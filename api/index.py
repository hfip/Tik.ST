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
    "name": "TukTuk",
    "description": "إضافة توك توك سينما المباشرة",
    "icon": "https://raw.githubusercontent.com/h-fip/TukTuk_ST/main/icon.png", 
    "resources": ["stream"],
    "types": ["movie"],
    "idPrefixes": ["tt"]
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
    # مسح الامتداد .json إذا كان موجوداً في الـ ID
    imdb_id = video_id.replace(".json", "")
    
    # استدعاء المحرك مع كود الـ IMDB
    streams = tuktuk.get_streams(imdb_id)
    
    return {"streams": streams}
