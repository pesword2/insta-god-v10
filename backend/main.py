import os
from fastapi import FastAPI, HTTPException, BackgroundTasks, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import requests
import random
import time
from datetime import datetime
from typing import Optional, List

# --- GÜVENLİK ---
GIZLI_API_ANAHTARI = "haci_baba_bunu_begenmedi_12345"

# --- AKILLI VERİTABANI AYARI ---
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./insta_god_final.db")
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELLER ---
class HedefUser(Base):
    __tablename__ = "hedefler"
    id = Column(Integer, primary_key=True, index=True)
    instagram_id = Column(String, unique=True, index=True)
    username = Column(String, index=True)
    full_name = Column(String)
    biography = Column(String)
    profile_pic_url = Column(String)
    followers = Column(Integer)
    following = Column(Integer)
    is_private = Column(Boolean)
    is_verified = Column(Boolean)
    kurulus_tarihi = Column(String)
    public_email = Column(String, nullable=True)
    public_phone = Column(String, nullable=True)
    analiz_tarihi = Column(String)
    takipci_listesi = relationship("Takipci", back_populates="hedef", cascade="all, delete-orphan")

class Takipci(Base):
    __tablename__ = "takipciler"
    id = Column(Integer, primary_key=True, index=True)
    hedef_id = Column(Integer, ForeignKey("hedefler.id"))
    username = Column(String)
    full_name = Column(String)
    instagram_pk = Column(String)
    hedef = relationship("HedefUser", back_populates="takipci_listesi")

Base.metadata.create_all(bind=engine)

# --- UYGULAMA & GÜVENLİK ---
app = FastAPI(
    dependencies=[Depends(lambda x_api_key=Header(None): 
        HTTPException(403, "⛔ Yetkisiz Giriş") if x_api_key != GIZLI_API_ANAHTARI else None)],
    docs_url=None, redoc_url=None, openapi_url=None
)

# CORS: Kapıyı Herkese Aç (Yıldız *)
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- VERİ MODELLERİ ---
class AnalizIstegi(BaseModel):
    username: str
    session_id: Optional[str] = ""

class TakipciIstegi(BaseModel):
    hedef_username: str
    session_id: str
    limit: int = 100

# --- YARDIMCILAR ---
def get_headers(session_id=""):
    h = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "X-IG-App-ID": "936619743392459",
        "X-Requested-With": "XMLHttpRequest",
        "Accept-Language": "tr-TR,tr;q=0.9"
    }
    if session_id:
        h["Cookie"] = f"sessionid={session_id}"
        h["User-Agent"] = "Instagram 219.0.0.12.117 Android"
    return h

def id_tarih_coz(user_id):
    try:
        binary_time = (int(user_id) >> 23) + 1314220021721
        return datetime.fromtimestamp(binary_time / 1000.0).strftime('%Y-%m-%d %H:%M:%S')
    except: return "Hesaplanamadi"

# --- ENDPOINTLER ---

@app.get("/")
def ana_sayfa():
    return {"mesaj": "🔒 Güvenli Insta-God Sunucusu Aktif (V10)"}

@app.post("/api/analiz")
def analiz_et(istek: AnalizIstegi):
    db = SessionLocal()
    try:
        url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={istek.username}"
        headers = get_headers()
        headers["Referer"] = f"https://www.instagram.com/{istek.username}/"
        
        time.sleep(random.uniform(0.8, 1.5)) # Jitter
        r = requests.get(url, headers=headers)
        
        if r.status_code != 200:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")
            
        user = r.json()["data"]["user"]
        
        # DB Kayıt
        db_user = db.query(HedefUser).filter(HedefUser.instagram_id == user["id"]).first()
        if not db_user: db_user = HedefUser()
            
        db_user.instagram_id = user["id"]
        db_user.username = user["username"]
        db_user.full_name = user["full_name"]
        db_user.biography = user["biography"]
        db_user.profile_pic_url = user.get("profile_pic_url_hd") # Resim URL
        db_user.followers = user["edge_followed_by"]["count"]
        db_user.following = user["edge_follow"]["count"]
        db_user.is_private = user["is_private"]
        db_user.is_verified = user["is_verified"]
        db_user.kurulus_tarihi = id_tarih_coz(user["id"])
        db_user.public_email = user.get("business_email")
        db_user.public_phone = user.get("business_phone_number")
        db_user.analiz_tarihi = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return {"status": "success", "data": db_user}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# --- STALKER (TAKİPÇİ) MODÜLÜ ---
def stalker_worker(hedef_username: str, session_id: str, limit: int):
    db = SessionLocal()
    hedef = db.query(HedefUser).filter(HedefUser.username == hedef_username).first()
    if not hedef:
        db.close()
        return

    headers = get_headers(session_id)
    next_max_id = ""
    count = 0
    
    # Eski listeyi temizle
    db.query(Takipci).filter(Takipci.hedef_id == hedef.id).delete()
    db.commit()

    while count < limit:
        try:
            url = f"https://i.instagram.com/api/v1/friendships/{hedef.instagram_id}/followers/?count=100&search_surface=follow_list_page&max_id={next_max_id}"
            r = requests.get(url, headers=headers)
            resp = r.json()
            users = resp.get("users", [])
            if not users: break
            
            for u in users:
                t = Takipci(
                    hedef_id=hedef.id,
                    username=u.get("username"),
                    full_name=u.get("full_name"),
                    instagram_pk=str(u.get("pk"))
                )
                db.add(t)
                count += 1
                if count >= limit: break
            
            db.commit()
            next_max_id = resp.get("next_max_id")
            if not next_max_id: break
            time.sleep(random.uniform(2.5, 4.5)) # WAF Koruması
            
        except: break
    db.close()

@app.post("/api/takipci_getir")
def takipci_baslat(istek: TakipciIstegi, background_tasks: BackgroundTasks):
    background_tasks.add_task(stalker_worker, istek.hedef_username, istek.session_id, istek.limit)
    return {"status": "started", "message": "İşlem başlatıldı."}

@app.get("/api/rapor/{username}")
def rapor_goster(username: str):
    db = SessionLocal()
    user = db.query(HedefUser).filter(HedefUser.username == username).first()
    if not user:
        db.close()
        raise HTTPException(status_code=404, detail="Kayıt yok.")
        
    takipciler = db.query(Takipci).filter(Takipci.hedef_id == user.id).limit(1000).all()
    db.close()
    return {"profil": user, "takipci_listesi": takipciler}
