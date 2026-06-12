"""
Главное окно через pywebview — главный поток.
"""
import json, sys, os, threading
from datetime import datetime

try:
    import webview
except ImportError:
    print("pip install pywebview")
    sys.exit(1)

_tracker = None
_network = None
_window  = None
_stats   = None

HTML = r"""
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Together</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,'Segoe UI',sans-serif;background:#0f0f13;color:#e8e6f0;height:100vh;overflow:hidden;user-select:none}
  .titlebar{height:40px;background:#0f0f13;display:flex;align-items:center;padding:0 16px;
    -webkit-app-region:drag;border-bottom:0.5px solid rgba(255,255,255,0.06);justify-content:space-between}
  .titlebar-title{font-size:13px;color:rgba(255,255,255,0.4);display:flex;align-items:center;gap:8px}
  .heart{color:#d4537e}
  .titlebar-btns{-webkit-app-region:no-drag;display:flex;gap:4px}
  .titlebar-close{width:28px;height:28px;border-radius:6px;border:none;
    background:transparent;color:rgba(255,255,255,0.3);cursor:pointer;font-size:15px;
    display:flex;align-items:center;justify-content:center;transition:all .15s}
  .titlebar-close:hover{background:rgba(255,255,255,0.07);color:rgba(255,255,255,0.7)}
  .content{padding:16px;height:calc(100vh - 40px);overflow-y:auto}
  .cards{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px}
  .card{background:#1a1820;border:0.5px solid rgba(255,255,255,0.07);border-radius:14px;
    padding:14px;border-top:2.5px solid transparent;transition:opacity .3s,filter .3s}
  .card-you{border-top-color:#534ab7}.card-her{border-top-color:#d4537e}
  .offline-card{opacity:.4;filter:grayscale(40%)}
  .avatar{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;
    justify-content:center;font-weight:600;font-size:13px;margin-bottom:10px}
  .avatar-you{background:rgba(83,74,183,0.2);color:#a89ef0}
  .avatar-her{background:rgba(212,83,126,0.2);color:#e891b0}
  .card-label{font-size:10px;color:rgba(255,255,255,0.25);margin-bottom:4px;
    text-transform:uppercase;letter-spacing:.05em}
  .card-app{font-size:14px;font-weight:500;color:#f0eeff;margin-bottom:3px;
    word-break:break-word;line-height:1.3;max-height:2.6em;overflow:hidden}
  .card-title{font-size:11px;color:rgba(255,255,255,0.3);
    word-break:break-word;line-height:1.3;max-height:2.6em;overflow:hidden;min-height:14px}
  .card-time{font-size:10px;color:rgba(255,255,255,0.2);margin-top:6px}
  .badge{display:inline-flex;align-items:center;gap:4px;font-size:10px;
    padding:2px 8px;border-radius:20px;margin-top:6px}
  .badge-gaming{background:rgba(83,74,183,0.2);color:#a89ef0}
  .badge-browser{background:rgba(23,100,165,0.2);color:#7ab8ef}
  .badge-chat{background:rgba(29,158,117,0.2);color:#5ddaaa}
  .badge-music{background:rgba(186,117,23,0.2);color:#f0b352}
  .badge-video{background:rgba(162,45,45,0.2);color:#f08080}
  .badge-work{background:rgba(99,152,34,0.2);color:#a8d865}
  .badge-idle,.badge-other,.badge-streaming{background:rgba(100,100,100,0.15);color:rgba(255,255,255,0.3)}
  .status-row{display:flex;align-items:center;gap:6px;margin-bottom:14px}
  .dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
  .dot-online{background:#1d9e75;box-shadow:0 0 6px #1d9e75}
  .dot-waiting{background:#b87c1a;box-shadow:0 0 6px #b87c1a}
  .status-text{font-size:12px;color:rgba(255,255,255,0.3)}
  .history-cols{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:8px}
  .history-col-title{font-size:10px;color:rgba(255,255,255,0.2);text-transform:uppercase;
    letter-spacing:.06em;margin-bottom:6px}
  .section-title{font-size:10px;color:rgba(255,255,255,0.2);
    text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px}
  .timeline{display:flex;flex-direction:column;gap:5px}
  .tl-item{display:flex;align-items:flex-start;gap:8px;padding:7px 10px;
    background:#1a1820;border-radius:9px;border:0.5px solid rgba(255,255,255,0.05)}
  .tl-dot{width:5px;height:5px;border-radius:50%;flex-shrink:0;margin-top:4px}
  .tl-dot-you{background:#534ab7}.tl-dot-her{background:#d4537e}
  .tl-time{font-size:11px;color:rgba(255,255,255,0.2);min-width:36px;flex-shrink:0}
  .tl-app{font-size:12px;color:rgba(255,255,255,0.6);word-break:break-word;line-height:1.4}
  @keyframes slideIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}
  .tl-item-new{animation:slideIn 0.25s ease}
  @keyframes fadeUpdate{0%{background:rgba(83,74,183,0.15)}100%{background:#1a1820}}
  .card-updated{animation:fadeUpdate 0.8s ease}
  #page-settings,#page-stats{display:none}
  .settings-row{display:flex;justify-content:space-between;align-items:center;
    padding:11px 0;border-bottom:0.5px solid rgba(255,255,255,0.05);font-size:13px}
  .settings-label{color:rgba(255,255,255,0.55)}
  input.si{background:#1a1820;border:0.5px solid rgba(255,255,255,0.1);border-radius:6px;
    padding:4px 10px;color:#e8e6f0;font-size:12px;width:140px;outline:none}
  input.si:focus{border-color:rgba(83,74,183,0.5)}
  .toggle{position:relative;width:36px;height:20px;flex-shrink:0}
  .toggle input{opacity:0;width:0;height:0}
  .toggle-slider{position:absolute;cursor:pointer;inset:0;background:rgba(255,255,255,0.1);
    border-radius:20px;transition:.2s}
  .toggle-slider:before{content:'';position:absolute;width:14px;height:14px;left:3px;bottom:3px;
    background:rgba(255,255,255,0.4);border-radius:50%;transition:.2s}
  .toggle input:checked+.toggle-slider{background:rgba(83,74,183,0.6)}
  .toggle input:checked+.toggle-slider:before{transform:translateX(16px);background:#a89ef0}
  .btn{padding:7px 14px;border-radius:8px;border:0.5px solid rgba(255,255,255,0.1);
    background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.55);cursor:pointer;
    font-size:12px;transition:all .15s}
  .btn:hover{background:rgba(255,255,255,0.09)}
  .btn-primary{background:rgba(83,74,183,0.2);border-color:rgba(83,74,183,0.4);color:#a89ef0}
  .btn-primary:hover{background:rgba(83,74,183,0.3)}
  .btn-danger{border-color:rgba(212,83,126,0.3);color:#d4537e}
  .btn-danger:hover{background:rgba(212,83,126,0.1)}
  .nav{display:flex;gap:4px;margin-bottom:16px}
  .nav-btn{flex:1;padding:6px;border-radius:8px;border:none;background:transparent;
    color:rgba(255,255,255,0.3);cursor:pointer;font-size:12px;transition:all .15s}
  .nav-btn.active{background:rgba(255,255,255,0.07);color:rgba(255,255,255,0.8)}
  ::-webkit-scrollbar{width:3px}
  ::-webkit-scrollbar-track{background:transparent}
  ::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.08);border-radius:2px}
</style>
</head>
<body>
<div class="titlebar">
  <div class="titlebar-title"><span class="heart">♥</span> Together</div>
  <div class="titlebar-btns">
    <button class="titlebar-close" onclick="pywebview.api.minimize_window()" title="Свернуть">—</button>
    <button class="titlebar-close" onclick="pywebview.api.hide_window()" title="В трей">✕</button>
  </div>
</div>
<div class="content">
  <div class="nav">
    <button class="nav-btn active" onclick="showPage('main',this)">Активность</button>
    <button class="nav-btn" onclick="showPage('stats',this)">Статистика</button>
    <button class="nav-btn" onclick="showPage('settings',this)">⚙</button>
  </div>

  <!-- АКТИВНОСТЬ -->
  <div id="page-main">
    <div class="status-row">
      <div class="dot dot-waiting" id="conn-dot"></div>
      <span class="status-text" id="conn-text">ожидание партнёра...</span>
    </div>
    <div class="cards">
      <div class="card card-you" id="my-card">
        <div class="avatar avatar-you" id="my-avatar">Я</div>
        <div class="card-label" id="my-label">ты</div>
        <div class="card-app" id="my-app">загрузка...</div>
        <div class="card-title" id="my-title"></div>
        <div class="card-time" id="my-time"></div>
        <div class="badge badge-idle" id="my-badge">—</div>
      </div>
      <div class="card card-her offline-card" id="her-card">
        <div class="avatar avatar-her" id="her-avatar">?</div>
        <div class="card-label" id="her-label">она</div>
        <div class="card-app" id="her-app">не в сети</div>
        <div class="card-title" id="her-title"></div>
        <div class="card-time" id="her-time"></div>
        <div class="badge badge-idle" id="her-badge">офлайн</div>
      </div>
    </div>
    <div class="history-cols">
      <div>
        <div class="history-col-title" id="my-col-title">ты</div>
        <div class="timeline" id="timeline-you">
          <div class="tl-item"><div class="tl-time">—</div>
            <div class="tl-dot tl-dot-you"></div><div class="tl-app">—</div></div>
        </div>
      </div>
      <div>
        <div class="history-col-title" id="her-col-title">она</div>
        <div class="timeline" id="timeline-her">
          <div class="tl-item"><div class="tl-time">—</div>
            <div class="tl-dot tl-dot-her"></div><div class="tl-app">—</div></div>
        </div>
      </div>
    </div>
  </div>

  <!-- СТАТИСТИКА -->
  <div id="page-stats">
    <div class="section-title" id="stats-date">сегодня</div>
    <div id="stats-categories" style="margin-bottom:16px"></div>
    <div class="section-title">топ приложений</div>
    <div id="stats-apps"></div>
    <div style="display:flex;gap:6px;margin-top:14px">
      <button class="btn btn-primary" id="btn-today" onclick="loadStats('today')" style="flex:1">Сегодня</button>
      <button class="btn" id="btn-week" onclick="loadStats('week')" style="flex:1">7 дней</button>
    </div>
  </div>

  <!-- НАСТРОЙКИ -->
  <div id="page-settings">
    <div class="settings-row">
      <span class="settings-label">Моё имя</span>
      <input class="si" id="inp-name" placeholder="Введи имя"/>
    </div>
    <div class="settings-row">
      <span class="settings-label">Имя партнёра</span>
      <input class="si" id="inp-partner-name" placeholder="Её имя"/>
    </div>
    <div class="settings-row">
      <span class="settings-label">IP партнёра (Zerotier)</span>
      <input class="si" id="inp-ip" placeholder="10.147.X.X"/>
    </div>
    <div class="settings-row">
      <span class="settings-label">Мой Zerotier IP</span>
      <span id="my-ip" style="font-size:12px;color:rgba(255,255,255,0.25)">—</span>
    </div>
    <div class="settings-row">
      <span class="settings-label">
        🕵️ Приватный режим
        <div style="font-size:10px;color:rgba(255,255,255,0.25);margin-top:2px">скрывает вкладку браузера</div>
      </span>
      <label class="toggle">
        <input type="checkbox" id="tog-private" onchange="savePrivate(this.checked)"/>
        <span class="toggle-slider"></span>
      </label>
    </div>
    <div class="settings-row">
      <span class="settings-label">Автозапуск с Windows</span>
      <button class="btn" id="btn-autostart" onclick="toggleAutostart()">проверка...</button>
    </div>
    <div style="margin-top:16px;display:flex;gap:8px">
      <button class="btn btn-primary" id="btn-save" onclick="saveSettings()">Сохранить</button>
      <button class="btn btn-danger" onclick="pywebview.api.quit_app()">Выйти</button>
    </div>
  </div>
</div>

<script>
const BADGES={gaming:'🎮 игра',browser:'🌐 браузер',chat:'💬 чат',
  music:'🎵 музыка',video:'▶ видео',work:'💻 работа',
  idle:'😴 AFK',streaming:'📡 стрим',other:'•'};
const CAT_COLORS = {
  gaming:'#a89ef0',
  browser:'#7ab8ef',
  chat:'#5ddaaa',
  music:'#f0b352',
  work:'#a8d865',
  tlauncher:'#006400',

  torrent:'#c678ff',
  photo:'#ff9ecb',
  vpn:'#58c4c4',
  archive:'#c9a66b',
  myapps:'#ff7b72',
  Paneltask:'#FFD700',

  video:'#f08080',
  idle:'rgba(255,255,255,0.15)',
  other:'rgba(255,255,255,0.15)'
};

const CAT_NAMES = {
    browser: '🌐 Браузер',
    chat: '💬 Общение',
    work: '💻 Работа',
    music: '🎵 Музыка',
    gaming: '🎮 Игры',
    Paneltask: '📟 Панель задач',

    torrent: '⬇️ Торренты',
    photo: '🖼️ Фото',
    vpn: '🔒 VPN',
    archive: '📦 Архивы',
    myapps: '🛠️ Мои приложения',
    tlauncher: "🧱 Майнкрафт",

    streaming: '📡 Стрим',
    idle: '😴 AFK',
    other: '• Другое'
};

function showPage(name,btn){
  ['main','stats','settings'].forEach(p=>{
    document.getElementById('page-'+p).style.display = p===name?'block':'none';
  });
  document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  if(name==='settings') loadSettings();
  if(name==='stats') loadStats('today');
}

function timeSince(iso){
  if(!iso) return '';
  const m=Math.floor((Date.now()-new Date(iso))/60000);
  if(m<1) return 'только что';
  if(m<60) return m+' мин';
  return Math.floor(m/60)+' ч '+(m%60)+' мин';
}

function fmtTime(s){
  if(s<60) return s+'с';
  const m=Math.floor(s/60);
  if(m<60) return m+'м';
  const h=Math.floor(m/60);
  return h+'ч '+(m%60?(' '+(m%60)+'м'):'');
}

let _prevApp={my:'',her:''};
function updateCard(prefix,data,online){
  document.getElementById(prefix+'-card').classList.toggle('offline-card',!online);
  const newApp=online?(data.app||'—'):'не в сети';
  if(newApp!==_prevApp[prefix]){
    _prevApp[prefix]=newApp;
    const card=document.getElementById(prefix+'-card');
    card.classList.remove('card-updated');
    void card.offsetWidth;
    card.classList.add('card-updated');
  }
  document.getElementById(prefix+'-app').textContent=newApp;
  document.getElementById(prefix+'-title').textContent=online?(data.title||''):'';
  document.getElementById(prefix+'-time').textContent=online?timeSince(data.since):'';
  if(data.name){
    document.getElementById(prefix+'-avatar').textContent=data.name[0].toUpperCase();
    document.getElementById(prefix+'-label').textContent=data.name;
    const col=document.getElementById(prefix==='my'?'my-col-title':'her-col-title');
    if(col) col.textContent=data.name;
  }
  const cat=data.afk?'idle':(data.category||'other');
  const badge=document.getElementById(prefix+'-badge');
  badge.className='badge badge-'+(online?cat:'idle');
  badge.textContent=!online?'офлайн':(data.afk?'😴 AFK':(BADGES[cat]||cat));
}

let _prevFirst={you:'',her:''};
function updateTimeline(myH,herH){
  const renderCol=(items,who)=>{
    if(!items||!items.length) return `
      <div class="tl-item">
        <div class="tl-time">—</div>
        <div class="tl-dot tl-dot-${who}"></div>
        <div class="tl-app">пусто</div>
      </div>`;
    return items.slice(0,8).map((h,i)=>{
      const isNew=i===0&&h.app!==_prevFirst[who];
      return `<div class="tl-item${isNew?' tl-item-new':''}">
        <div class="tl-time">${h.time}</div>
        <div class="tl-dot tl-dot-${who}"></div>
        <div class="tl-app">${h.app}${h.title?' — '+h.title:''}</div>
      </div>`;
    }).join('');
  };
  document.getElementById('timeline-you').innerHTML=renderCol(myH,'you');
  document.getElementById('timeline-her').innerHTML=renderCol(herH,'her');
  if(myH&&myH[0])  _prevFirst.you=myH[0].app;
  if(herH&&herH[0]) _prevFirst.her=herH[0].app;
}

function updateStatus(c){
  document.getElementById('conn-dot').className='dot '+(c?'dot-online':'dot-waiting');
  document.getElementById('conn-text').textContent=c?'оба онлайн':'ожидание партнёра...';
}

function loadSettings(){
  pywebview.api.get_settings().then(s=>{
    document.getElementById('inp-name').value=s.name||'';
    document.getElementById('inp-partner-name').value=s.partner_name||'';
    document.getElementById('inp-ip').value=s.ip||'';
    document.getElementById('my-ip').textContent=s.my_ip||'—';
    document.getElementById('btn-autostart').textContent=s.autostart?'включён ✓':'выключен';
    document.getElementById('tog-private').checked=s.private_mode||false;
  });
}

function saveSettings(){
  pywebview.api.save_settings({
    name:document.getElementById('inp-name').value,
    partner_name:document.getElementById('inp-partner-name').value,
    ip:document.getElementById('inp-ip').value,
  }).then(()=>{
    const b=document.getElementById('btn-save');
    b.textContent='Сохранено ✓';
    setTimeout(()=>b.textContent='Сохранить',1500);
  });
}

function savePrivate(val){ pywebview.api.save_settings({private_mode:val}); }

function toggleAutostart(){
  pywebview.api.toggle_autostart().then(on=>{
    document.getElementById('btn-autostart').textContent=on?'включён ✓':'выключен';
  });
}

function loadStats(period){
  document.getElementById('btn-today').className='btn'+(period==='today'?' btn-primary':'');
  document.getElementById('btn-week').className ='btn'+(period==='week' ?' btn-primary':'');
  pywebview.api.get_stats(period).then(data=>{
    document.getElementById('stats-date').textContent=
      period==='today'?'сегодня':'последние 7 дней';
    const total=data.total||1;
    document.getElementById('stats-categories').innerHTML=
      (data.categories||[]).length===0
        ? '<div style="color:rgba(255,255,255,0.2);font-size:12px;margin-bottom:8px">нет данных — запусти и поработай немного</div>'
        : (data.categories||[]).map(c=>{
            const pct=Math.round(c.seconds/total*100);
            const color=CAT_COLORS[c.category]||'rgba(255,255,255,0.2)';
            return `<div style="margin-bottom:8px">
              <div style="display:flex;justify-content:space-between;font-size:11px;
                color:rgba(255,255,255,0.4);margin-bottom:4px">
                <span>${CAT_NAMES[c.category] || c.category}</span>
                <span>${fmtTime(c.seconds)}</span></div>
              <div style="height:4px;background:rgba(255,255,255,0.06);border-radius:2px">
                <div style="height:4px;width:${pct}%;background:${color};
                  border-radius:2px;transition:width .5s ease"></div>
              </div></div>`;
          }).join('');
    document.getElementById('stats-apps').innerHTML=
      (data.apps||[]).map((a,i)=>{
        const color=CAT_COLORS[a.category]||'rgba(255,255,255,0.2)';
        return `<div class="tl-item" style="margin-bottom:5px">
          <div style="font-size:11px;color:rgba(255,255,255,0.2);min-width:16px">${i+1}</div>
          <div style="width:6px;height:6px;border-radius:50%;background:${color};flex-shrink:0;margin-top:3px"></div>
          <div style="flex:1;font-size:12px;color:rgba(255,255,255,0.7)">${a.app}</div>
          <div style="font-size:11px;color:rgba(255,255,255,0.3)">${fmtTime(a.seconds)}</div>
        </div>`;
      }).join('');
  }).catch(()=>{});
}

function tick(){
  if(!window.pywebview) return;
  pywebview.api.get_state().then(s=>{
    if(s.my) updateCard('my',s.my,true);
    updateStatus(s.connected);
    if(s.partner){
      updateCard('her',s.partner,true);
      updateTimeline(s.my_history,s.partner.history||[]);
    } else {
      updateCard('her',{},false);
      updateTimeline(s.my_history,[]);
    }
  }).catch(()=>{});
}

window.addEventListener('pywebviewready',()=>{ tick(); setInterval(tick,1500); });
</script>
</body>
</html>
"""


