import { useState } from 'react'
import axios from 'axios'
import { Search, Download, Shield, Calendar, Mail, Phone } from 'lucide-react'
import './App.css'

// --- AYARLAR ---
const API_URL = "http://127.0.0.1:8000"
const API_KEY = "haci_baba_bunu_begenmedi_12345" // Backend şifresiyle aynı olmalı

function App() {
  const [username, setUsername] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [limit, setLimit] = useState(100)
  const [loading, setLoading] = useState(false)
  const [sonuc, setSonuc] = useState(null)
  const [takipciler, setTakipciler] = useState([])
  const [mesaj, setMesaj] = useState('')

  // 1. GENEL ANALİZ
  const analizEt = async () => {
    if (!username) return alert("Kullanıcı adı gir!")
    setLoading(true)
    setMesaj("Hedef analiz ediliyor...")
    setSonuc(null)
    setTakipciler([]) // Eski listeyi temizle
    
    try {
      const res = await axios.post(`${API_URL}/api/analiz`, {
        username: username,
        session_id: sessionId
      }, {
        headers: { 'x-api-key': API_KEY }
      })
      
      setSonuc(res.data.data)
      setMesaj("✅ Analiz Başarılı!")
      // Eğer önceden çekilmiş rapor varsa onu da getir
      raporuGuncelle() 
    } catch (err) {
      setMesaj("❌ Hata: " + (err.response?.data?.detail || err.message))
    }
    setLoading(false)
  }

  // 2. STALKER MODU (TAKİPÇİ ÇEKME)
  const takipciBaslat = async () => {
    if (!sessionId) return alert("Bunun için Session ID şart!")
    
    try {
      await axios.post(`${API_URL}/api/takipci_getir`, {
        hedef_username: username,
        session_id: sessionId,
        limit: parseInt(limit)
      }, {
        headers: { 'x-api-key': API_KEY }
      })
      alert("🕵️‍♂️ İşlem arka planda başlatıldı! Terminali kontrol et.")
    } catch (err) {
      alert("Hata: " + err.message)
    }
  }

  // 3. RAPOR GÜNCELLEME
  const raporuGuncelle = async () => {
    if (!username) return
    try {
      const res = await axios.get(`${API_URL}/api/rapor/${username}`, {
        headers: { 'x-api-key': API_KEY }
      })
      if (res.data.takipci_listesi) {
        setTakipciler(res.data.takipci_listesi)
      }
    } catch (err) {
      console.log("Rapor yok")
    }
  }

  return (
    <div className="dashboard">
      <header>
        <h1>👁️ INSTA-GOD <span className="tag">V10 PRO</span></h1>
        <p>Advanced OSINT & Forensics Dashboard</p>
      </header>

      <div className="control-panel">
        <div className="input-group">
          <Search size={20} />
          <input 
            type="text" 
            placeholder="Hedef Kullanıcı (örn: tarkan)" 
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>
        
        <div className="input-group">
          <Shield size={20} />
          <input 
            type="password" 
            placeholder="Session ID (İsteğe Bağlı)" 
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
          />
        </div>

        <button onClick={analizEt} disabled={loading} className="btn-main">
          {loading ? "Sızılıyor..." : "HEDEFİ ANALİZ ET"}
        </button>
      </div>

      {mesaj && <div className="status-bar">{mesaj}</div>}

      {sonuc && (
        <div className="grid-container">
          {/* --- SOL: PROFİL KARTI (GÜNCELLENDİ) --- */}
          <div className="card profile-card">
            <div className="card-header"><h3>👤 KİMLİK BİLGİLERİ</h3></div>
            <div className="card-body profile-body">
              
              {/* Profil Resmi */}
              <div className="profile-image-container">
                <img 
                  src={sonuc.profile_pic_url} 
                  alt="Profil" 
                  className="profile-img"
                  onError={(e) => {e.target.src = "https://cdn-icons-png.flaticon.com/512/149/149071.png"}}
                />
              </div>

              {/* İsim ve Linkler */}
              <div className="profile-info">
                <h2>
                  {sonuc.full_name} 
                  {sonuc.is_verified && <span title="Onaylı Hesap"> ✅</span>}
                </h2>
                <p className="username">@{sonuc.username}</p>
                
                <a 
                  href={`https://www.instagram.com/${sonuc.username}`} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="insta-link"
                >
                  Instagram'da Görüntüle ↗
                </a>

                <p className="bio">{sonuc.biography}</p>
                
                <div className="stats">
                  <div>👥 <b>{sonuc.followers}</b> Takipçi</div>
                  <div>👀 <b>{sonuc.following}</b> Takip</div>
                </div>
                <p className={sonuc.is_private ? "red" : "green"} style={{marginTop: '10px'}}>
                  {sonuc.is_private ? "🔒 GİZLİ HESAP" : "🔓 AÇIK HESAP"}
                </p>
              </div>
            </div>
          </div>

          {/* --- SAĞ: FORENSICS (ADLİ BİLİŞİM) --- */}
          <div className="card forensics-card">
            <div className="card-header"><h3>🧩 ADLİ BİLİŞİM</h3></div>
            <div className="card-body">
              <div className="info-row">
                <span className="code-label">Instagram ID:</span>
                <span className="code">{sonuc.instagram_id}</span>
              </div>

              <div className="info-row">
                <Calendar size={18} />
                <div>
                  <small>Hesap Kuruluş Tarihi (Tahmini)</small>
                  <strong>{sonuc.kurulus_tarihi}</strong>
                </div>
              </div>
              
              <div className="info-row">
                <Mail size={18} />
                <div>
                  <small>Sızdırılan E-Posta</small>
                  <strong>{sonuc.public_email || "Tespit Edilemedi"}</strong>
                </div>
              </div>

              <div className="info-row">
                <Phone size={18} />
                <div>
                  <small>Sızdırılan Telefon</small>
                  <strong>{sonuc.public_phone || "Tespit Edilemedi"}</strong>
                </div>
              </div>
            </div>
          </div>

          {/* --- ALT: STALKER MODU --- */}
          <div className="card stalker-card full-width">
            <div className="card-header">
              <h3>🕵️‍♂️ STALKER MODU (Takipçi Listesi)</h3>
              <div className="actions">
                <input 
                  type="number" 
                  value={limit} 
                  onChange={(e) => setLimit(e.target.value)} 
                  style={{width: '80px', padding: '5px'}}
                  placeholder="Limit"
                />
                <button onClick={takipciBaslat} className="btn-danger">
                  <Download size={16} /> LİSTEYİ ÇEK
                </button>
                <button onClick={raporuGuncelle} className="btn-secondary">
                  🔄 YENİLE
                </button>
              </div>
            </div>
            
            <div className="user-list">
              {takipciler.length > 0 ? (
                <table>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Kullanıcı Adı</th>
                      <th>Tam Adı</th>
                    </tr>
                  </thead>
                  <tbody>
                    {takipciler.map((u, i) => (
                      <tr key={i}>
                        <td className="code">{u.instagram_pk}</td>
                        <td>{u.username}</td>
                        <td>{u.full_name}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p style={{padding: '20px', textAlign: 'center', color: '#666'}}>
                  Henüz veri çekilmedi. Session ID girip "Listeyi Çek" butonuna bas.
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
