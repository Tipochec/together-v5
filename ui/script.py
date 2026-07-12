JS = r"""

const BADGES={gaming:'🎮 игра',browser:'🌐 браузер',chat:'💬 чат',
  music:'🎵 музыка',video:'▶ видео',work:'💻 работа',
  idle:'😴 AFK',streaming:'📡 стрим',other:'•'};
const STATUS_LABEL={'active':'','watching':'📺 медиа','afk':'😴 AFK'};

function runDebugScan(){
  const el=document.getElementById('debug-result');
  el.innerHTML='<div style="color:rgba(255,255,255,0.2)">сканирую...</div>';
  pywebview.api.debug_scan().then(rows=>{
    if(!rows||!rows.length){ el.innerHTML='<div>ничего не найдено</div>'; return; }
    el.innerHTML=rows.map(r=>`
      <div style="padding:4px 0;border-bottom:0.5px solid rgba(255,255,255,0.05);
        display:flex;justify-content:space-between;gap:8px">
        <span style="color:${r.ignored?'rgba(255,255,255,0.2)':'#a89ef0'}">${r.proc}</span>
        <span style="color:rgba(255,255,255,0.25);overflow:hidden;text-overflow:ellipsis;
          white-space:nowrap;flex:1;text-align:right">${r.title}</span>
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
  const status=data.status||'active';
  const cat=status==='afk'?'idle':(data.category||'other');
  const badge=document.getElementById(prefix+'-badge');
  badge.className='badge badge-'+(online?cat:'idle');
  if(!online) badge.textContent='офлайн';
  else if(status==='afk') badge.textContent='😴 AFK';
  else if(status==='watching') badge.textContent='📺 смотрит';
  else badge.textContent=BADGES[cat]||cat;
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
      const isNew=i===0&&(h.app+h.time)!==_prevFirst[who];
      return `<div class="tl-item${isNew?' tl-item-new':''}">
        <div class="tl-time">${h.time}</div>
        <div class="tl-dot tl-dot-${who}"></div>
        <div class="tl-app">${h.app}${h.title?' — '+h.title:''}</div>
      </div>`;
    }).join('');
  };
  document.getElementById('timeline-you').innerHTML=renderCol(myH,'you');
  document.getElementById('timeline-her').innerHTML=renderCol(herH,'her');
  if(myH&&myH[0])  _prevFirst.you=myH[0].app+myH[0].time;
  if(herH&&herH[0]) _prevFirst.her=herH[0].app+herH[0].time;
}

function updateStatus(c){
  document.getElementById('conn-dot').className='dot '+(c?'dot-online':'dot-waiting');
  document.getElementById('conn-text').textContent=c?'оба онлайн':'ожидание партнёра...';
}

function updateConnLog(log){
  const el = document.getElementById('conn-log');
  if(!log || !log.length){ el.innerHTML=''; return; }
  // Последние 6 событий, самое новое справа
  el.innerHTML = log.slice(-6).map(e =>
    `<span>${e.online ? '🟢' : '🔴'} ${e.time}</span>`
  ).join('<span style="opacity:.3">·</span>');
}

function loadSettings(){
  pywebview.api.get_settings().then(s=>{
    document.getElementById('inp-name').value=s.name||'';
    document.getElementById('inp-partner-name').value=s.partner_name||'';
    document.getElementById('inp-ip').value=s.ip||'';
    document.getElementById('inp-openrouter-key').value=s.openrouter_api_key||'';
    document.getElementById('inp-extra-ignore').value=(s.extra_ignore_processes||[]).join(', ');
    document.getElementById('inp-custom-sound').value=s.custom_sound_path||'';
    document.getElementById('inp-my-ip').value=s.my_ip||'';
    document.getElementById('btn-autostart').textContent=s.autostart?'включён ✓':'выключен';
    document.getElementById('tog-private').checked=s.private_mode||false;
  });
}

function saveSettings(){
  const extraIgnore = document.getElementById('inp-extra-ignore').value
    .split(',').map(s=>s.trim()).filter(Boolean);
  pywebview.api.save_settings({
    name:document.getElementById('inp-name').value,
    partner_name:document.getElementById('inp-partner-name').value,
    ip:document.getElementById('inp-ip').value,
    openrouter_api_key:document.getElementById('inp-openrouter-key').value,
    extra_ignore_processes:extraIgnore,
    custom_sound_path:document.getElementById('inp-custom-sound').value,
    my_ip_override:document.getElementById('inp-my-ip').value,
  }).then(()=>{
    const b=document.getElementById('btn-save');
    b.textContent='Сохранено ✓';
    setTimeout(()=>b.textContent='Сохранить',1500);
  });
}

function showAiLog(){
  const el=document.getElementById('ai-log-result');
  el.textContent='читаю лог...';
  pywebview.api.get_ai_log().then(text=>{
    el.textContent = text && text.length ? text : 'лог пуст — запросов к AI ещё не было';
  }).catch(e=>{ el.textContent='ошибка чтения лога: '+e; });
}

function savePrivate(val){ pywebview.api.save_settings({private_mode:val}); }

function toggleAutostart(){
  pywebview.api.toggle_autostart().then(on=>{
    document.getElementById('btn-autostart').textContent=on?'включён ✓':'выключен';
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
    if(!t||!t.total) return;
    const pctA = Math.round(t.active   / (t.total||1) * 100);
    const pctW = Math.round(t.watching / (t.total||1) * 100);
    const el = document.getElementById('session-time');
    if(!el) return;
    el.innerHTML = `
      <div style="display:flex;justify-content:space-between;font-size:11px;color:rgba(255,255,255,0.35);margin-bottom:6px">
        <span>За сессию: <b style="color:rgba(255,255,255,0.7)">${fmtHMS(t.total)}</b></span>
        <span style="color:rgba(255,255,255,0.2)">${fmtHMS(t.afk)} AFK</span>
      </div>
      <div style="display:flex;height:6px;border-radius:3px;overflow:hidden;gap:2px">
        <div style="width:${pctA}%;background:#534ab7;border-radius:3px;transition:width .5s"></div>
        <div style="width:${pctW}%;background:#d4537e;border-radius:3px;transition:width .5s"></div>
      </div>
      <div style="display:flex;gap:12px;margin-top:5px;font-size:10px;color:rgba(255,255,255,0.25)">
        <span><span style="color:#a89ef0">■</span> активен ${fmtHMS(t.active)}</span>
        <span><span style="color:#d4537e">■</span> медиа ${fmtHMS(t.watching)}</span>
      </div>`;
  }).catch(()=>{});
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
    updateConnLog(s.connection_log);
    // Раньше тут проверялось только "есть ли вообще когда-либо полученные
    // данные о партнёре" (s.partner) — из-за этого карточка навсегда
    // застревала на последнем известном приложении/вкладке даже после
    // того, как партнёр вышел из сети. Теперь online по-настоящему зависит
    // от актуального connected-статуса.
    if(s.partner && s.connected){
      updateCard('her',s.partner,true);
      updateTimeline(s.my_history,s.partner.history||[]);
    } else {
      updateCard('her',s.partner||{},false);
      updateTimeline(s.my_history,[]);
    }
  }).catch(()=>{});
}

window.addEventListener('pywebviewready',()=>{ tick(); setInterval(tick,1500); });

function openChat(){
  setChatBadge(false);           // открываем чат — считаем что всё прочитано
  pywebview.api.open_chat();
}

function setChatBadge(show){
  const b = document.getElementById('chat-badge');
  if(b) b.style.display = show ? 'block' : 'none';
}

"""