class WindowAPI:
    def get_state(self):
        from core.tracker import load_settings
        s         = load_settings()
        current   = _tracker.get_current()
        history   = _tracker.get_history()
        partner   = _network.get_partner_data() if _network else None
        connected = _network.is_connected()     if _network else False

        def fmt(items, who):
            return [{
                "app":   h.get("app","—"),
                "title": h.get("title",""),
                "time":  h["timestamp"].strftime("%H:%M") if h.get("timestamp") else "—",
                "ts":    h["timestamp"].isoformat()       if h.get("timestamp") else "0",
                "who":   who,
            } for h in items[:10]]

        return {
            "my": {
                "app":      current.get("app","—"),
                "title":    current.get("title",""),
                "since":    current.get("since", datetime.now()).isoformat(),
                "category": current.get("category","other"),
                "afk":      current.get("afk", False),
                "name":     s.get("name","Я"),
            },
            "my_history": fmt(history, "you"),
            "partner":    partner,
            "connected":  connected,
        }

    def get_settings(self):
        import socket as sk
        from core.tracker import load_settings
        from core.autostart import is_autostart_enabled
        s = load_settings()
        try:
            addrs = sk.getaddrinfo(sk.gethostname(), None)
            zt_ip = next((a[4][0] for a in addrs if a[4][0].startswith("10.")), "—")
        except Exception:
            zt_ip = "—"
        s["my_ip"]    = zt_ip
        s["autostart"] = is_autostart_enabled()
        return s

    def save_settings(self, data):
        from core.tracker import load_settings, _settings_path
        try:
            current = load_settings()
            current.update(data)
            with open(_settings_path(), "w", encoding="utf-8") as f:
                json.dump(current, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("save_settings error:", e)
        return True

    def get_stats(self, period):
        from core.stats import fmt_time
        if not _stats:
            return {"apps": [], "categories": [], "total": 0}
        if period == "week":
            apps = _stats.get_week()
            cats_raw = {}
            for a in apps:
                c = a["category"]
                cats_raw[c] = cats_raw.get(c, 0) + a["seconds"]
            categories = [{"category": k, "seconds": v}
                          for k, v in sorted(cats_raw.items(), key=lambda x: -x[1])]
        else:
            apps       = _stats.get_today()
            categories = _stats.get_category_totals()
        total = sum(a["seconds"] for a in apps)
        return {"apps": apps, "categories": categories, "total": total}

    def hide_window(self):
        if _window:
            _window.hide()

    def minimize_window(self):
        if _window:
            _window.minimize()

    def quit_app(self):
        _do_quit()

    def toggle_autostart(self):
        from core.autostart import setup_autostart, is_autostart_enabled
        enabled = is_autostart_enabled()
        setup_autostart(enable=not enabled)
        return not enabled


def _do_quit():
    _tracker.stop()
    if _network:
        _network.stop()
    if _stats:
        _stats.stop()
    if _window:
        _window.destroy()


def open_window():
    if _window:
        _window.show()


def run_webview_loop(tracker, network, stats=None):
    global _tracker, _network, _window, _stats
    import builtins

    _tracker = tracker
    _network = network
    _stats   = stats
    builtins._together_open_window = open_window
    builtins._together_quit        = _do_quit

    api = WindowAPI()
    _window = webview.create_window(
        title="Together",
        html=HTML,
        js_api=api,
        width=480,
        height=600,
        resizable=False,
        frameless=True,
        easy_drag=True,
        background_color="#0f0f13",
        hidden=True,
    )

    def hide_from_taskbar():
        import ctypes
        hwnd = ctypes.windll.user32.FindWindowW(None, "Together")
        if hwnd:
            GWL_EXSTYLE     = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW  = 0x00040000
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    threading.Timer(1.5, hide_from_taskbar).start()

    webview.start(debug=False)
    os._exit(0)
