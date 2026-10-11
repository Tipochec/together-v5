from .styles import CSS
from .script import JS

HTML = r"""
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Together</title>
<style>
{styles}
</style>
</head>
<body>
<div class="titlebar pywebview-drag-region">
  <div class="titlebar-title"><span class="heart">♥</span> Together</div>
    <div class="titlebar-btns">
        <button class="titlebar-btn" id="btn-chat" onclick="openChat()" title="Чат" style="position:relative">
          💬
          <span id="chat-badge" style="display:none;position:absolute;top:2px;right:2px;
            width:8px;height:8px;border-radius:50%;background:#e5484d;
            box-shadow:0 0 0 2px #16141c;"></span>
        </button>
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
    <div class="status-row" style="justify-content:center">
      <div class="dot dot-waiting" id="conn-dot"></div>
      <span class="status-text" id="conn-text">ожидание партнёра...</span>
    </div>
    <div class="cards">
      <div class="card card-you" id="my-card">
        <div class="online-since" id="my-online-since"></div>
        <div class="avatar" id="my-avatar">Я</div>
        <div class="card-label" id="my-label">ты</div>
        <div class="card-app" id="my-app">загрузка...</div>
        <div class="card-title" id="my-title"></div>
        <div class="card-time" id="my-time"></div>
        <div class="badge badge-idle" id="my-badge">—</div>
      </div>
      <div class="card card-her offline-card" id="her-card" style="position:relative">
        <button id="btn-send-heart" class="btn-heart-ping" onclick="sendHeartPing()" title="Отправить сердечко: думаю о тебе ❤️">❤️</button>
        <div id="heart-burst" class="heart-burst"></div>
        <div class="online-since" id="her-online-since"></div>
        <div class="avatar" id="her-avatar">?</div>
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
    <div id="session-time" style="background:#1a1820;border-radius:10px;padding:10px 12px;margin-bottom:14px;border:0.5px solid rgba(255,255,255,0.06)"></div>
    <div class="section-title" id="stats-date">сегодня</div>
    <div id="stats-categories" style="margin-bottom:16px"></div>
    <div class="section-title">топ приложений <span style="text-transform:none;color:rgba(255,255,255,0.2)">(нажми на строку — переименовать/перекрасить/исключить)</span></div>
    <div id="stats-apps"></div>
    <div style="display:flex;gap:6px;margin-top:14px">
      <button class="btn btn-primary" id="btn-today" onclick="loadStats('today')" style="flex:1">Сегодня</button>
      <button class="btn" id="btn-week" onclick="loadStats('week')" style="flex:1">7 дней</button>
      <button class="btn" id="btn-all" onclick="loadStats('all')" style="flex:1">Всё время</button>
    </div>
    <div class="section-title" style="margin-top:16px">история сессий</div>
    <div id="stats-sessions" style="font-size:11px;color:rgba(255,255,255,0.3)"></div>
  </div>

  <!-- Окно редактирования приложения в статистике: название, категория,
       цвет и исключение — всё в одном месте, как и просили. -->
  <div id="stat-edit-overlay" class="modal-overlay" style="display:none">
    <div class="modal-box">
      <div class="modal-title" id="stat-edit-title">Настройка приложения</div>

      <div class="modal-row">
        <span class="modal-label">Название</span>
        <input class="si" id="stat-edit-name" style="width:170px">
      </div>
      <div class="modal-row">
        <span class="modal-label">Категория</span>
        <select class="si" id="stat-edit-category" style="width:170px" onchange="toggleNewCategoryRow()"></select>
      </div>
      <div class="modal-row" id="stat-edit-newcat-row" style="display:none">
        <span class="modal-label">Название</span>
        <input class="si" id="stat-edit-newcat-name" style="width:170px" placeholder="Например: Стриминг">
      </div>
      <div class="modal-row">
        <span class="modal-label">Цвет</span>
        <input type="color" id="stat-edit-color" class="color-input">
      </div>
      <div class="modal-row">
        <span class="modal-label">🚫 Исключить из статистики</span>
        <label class="toggle">
          <input type="checkbox" id="stat-edit-excluded"/>
          <span class="toggle-slider"></span>
        </label>
      </div>

      <div class="confirm-btns" style="margin-top:14px">
        <button class="confirm-btn confirm-cancel" onclick="closeStatEdit()">Отмена</button>
        <button class="confirm-btn confirm-ok" onclick="saveStatEdit()">Сохранить</button>
      </div>
    </div>
  </div>

  <!-- Подтверждение удаления строки статистики — удаляет ВСЕ дни этого
       приложения, не только сегодняшний. -->
  <div id="stat-delete-overlay" class="modal-overlay" style="display:none">
    <div class="modal-box">
      <div class="confirm-text" id="stat-delete-text">Удалить это приложение из статистики?</div>
      <div class="confirm-btns">
        <button class="confirm-btn confirm-cancel" onclick="closeStatDelete()">Отмена</button>
        <button class="confirm-btn confirm-ok" onclick="confirmDeleteStat()">Удалить</button>
      </div>
    </div>
  </div>


  <!-- НАСТРОЙКИ -->
  <div id="page-settings">
    <div class="settings-row">
      <span class="settings-label">
        🖼️ Моя аватарка
        <span class="help-icon help-icon-down" tabindex="0">?
          <span class="help-tooltip">Квадратная фотка, которая видна партнёру и тебе на карточке. <b>JPG/PNG</b>, любой размер — само обрежется по центру в квадрат.</span>
        </span>
      </span>
      <div style="display:flex;align-items:center;gap:8px">
        <div class="avatar gender-male" id="settings-avatar-preview" style="width:40px;height:40px;margin-bottom:0">Я</div>
        <button class="btn" onclick="pickAvatar()">Выбрать файл</button>
        <button class="btn btn-danger" onclick="removeAvatar()" title="Убрать аватарку">✕</button>
      </div>
    </div>
    <div class="settings-row">
      <span class="settings-label">
        👤 Моё имя
        <span class="help-icon" tabindex="0">?
          <span class="help-tooltip">Твоё имя или никнейм, который увидит партнёр.</span>
        </span>
      </span>
      <input class="si" id="inp-name" placeholder="Введи имя"/>
    </div>
    <div class="settings-row">
      <span class="settings-label">
        ⚧ Мой пол
        <span class="help-icon" tabindex="0">?
          <span class="help-tooltip">Влияет на <b>цвет акцента твоей карточки</b> у тебя и у партнёра.</span>
        </span>
      </span>
      <select class="si" id="inp-gender">
        <option value="male">Мужской</option>
        <option value="female">Женский</option>
      </select>
    </div>
    <div class="settings-row">
      <span class="settings-label">
        🔒 Ключ подключения
        <span class="help-icon" tabindex="0">?
          <span class="help-tooltip">Общий ключ комнаты для вас двоих. Введите <b>одинаковый ключ</b> себе и партнёру, либо сгенерируйте случайный.</span>
        </span>
      </span>
      <div style="display:flex;gap:6px;width:60%">
        <input class="si" id="inp-pairing-key" placeholder="общий ключ комнаты" type="text" style="flex:1"/>
        <button class="btn" onclick="generatePairingKey()" title="Сгенерировать случайный надёжный ключ" style="padding:4px 8px;font-size:14px">🎲</button>
        <button class="btn" onclick="copyPairingKey(this)" title="Скопировать ключ" style="padding:4px 8px;font-size:14px">📋</button>
      </div>
    </div>
    <div class="settings-row">
      <span class="settings-label">
        🕵️ Приватный режим
        <span class="help-icon" tabindex="0">?
          <span class="help-tooltip">Скрывает названия открытых вкладок и сайтов — отображается только название браузера.</span>
        </span>
      </span>
      <label class="toggle">
        <input type="checkbox" id="tog-private"/>
        <span class="toggle-slider"></span>
      </label>
    </div>
    <div class="settings-row">
      <span class="settings-label">
        🚀 Автозапуск с Windows
        <span class="help-icon" tabindex="0">?
          <span class="help-tooltip">Запускает приложение в фоне при старте системы.</span>
        </span>
      </span>
      <button class="btn" id="btn-autostart" onclick="toggleAutostart()">проверка...</button>
    </div>
    <div style="margin-top:16px;display:flex;gap:8px">
      <button class="btn btn-primary" id="btn-save" onclick="saveSettings()">Сохранить</button>
      <button class="btn btn-danger" onclick="pywebview.api.quit_app()">Выйти</button>
    </div>
    <div style="margin-top:16px">
      <button class="btn" onclick="runDebugScan()" style="width:100%">🔍 Что видит сканер сейчас?</button>
      <div id="debug-result" style="margin-top:10px;font-size:11px;color:rgba(255,255,255,0.4);
        max-height:200px;overflow-y:auto"></div>
    </div>
    <div style="margin-top:10px">
      <button class="btn" onclick="showNetworkLog()" style="width:100%">🌐 Лог сети (последние 20 строк)</button>
      <div id="network-log-result" style="margin-top:10px;font-size:11px;color:rgba(255,255,255,0.4);
        max-height:200px;overflow-y:auto;white-space:pre-wrap"></div>
    </div>
  </div>
</div>

<script>
{script}
</script>
</body>
</html>
"""
HTML = HTML.format(
    styles=CSS,
    script=JS
)
