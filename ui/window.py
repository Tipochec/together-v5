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
  .titlebar-close{-webkit-app-region:no-drag;width:28px;height:28px;border-radius:6px;border:none;
    background:transparent;color:rgba(255,255,255,0.3);cursor:pointer;font-size:16px;
    display:flex;align-items:center;justify-content:center}
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
  .section-title{font-size:10px;color:rgba(255,255,255,0.2);
    text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px}
  .history-cols{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:8px}
  .history-col-title{font-size:10px;color:rgba(255,255,255,0.2);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px}
  .timeline{display:flex;flex-direction:column;gap:5px}
  .tl-item{display:flex;align-items:flex-start;gap:8px;padding:7px 10px;
    background:#1a1820;border-radius:9px;border:0.5px solid rgba(255,255,255,0.05)}
  .tl-dot{width:5px;height:5px;border-radius:50%;flex-shrink:0;margin-top:4px}
  .tl-dot-you{background:#534ab7}.tl-dot-her{background:#d4537e}
  .tl-time{font-size:11px;color:rgba(255,255,255,0.2);min-width:36px;flex-shrink:0}
  .tl-app{font-size:12px;color:rgba(255,255,255,0.6);word-break:break-word;line-height:1.4}
  #page-settings{display:none}
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
  <!-- Кнопка закрытия скрывает окно через Python API -->
  <button class="titlebar-close" onclick="pywebview.api.hide_window()">✕</button>
</div>
<div class="content">
  <div class="nav">
    <button class="nav-btn active" onclick="showPage('main',this)">Активность</button>
    <button class="nav-btn" onclick="showPage('settings',this)">Настройки</button>
  </div>
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
          <div class="tl-item"><div class="tl-time">—</div><div class="tl-dot tl-dot-you"></div><div class="tl-app">—</div></div>
        </div>
      </div>
      <div>
        <div class="history-col-title" id="her-col-title">она</div>
        <div class="timeline" id="timeline-her">
          <div class="tl-item"><div class="tl-time">—</div><div class="tl-dot tl-dot-her"></div><div class="tl-app">—</div></div>
        </div>
      </div>
    </div>
  </div>
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

function showPage(name,btn){
  document.getElementById('page-main').style.display=name==='main'?'block':'none';
  document.getElementById('page-settings').style.display=name==='settings'?'block':'none';
  document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  if(name==='settings') loadSettings();
}

function timeSince(iso){
  if(!iso) return '';
  const m=Math.floor((Date.now()-new Date(iso))/60000);
  if(m<1) return 'только что';
  if(m<60) return m+' мин';
  return Math.floor(m/60)+' ч '+(m%60)+' мин';
}

function updateCard(prefix,data,online){
  document.getElementById(prefix+'-card').classList.toggle('offline-card',!online);
  document.getElementById(prefix+'-app').textContent=online?(data.app||'—'):'не в сети';
  document.getElementById(prefix+'-title').textContent=online?(data.title||''):'';
  document.getElementById(prefix+'-time').textContent=online?timeSince(data.since):'';
  if(data.name){
    document.getElementById(prefix+'-avatar').textContent=data.name[0].toUpperCase();
    document.getElementById(prefix+'-label').textContent=data.name;
    const colId = prefix==='my' ? 'my-col-title' : 'her-col-title';
    const colEl = document.getElementById(colId);
    if (colEl && data.name) colEl.textContent = data.name;
  }
  const cat=data.afk?'idle':(data.category||'other');
  const badge=document.getElementById(prefix+'-badge');
  badge.className='badge badge-'+(online?cat:'idle');
  badge.textContent=!online?'офлайн':(data.afk?'😴 AFK':(BADGES[cat]||cat));
}

function updateTimeline(myH, herH) {
  const renderCol = (items, who) => {
    if (!items || !items.length) return `
      <div class="tl-item">
        <div class="tl-time">—</div>
        <div class="tl-dot tl-dot-${who}"></div>
        <div class="tl-app">пусто</div>
      </div>`;
    return items.slice(0,8).map(h => `
      <div class="tl-item">
        <div class="tl-time">${h.time}</div>
        <div class="tl-dot tl-dot-${who}"></div>
        <div class="tl-app">${h.app}${h.title?' — '+h.title:''}</div>
      </div>`).join('');
  };
  document.getElementById('timeline-you').innerHTML = renderCol(myH, 'you');
  document.getElementById('timeline-her').innerHTML = renderCol(herH, 'her');
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
        s = load_settings()
        current   = _tracker.get_current()
        history   = _tracker.get_history()
        partner   = _network.get_partner_data() if _network else None
        connected = _network.is_connected()     if _network else False

        def fmt(items, who):
            return [{
                "app":   h.get("app","—"),
                "title": h.get("title",""),
                "time":  h["timestamp"].strftime("%H:%M") if h.get("timestamp") else "—",
                "who":   who,
            } for h in items[:10]]

        return {
            "my": {
                "app":      current.get("app","—"),
                "title":    current.get("title",""),
                "since":    current.get("since", datetime.now()).isoformat(),
                "category": current.get("category","other"),
                "afk":      current.get("afk", False),
                "name":     s.get("name", "Я"),
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

    def hide_window(self):
        """Скрывает окно — приложение продолжает работать в трее"""
        if _window:
            _window.hide()

    def quit_app(self):
        """Полный выход — вызывается из кнопки Выйти в настройках"""
        _do_quit()

    def toggle_autostart(self):
        from core.autostart import setup_autostart, is_autostart_enabled
        enabled = is_autostart_enabled()
        setup_autostart(enable=not enabled)
        return not enabled


def _do_quit():
    """Единая точка выхода — безопасно завершает всё"""
    _tracker.stop()
    if _network:
        _network.stop()
    if _window:
        _window.destroy()
    # destroy() завершит webview.start() → run_webview_loop вернётся → os._exit


def open_window():
    if _window:
        _window.show()


def run_webview_loop(tracker, network):
    global _tracker, _network, _window
    import builtins

    _tracker = tracker
    _network = network
    builtins._together_open_window = open_window
    builtins._together_quit = _do_quit  # трей вызывает это вместо sys.exit

    api = WindowAPI()
    _window = webview.create_window(
        title="Together",
        html=HTML,
        js_api=api,
        width=480,
        height=590,
        resizable=False,
        frameless=True,
        easy_drag=True,
        background_color="#0f0f13",
        hidden=True,
    )

    webview.start(debug=False)
    # Сюда попадаем после destroy() — финальный выход
    os._exit(0)
