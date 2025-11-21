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
# 1. Render'dan gelen adresi al, yoksa yerel dosya (SQLite) kullan
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./insta_god_final.db")

# 2. Render 'postgres://' verir ama SQLAlchemy 'postgresql://' ister. Düzeltiyoruz.
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. SQLite ve PostgreSQL Ayar Farkı
# "check_same_thread" sadece SQLite'ta lazımdır, Postgres'te hata verir.
connect_args = {}
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    connect_args = {"check_same_thread": False}

# 4. Motoru Ateşle
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELLER (RESİM URL EKLENDİ) ---
class HedefUser(Base):
    __tablename__ = "hedefler"
    id = Column(Integer, primary_key=True, index=True)
    instagram_id = Column(String, unique=True, index=True)
    username = Column(String, index=True)
    full_name = Column(String)
    biography = Column(String)
    profile_pic_url = Column(String)  # <-- YENİ SÜTUN: Profil Resmi
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

app = FastAPI(dependencies=[Depends(lambda x_api_key=Header(None): 
    HTTPException(403, "Yasak") if x_api_key != GIZLI_API_ANAHTARI else None)],
    docs_url=None, redoc_url=None, openapi_url=None)

origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class AnalizIstegi(BaseModel):
    username: str
    session_id: Optional[str] = ""

class TakipciIstegi(BaseModel):
    hedef_username: str
    session_id: str
    limit: int = 100

def get_headers(session_id=""):
    h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "X-IG-App-ID": "936619743392459", "X-Requested-With": "XMLHttpRequest"}
    if session_id: h.update({"Cookie": f"sessionid={session_id}", "User-Agent": "Instagram 219.0.0.12.117 Android"})
    return h

def id_tarih_coz(user_id):
    try: return datetime.fromtimestamp(((int(user_id) >> 23) + 1314220021721) / 1000.0).strftime('%Y-%m-%d %H:%M:%S')
    except: return "Hesaplanamadi"

@app.post("/api/analiz")
def analiz_et(istek: AnalizIstegi):
    db = SessionLocal()
    try:
        url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={istek.username}"
        headers = get_headers(); headers["Referer"] = f"https://www.instagram.com/{istek.username}/"
        time.sleep(random.uniform(0.8, 1.5))
        
        r = requests.get(url, headers=headers)
        if r.status_code != 200: raise HTTPException(404, detail="Kullanıcı bulunamadı.")
        
        user = r.json()["data"]["user"]
        
        db_user = db.query(HedefUser).filter(HedefUser.instagram_id == user["id"]).first()
        if not db_user: db_user = HedefUser()
            
        db_user.instagram_id = user["id"]
        db_user.username = user["username"]
        db_user.full_name = user["full_name"]
        db_user.biography = user["biography"]
        # RESİM URL'SİNİ ARTIK KAYDEDİYORUZ:
        db_user.profile_pic_url = user.get("profile_pic_url_hd") 
        db_user.followers = user["edge_followed_by"]["count"]
        db_user.following = user["edge_follow"]["count"]
        db_user.is_private = user["is_private"]
        db_user.is_verified = user["is_verified"]
        db_user.kurulus_tarihi = id_tarih_coz(user["id"])
        db_user.public_email = user.get("business_email")
        db_user.public_phone = user.get("business_phone_number")
        db_user.analiz_tarihi = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        db.add(db_user); db.commit(); db.refresh(db_user)
        return {"status": "success", "data": db_user}
    except Exception as e: raise HTTPException(500, detail=str(e))
    finally: db.close()

# ... (Diğer fonksiyonlar: stalker_worker, takipci_getir, rapor_getir aynı kalacak)
# Not: Kodun çok uzamaması için diğer kısımları öncekiyle aynı varsayıyorum.
# Eğer stalker kısmını da tekrar istersen söyle, eklerim.
