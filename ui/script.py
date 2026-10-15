JS = r"""

// app/title приходят от партнёра по сети (core/network.py слушает порт
// 39721 без пароля и шифрования) — значит это ЧУЖИЕ, непроверенные
// строки. Раньше они вставлялись в innerHTML напрямую: посторонний,
// подключившийся к порту, мог прислать поддельный activity-пакет с
// title вида '<img src=x onerror="...">' и выполнить свой JS прямо в
// этом окне (а оттуда — вызвать pywebview.api.get_settings() и утащить
// API-ключ). escapeHtml() экранирует спецсимволы перед вставкой.
function escapeHtml(str){
  return String(str ?? '').replace(/[&<>"']/g, ch => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  }[ch]));
}

const BADGES={gaming:'🎮 игра',browser:'🌐 браузер',chat:'💬 чат',
  music:'🎵 музыка',video:'▶ видео',work:'💻 работа',
  idle:'😴 AFK',streaming:'📡 стрим',other:'•'};
const STATUS_LABEL={'active':'','afk':'😴 AFK'};

function runDebugScan(){
  const el=document.getElementById('debug-result');
  el.innerHTML='<div style="color:rgba(255,255,255,0.2)">сканирую...</div>';
  pywebview.api.debug_scan().then(rows=>{
    if(!rows||!rows.length){ el.innerHTML='<div>ничего не найдено</div>'; return; }
    el.innerHTML=rows.map(r=>`
      <div style="padding:4px 0;border-bottom:0.5px solid rgba(255,255,255,0.05);
        display:flex;justify-content:space-between;gap:8px">
        <span style="color:${r.ignored?'rgba(255,255,255,0.2)':'#a89ef0'}">${escapeHtml(r.proc)}</span>
        <span style="color:rgba(255,255,255,0.25);overflow:hidden;text-overflow:ellipsis;
          white-space:nowrap;flex:1;text-align:right">${escapeHtml(r.title)}</span>
        <span style="color:${r.ignored?'#d4537e':'#1d9e75'}">${r.ignored?('игнор'+(r.reason?': '+r.reason:'')):'учтён'}</span>
      </div>`).join('');
  }).catch(e=>{ el.innerHTML='<div style="color:#d4537e">ошибка: '+e+'</div>'; });
}
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
  if(name==='stats'){ loadStats('today'); loadTimeStats(); loadSessionHistory(); }
}

function loadSessionHistory(){
  pywebview.api.get_session_history().then(sessions=>{
    const el = document.getElementById('stats-sessions');
    if(!sessions || !sessions.length){
      el.innerHTML = '<div style="color:rgba(255,255,255,0.2)">пока пусто — появится после первого закрытия приложения</div>';
      return;
    }
    el.innerHTML = sessions.map(s=>{
      const start = new Date(s.started_at);
      const end   = new Date(s.ended_at);
      const now = new Date();
      const daysAgo = Math.round((new Date(now.toDateString()) - new Date(start.toDateString())) / 86400000);
      let dateStr;
      if(daysAgo===0) dateStr='сегодня';
      else if(daysAgo===1) dateStr='вчера';
      else if(daysAgo===2) dateStr='позавчера';
      else dateStr=start.toLocaleDateString([], {day:'2-digit', month:'2-digit'});
      const timeStr = `${start.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}–${end.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}`;
      const total = s.active + s.afk;
      const activePct = total ? Math.round(s.active/total*100) : 0;
      const isToday = daysAgo===0;
      return `<div style="display:flex;align-items:center;gap:10px;padding:9px 10px;
        margin-bottom:6px;background:#1a1820;border-radius:10px;
        border-left:2.5px solid ${isToday ? '#534ab7' : 'rgba(255,255,255,0.1)'}">
        <div style="flex:1;min-width:0">
          <div style="font-size:11px;color:rgba(255,255,255,0.75);margin-bottom:4px">
            ${isToday ? '<span style="color:#a89ef0">●</span> ' : ''}${dateStr}, ${timeStr}
          </div>
          <div style="height:4px;border-radius:2px;background:rgba(255,255,255,0.06);overflow:hidden;display:flex">
            <div style="width:${activePct}%;background:#534ab7"></div>
            <div style="width:${100-activePct}%;background:#f0b352"></div>
          </div>
        </div>
        <div style="text-align:right;flex-shrink:0">
          <div style="font-size:13px;font-weight:600;color:#e8e6f0">${fmtTime(total)}</div>
          <div style="font-size:9px;color:rgba(255,255,255,0.3)">${activePct}% активен</div>
        </div>
      </div>`;
    }).join('');
  }).catch(()=>{});
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
  const avatarEl = document.getElementById(prefix+'-avatar');
  if(data.name){
    document.getElementById(prefix+'-label').textContent=data.name;
    const col=document.getElementById(prefix==='my'?'my-col-title':'her-col-title');
    if(col) col.textContent=data.name;
  }
  if(data.avatar){
    avatarEl.style.backgroundImage=`url("${data.avatar}")`;
    avatarEl.classList.add('has-img');
    avatarEl.textContent='';
  } else {
    avatarEl.style.backgroundImage='';
    avatarEl.classList.remove('has-img');
    if(data.name) avatarEl.textContent=data.name[0].toUpperCase();
  }
  const genderClass = data.gender==='female' ? 'gender-female' : 'gender-male';
  const cardEl = document.getElementById(prefix+'-card');
  cardEl.classList.remove('gender-male','gender-female');
  cardEl.classList.add(genderClass);
  avatarEl.classList.remove('gender-male','gender-female');
  avatarEl.classList.add(genderClass);
  const status=data.status||'active';
  const cat=status==='afk'?'idle':(data.category||'other');
  const badge=document.getElementById(prefix+'-badge');
  badge.className='badge badge-'+(online?cat:'idle');
  if(!online) badge.textContent='офлайн';
  else if(status==='afk') badge.textContent='😴 AFK';
  else badge.textContent=BADGES[cat]||cat;
}

let _prevFirst={you:'',her:''};
function updateTimeline(myH,herH,myGender,herGender){
  const renderCol=(items,gender,colKey)=>{
    const dotClass = gender === 'female' ? 'tl-dot-female' : 'tl-dot-male';
    if(!items||!items.length) return `
      <div class="tl-item">
        <div class="tl-time">—</div>
        <div class="tl-dot ${dotClass}"></div>
        <div class="tl-app">пусто</div>
      </div>`;
    const topKey = (items[0].app||'') + (items[0].title||'') + (items[0].time||'');
    const isNew = topKey !== _prevFirst[colKey];
    _prevFirst[colKey] = topKey;

    return items.slice(0,8).map((h,i)=>{
      const isNewItem = (i === 0 && isNew);
      const app = escapeHtml(h.app);
      const title = h.title ? ' — '+escapeHtml(h.title) : '';
      return `<div class="tl-item${isNewItem?' tl-item-new':''}">
        <div class="tl-time">${escapeHtml(h.time)}</div>
        <div class="tl-dot ${dotClass}"></div>
        <div class="tl-app">${app}${title}</div>
      </div>`;
    }).join('');
  };
  const youHtml = renderCol(myH,myGender||'male','you');
  const herHtml = renderCol(herH,herGender||'female','her');
  const elYou = document.getElementById('timeline-you');
  const elHer = document.getElementById('timeline-her');
  if(elYou && elYou.innerHTML !== youHtml) elYou.innerHTML = youHtml;
  if(elHer && elHer.innerHTML !== herHtml) elHer.innerHTML = herHtml;
}

function updateStatus(c){
  document.getElementById('conn-dot').className='dot '+(c?'dot-online':'dot-waiting');
  document.getElementById('conn-text').textContent=c?'оба онлайн':'ожидание партнёра...';
}

function updatePartnerStatus(st){
  const el = document.getElementById('her-online-since');
  if(!st){ el.textContent=''; el.className='online-since'; return; }
  const verb = st.gender==='female' ? 'была' : 'был';
  if(st.online){
    el.className = 'online-since is-online';
    el.innerHTML = `<span class="dot"></span> в сети с ${st.since}`;
  } else {
    const mins = st.last_session_minutes || 0;
    const dur = mins >= 60 ? `${Math.floor(mins/60)}ч ${mins%60}м` : `${mins}м`;
    el.className = 'online-since is-offline';
    el.innerHTML = mins > 0
      ? `<span class="dot"></span> не в сети с ${st.since} (${verb} ${dur})`
      : `<span class="dot"></span> не в сети с ${st.since}`;
  }
}

function updateMyOnlineSince(since){
  const el = document.getElementById('my-online-since');
  if(!el) return;
  el.className = 'online-since is-online';
  el.innerHTML = since ? `<span class="dot"></span> в сети с ${since}` : '';
}

function renderAvatarPreview(dataUri){
  const el=document.getElementById('settings-avatar-preview');
  if(!el) return;
  if(dataUri){
    el.style.backgroundImage=`url("${dataUri}")`;
    el.classList.add('has-img');
    el.textContent='';
  } else {
    el.style.backgroundImage='';
    el.classList.remove('has-img');
    el.textContent='Я';
  }
}

function setupFirewall(){
  const b = document.getElementById('btn-firewall');
  const row = b.closest('.settings-row');
  b.textContent = 'ждём подтверждения...';
  pywebview.api.setup_firewall().then(ok=>{
    b.textContent = ok ? 'настроено ✓' : 'не удалось, повторить?';
    if(row) row.classList.add('settings-dirty');
  });
}

function repairFirewall(){
  const b = document.getElementById('btn-firewall-repair');
  const row = b.closest('.settings-row');
  const original = b.textContent;
  b.textContent = 'ждём подтверждения...';
  pywebview.api.repair_firewall().then(deleted=>{
    b.textContent = deleted ? 'готово — жди окно Windows' : 'не удалось, повторить?';
    if(row) row.classList.add('settings-dirty');
    setTimeout(()=>{ b.textContent = original; }, 4000);
  });
}

function pickAvatar(){
  pywebview.api.pick_avatar().then(uri=>{
    if(uri) renderAvatarPreview(uri);
  });
}

function removeAvatar(){
  pywebview.api.remove_avatar().then(()=>renderAvatarPreview(null));
}

// ── Настройки: отслеживание несохранённых изменений ──────────────
// Раньше "Приватный режим" сохранялся мгновенно по своему onchange, в
// обход кнопки "Сохранить" — а остальные поля ждали нажатия кнопки.
// Это и сбивало с толку ("сохранение не всегда требовало кнопку").
// Теперь ВСЕ поля настроек, включая приватный режим, копятся только в
// интерфейсе и уходят в settings.json одним пакетом по кнопке
// "Сохранить" — а до этого момента изменённая строка подсвечивается,
// чтобы было видно, что именно поменялось и ещё не сохранено.
const SETTINGS_FIELDS = {
  name:                   'inp-name',
  gender:                 'inp-gender',
  pairing_key:            'inp-pairing-key',
  private_mode:           'tog-private',
};

function generatePairingKey(){
  const chars = 'abcdefghjkmnpqrstuvwxyz23456789';
  const part = (len) => Array.from({length: len}, () => chars[Math.floor(Math.random() * chars.length)]).join('');
  const key = `tgt-${part(4)}-${part(4)}-${part(4)}`;
  const inp = document.getElementById('inp-pairing-key');
  if(inp){
    inp.value = key;
    _markSettingsDirty('inp-pairing-key');
  }
}

function copyPairingKey(btn){
  const inp = document.getElementById('inp-pairing-key');
  if(!inp || !inp.value) return;
  const text = inp.value;
  
  const showSuccess = () => {
    if(btn){
      const old = btn.textContent;
      btn.textContent = '✓';
      btn.style.color = '#78dce8';
      setTimeout(()=>{
        btn.textContent = old;
        btn.style.color = '';
      }, 1500);
    }
  };

  // 1. Стандартный execCommand через временный input
  try {
    inp.select();
    inp.setSelectionRange(0, 99999);
    if(document.execCommand('copy')){
      showSuccess();
      return;
    }
  } catch(e) {}

  // 2. Fallback через navigator.clipboard
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(text).then(showSuccess).catch(()=>{
      // 3. Через создание невидимого textarea
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      showSuccess();
    });
  }
}

let _settingsBaseline = {};

function _settingsFieldValue(elId){
  const el = document.getElementById(elId);
  if(!el) return undefined;
  return el.type==='checkbox' ? el.checked : el.value;
}

function _markSettingsDirty(elId){
  const el = document.getElementById(elId);
  if(!el) return;
  const row = el.closest('.settings-row');
  if(!row) return;
  const changed = _settingsFieldValue(elId) !== _settingsBaseline[elId];
  row.classList.toggle('settings-dirty', changed);
}

let _settingsWired = false;
function _wireSettingsDirtyTracking(){
  if(_settingsWired) return;
  _settingsWired = true;
  Object.values(SETTINGS_FIELDS).forEach(elId=>{
    const el = document.getElementById(elId);
    if(!el) return;
    const evt = (el.tagName==='SELECT' || el.type==='checkbox') ? 'change' : 'input';
    el.addEventListener(evt, ()=>_markSettingsDirty(elId));
  });
}

function loadSettings(){
  _wireSettingsDirtyTracking();
  pywebview.api.get_settings().then(s=>{
    document.getElementById('inp-name').value=s.name||'';
    document.getElementById('inp-gender').value=s.gender||'male';
    document.getElementById('inp-pairing-key').value=s.pairing_key||'';
    document.getElementById('btn-autostart').textContent=s.autostart?'включён ✓':'выключен';
    document.getElementById('tog-private').checked=s.private_mode||false;
    renderAvatarPreview(s.avatar||'');

    // Свежая точка отсчёта "что уже сохранено" + снимаем подсветку
    Object.entries(SETTINGS_FIELDS).forEach(([key,elId])=>{
      _settingsBaseline[elId] = _settingsFieldValue(elId);
    });
    document.querySelectorAll('.settings-row.settings-dirty')
      .forEach(r=>r.classList.remove('settings-dirty'));
  });
}

function saveSettings(){
  pywebview.api.save_settings({
    name:document.getElementById('inp-name').value,
    gender:document.getElementById('inp-gender').value,
    pairing_key:document.getElementById('inp-pairing-key').value,
    private_mode:document.getElementById('tog-private').checked,
  }).then(()=>{
    const b=document.getElementById('btn-save');
    b.textContent='Сохранено ✓';
    setTimeout(()=>b.textContent='Сохранить',1500);

    // Всё, что только что ушло в JSON, становится новой "базой" —
    // подсветка изменённых полей снимается, поля возвращаются к
    // обычному виду ровно так, как просили.
    Object.entries(SETTINGS_FIELDS).forEach(([key,elId])=>{
      _settingsBaseline[elId] = _settingsFieldValue(elId);
    });
    document.querySelectorAll('.settings-row.settings-dirty')
      .forEach(r=>r.classList.remove('settings-dirty'));
  });
}

function showNetworkLog(){
  const el=document.getElementById('network-log-result');
  el.textContent='читаю лог...';
  pywebview.api.get_network_log(20).then(text=>{
    el.textContent = text && text.length ? text : 'лог пуст — событий пока не было';
  }).catch(e=>{ el.textContent='ошибка чтения лога: '+e; });
}

function reconnectNetwork(){
  const btn=document.getElementById('btn-reconnect');
  if(btn) btn.textContent='⏳ Переподключение...';
  pywebview.api.reconnect_network().then(()=>{
    setTimeout(()=>{
      if(btn) btn.textContent='🔄 Переподключиться к серверу';
      showNetworkLog();
    }, 1500);
  }).catch(e=>{
    if(btn) btn.textContent='🔄 Переподключиться к серверу';
  });
}

function toggleAutostart(){
  const row = document.getElementById('btn-autostart').closest('.settings-row');
  pywebview.api.toggle_autostart().then(on=>{
    document.getElementById('btn-autostart').textContent=on?'включён ✓':'выключен';
    // Подсветка должна вести себя так же, как у остальных полей
    // настроек: гаснет только когда нажали "Сохранить" (см. общий
    // сброс .settings-dirty в конце saveSettings()), а НЕ сама по
    // себе через какой-то таймер — иначе получается заметное
    // расхождение в поведении между этой строкой и всеми остальными.
    if(row) row.classList.add('settings-dirty');
  });
}

function fmtHMS(s){
  if(!s||s<60) return s+'с';
  const m=Math.floor(s/60);
  if(m<60) return m+'м';
  const h=Math.floor(m/60);
  return h+'ч'+(m%60?' '+(m%60)+'м':'');
}

function loadTimeStats(){
  pywebview.api.get_time_stats().then(t=>{
    if(!t) return;
    const wholeSession = (t.active||0) + (t.afk||0);
    if(!wholeSession) return;
    const pctA = Math.round(t.active / wholeSession * 100);
    const el = document.getElementById('session-time');
    if(!el) return;
    el.innerHTML = `
      <div style="display:flex;justify-content:space-between;font-size:11px;color:rgba(255,255,255,0.35);margin-bottom:6px">
        <span>За сессию: <b style="color:rgba(255,255,255,0.7)">${fmtHMS(t.total)}</b></span>
        <span style="color:rgba(255,255,255,0.2)">${fmtHMS(t.afk)} AFK</span>
      </div>
      <div style="display:flex;height:6px;border-radius:3px;overflow:hidden;gap:2px">
        <div style="width:${pctA}%;background:#534ab7;border-radius:3px;transition:width .5s"></div>
        <div style="width:${100-pctA}%;background:rgba(255,255,255,0.08);border-radius:3px;transition:width .5s"></div>
      </div>
      <div style="display:flex;gap:12px;margin-top:5px;font-size:10px;color:rgba(255,255,255,0.25)">
        <span><span style="color:#a89ef0">■</span> активен ${fmtHMS(t.active)}</span>
        <span><span style="color:rgba(255,255,255,0.3)">■</span> AFK ${fmtHMS(t.afk)}</span>
      </div>`;
  }).catch(()=>{});
}

let _statsAppsCache = [];

function loadStats(period){
  document.getElementById('btn-today').className='btn'+(period==='today'?' btn-primary':'');
  document.getElementById('btn-week').className ='btn'+(period==='week' ?' btn-primary':'');
  document.getElementById('btn-all').className  ='btn'+(period==='all'  ?' btn-primary':'');
  window._lastStatsPeriod = period;
  pywebview.api.get_stats(period).then(data=>{
    document.getElementById('stats-date').textContent=
      period==='today'?'сегодня':(period==='week'?'последние 7 дней':'за всё время (топ-30)');
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

    _statsAppsCache = data.apps || [];
    document.getElementById('stats-apps').innerHTML=
      _statsAppsCache.length===0
        ? '<div style="color:rgba(255,255,255,0.2);font-size:12px">нет данных</div>'
        : _statsAppsCache.map((a,i)=>{
            const color = a.color || CAT_COLORS[a.category] || 'rgba(255,255,255,0.2)';
            const label = a.display_name || a.app;
            return `<div class="tl-item stat-row" style="margin-bottom:5px;cursor:pointer" onclick="openStatEdit(${i})">
              <div style="font-size:11px;color:rgba(255,255,255,0.2);min-width:16px">${i+1}</div>
              <div style="width:6px;height:6px;border-radius:50%;background:${color};flex-shrink:0;margin-top:3px"></div>
              <div style="flex:1;font-size:12px;color:rgba(255,255,255,0.7)">${escapeHtml(label)}</div>
              <div style="font-size:11px;color:rgba(255,255,255,0.3)">${fmtTime(a.seconds)}</div>
              <button class="stat-del-btn" title="Удалить из статистики" onclick="event.stopPropagation();promptDeleteStat(${i})">✕</button>
            </div>`;
          }).join('');
  }).catch(()=>{});
}

// ── Редактирование/исключение приложения в статистике ────────────────
function openStatEdit(i){
  const a = _statsAppsCache[i];
  if(!a) return;
  window._statEditApp = a.app;
  document.getElementById('stat-edit-title').textContent = a.app;
  document.getElementById('stat-edit-name').value = a.display_name || a.app;

  const sel = document.getElementById('stat-edit-category');
  sel.innerHTML = Object.keys(CAT_NAMES).map(k=>
    `<option value="${k}">${CAT_NAMES[k]}</option>`).join('')
    + `<option value="__new__">+ своя категория…</option>`;
  sel.value = a.category;
  document.getElementById('stat-edit-newcat-name').value = '';
  toggleNewCategoryRow();

  document.getElementById('stat-edit-color').value =
    (a.color || CAT_COLORS[a.category] || '#a89ef0');

  pywebview.api.get_stat_customization(a.app).then(c=>{
    document.getElementById('stat-edit-excluded').checked = !!(c && c.excluded);
  });

  document.getElementById('stat-edit-overlay').style.display = 'flex';
}

function closeStatEdit(){
  document.getElementById('stat-edit-overlay').style.display = 'none';
}

function toggleNewCategoryRow(){
  const sel = document.getElementById('stat-edit-category');
  const row = document.getElementById('stat-edit-newcat-row');
  if(row) row.style.display = (sel.value === '__new__') ? 'flex' : 'none';
}

function saveStatEdit(){
  const app = window._statEditApp;
  if(!app) return;
  const sel = document.getElementById('stat-edit-category');
  const color = document.getElementById('stat-edit-color').value;

  const finish = (categoryKey) => {
    const data = {
      display_name: document.getElementById('stat-edit-name').value.trim(),
      category:     categoryKey,
      color:        color,
      excluded:     document.getElementById('stat-edit-excluded').checked,
    };
    pywebview.api.save_stat_customization(app, data).then(()=>{
      closeStatEdit();
      loadStats(window._lastStatsPeriod || 'today');
    });
  };

  if(sel.value === '__new__'){
    const name = document.getElementById('stat-edit-newcat-name').value.trim();
    if(!name) return;  // без названия новую категорию не создаём
    pywebview.api.add_custom_category(name, color).then(cat=>{
      if(!cat) return;
      CAT_NAMES[cat.key]  = cat.name;
      CAT_COLORS[cat.key] = cat.color;
      finish(cat.key);
    });
  } else {
    finish(sel.value);
  }
}

function promptDeleteStat(i){
  const a = _statsAppsCache[i];
  if(!a) return;
  window._statDeleteApp = a.app;
  document.getElementById('stat-delete-text').textContent =
    `Удалить «${a.display_name || a.app}» из статистики? Удалятся все дни, не только сегодня.`;
  document.getElementById('stat-delete-overlay').style.display = 'flex';
}

function closeStatDelete(){
  document.getElementById('stat-delete-overlay').style.display = 'none';
}

function confirmDeleteStat(){
  const app = window._statDeleteApp;
  if(!app) return;
  pywebview.api.delete_stat(app).then(()=>{
    closeStatDelete();
    loadStats(window._lastStatsPeriod || 'today');
  });
}


function tick(){
  if(!window.pywebview) return;
  pywebview.api.get_state().then(s=>{
    const myGender = (s.my && s.my.gender) || 'male';
    const herGender = (s.partner && s.partner.gender) || (myGender === 'male' ? 'female' : 'male');
    if(s.my) updateCard('my',s.my,true);
    updateStatus(s.connected);
    updatePartnerStatus(s.partner_status);
    updateMyOnlineSince(s.my_online_since);
    const statsPage = document.getElementById('page-stats');
    if(statsPage && statsPage.style.display === 'block') loadTimeStats();
    if(s.partner && s.connected){
      updateCard('her',s.partner,true);
      updateTimeline(s.my_history,s.partner.history||[],myGender,herGender);
    } else {
      updateCard('her',s.partner||{},false);
      updateTimeline(s.my_history,[],myGender,herGender);
    }
    if(!document.hidden && !_windowIsHidden && _pendingHeartSender){
      const s = _pendingHeartSender;
      _pendingHeartSender = null;
      setTimeout(()=>triggerHeartCelebration(s), 200);
    }
  }).catch(()=>{});
}

window.addEventListener('pywebviewready',()=>{
  tick(); setInterval(tick,1500);
  loadCustomCategories();
});

// Категории, которые пользователь добавил сам через "+ своя категория" в
// окне редактирования приложения в статистике — подмешиваем поверх
// встроенных CAT_NAMES/CAT_COLORS один раз при старте.
function loadCustomCategories(){
  pywebview.api.get_custom_categories().then(cats=>{
    Object.entries(cats||{}).forEach(([key,c])=>{
      CAT_NAMES[key]  = c.name;
      CAT_COLORS[key] = c.color;
    });
  }).catch(()=>{});
}

function openChat(){
  setChatBadge(false);           // открываем чат — считаем что всё прочитано
  pywebview.api.open_chat();
}

function setChatBadge(show){
  const b = document.getElementById('chat-badge');
  if(b) b.style.display = show ? 'block' : 'none';
}

function sendHeartPing(){
  const btn = document.getElementById('btn-send-heart');
  if(btn){
    btn.classList.add('sent');
    setTimeout(()=>btn.classList.remove('sent'), 700);
  }
  spawnHeartAnimation();
  showHeartBanner('ОХАЁ)');
  if(window.pywebview && window.pywebview.api && window.pywebview.api.send_heart){
    window.pywebview.api.send_heart().catch(e=>console.error('Heart send error:', e));
  }
}

let _windowIsHidden = false;
let _pendingHeartSender = null;

function onWindowHidden(){
  _windowIsHidden = true;
}

function onWindowRestored(){
  _windowIsHidden = false;
  if(_pendingHeartSender){
    const s = _pendingHeartSender;
    _pendingHeartSender = null;
    setTimeout(()=>triggerHeartCelebration(s), 250);
  }
}

function queuePendingHeart(senderName){
  _pendingHeartSender = senderName || 'Партнёр';
}

function onHeartReceived(senderName){
  const sender = senderName || 'Партнёр';
  if (document.hidden || _windowIsHidden) {
    _pendingHeartSender = sender;
  } else {
    triggerHeartCelebration(sender);
  }
}

function showHeartBanner(text){
  const old = document.querySelector('.heart-banner');
  if(old) old.remove();
  const banner = document.createElement('div');
  banner.className = 'heart-banner';
  banner.innerHTML = `<span>❤️</span> <span>${escapeHtml(text)}</span>`;
  document.body.appendChild(banner);
  setTimeout(()=>{ if(banner.parentNode) banner.remove(); }, 3200);
}

function triggerHeartCelebration(senderName){
  showHeartBanner('ОХАЁ)');
  spawnHeartAnimation();
  const card = document.getElementById('her-card');
  if(card){
    card.classList.remove('offline-card');
    card.classList.add('card-updated');
    setTimeout(()=>card.classList.remove('card-updated'), 1200);
  }
}

window.addEventListener('focus', ()=>{
  _windowIsHidden = false;
  if(_pendingHeartSender){
    const s = _pendingHeartSender;
    _pendingHeartSender = null;
    setTimeout(()=>triggerHeartCelebration(s), 250);
  }
});

document.addEventListener('visibilitychange', ()=>{
  if(!document.hidden){
    _windowIsHidden = false;
    if(_pendingHeartSender){
      const s = _pendingHeartSender;
      _pendingHeartSender = null;
      setTimeout(()=>triggerHeartCelebration(s), 250);
    }
  } else {
    _windowIsHidden = true;
  }
});

function spawnHeartAnimation(){
  const container = document.getElementById('heart-burst');
  if(!container) return;
  const hearts = ['❤️', '💖', '💕', '✨', '💓', '💗'];
  for(let i = 0; i < 6; i++){
    setTimeout(()=>{
      const el = document.createElement('div');
      el.className = 'flying-heart';
      el.textContent = hearts[Math.floor(Math.random() * hearts.length)];
      el.style.left = (15 + Math.random() * 70) + '%';
      el.style.top = (40 + Math.random() * 40) + '%';
      container.appendChild(el);
      setTimeout(()=>el.remove(), 1200);
    }, i * 120);
  }
}

"""