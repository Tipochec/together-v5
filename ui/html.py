from .styles import CSS
from .script import JS
from core.version import APP_VERSION
from core.paths import is_test_instance

test_tag = '<span style="font-size:10px;font-weight:700;padding:1px 6px;background:#e5484d;color:#fff;border-radius:4px;margin-left:6px;vertical-align:middle;display:inline-block;">ТЕСТ</span>' if is_test_instance() else ''

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
  <div class="titlebar-title"><span class="heart">♥</span> Together{test_tag}</div>
    <div class="titlebar-btns">
        <button class="titlebar-btn" id="btn-volume" onclick="toggleVolumeMixer()" title="Микшер громкости">🔊</button>
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

<div id="volume-mixer-popup" class="volume-mixer-popup" style="display:none">
  <div class="mixer-header">
    <span class="mixer-title">🔊 Микшер громкости</span>
    <button class="mixer-close" onclick="toggleVolumeMixer()">✕</button>
  </div>
  
  <div class="mixer-item">
    <div class="mixer-item-header">
      <span>❤️ Сердечко (ОХАЁ)</span>
      <span class="mixer-val" id="mixer-val-heart">80%</span>
    </div>
    <div class="mixer-controls">
      <input type="range" min="0" max="100" value="80" class="volume-slider" id="slider-heart" oninput="onVolumeSliderInput('heart', this.value)" onchange="onVolumeSliderChange('heart', this.value)"/>
      <button class="mixer-test-btn" onclick="testSound('heart')" title="Проверить громкость">▶</button>
    </div>
  </div>

  <div class="mixer-item" style="margin-top:12px">
    <div class="mixer-item-header">
      <span>💬 Сообщения чата</span>
      <span class="mixer-val" id="mixer-val-chat">80%</span>
    </div>
    <div class="mixer-controls">
      <input type="range" min="0" max="100" value="80" class="volume-slider" id="slider-chat" oninput="onVolumeSliderInput('chat', this.value)" onchange="onVolumeSliderChange('chat', this.value)"/>
      <button class="mixer-test-btn" onclick="testSound('chat')" title="Проверить громкость">▶</button>
    </div>
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
      <div class="card card-you" id="my-card" style="position:relative">
        <button id="btn-toggle-afk" class="btn-afk-toggle" onclick="toggleAfk()" title="Я отошёл (AFK)">🌙</button>
        <div class="online-since" id="my-online-since"></div>
        <div class="avatar" id="my-avatar">Я</div>
        <div class="card-label" id="my-label">ты</div>
        <div class="card-app" id="my-app">загрузка...</div>
        <div class="card-title" id="my-title"></div>
        <div class="card-time" id="my-time"></div>
        <div class="badge badge-idle" id="my-badge">—</div>
      </div>
      <div class="card card-her offline-card" id="her-card" style="position:relative">
        <button id="btn-send-heart" class="btn-heart-ping" onclick="sendHeartPing()" title="ОХАЁ)">❤️</button>
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
  <div id="page-settings" class="settings-page">

    <!-- ПРОФИЛЬ -->
    <div class="settings-section-title">
      <span>👤 Профиль</span>
    </div>
    <div class="settings-card">
      <div class="settings-row">
        <div class="settings-row-main">
          <div class="settings-row-title">Аватарка</div>
          <div class="settings-row-desc">Отображается на карточке активности</div>
        </div>
        <div class="settings-row-ctrl avatar-ctrl">
          <div class="avatar gender-male" id="settings-avatar-preview">Я</div>
          <button class="btn-settings-action" onclick="pickAvatar()">Сменить</button>
          <button class="btn-settings-icon btn-danger" onclick="removeAvatar()" title="Удалить аватарку">✕</button>
        </div>
      </div>

      <div class="settings-row">
        <div class="settings-row-main">
          <div class="settings-row-title">Имя</div>
          <div class="settings-row-desc">Имя или никнейм, который видит партнёр</div>
        </div>
        <div class="settings-row-ctrl">
          <input class="settings-input" id="inp-name" placeholder="Введи имя" maxlength="32"/>
        </div>
      </div>

      <div class="settings-row">
        <div class="settings-row-main">
          <div class="settings-row-title">Акцент карточки</div>
          <div class="settings-row-desc">Цвет оформления (мужской — синий, женский — розовый)</div>
        </div>
        <div class="settings-row-ctrl">
          <div class="segmented-control">
            <button type="button" class="segmented-btn active" id="gender-male" onclick="setGender('male')">♂ Мужской</button>
            <button type="button" class="segmented-btn" id="gender-female" onclick="setGender('female')">♀ Женский</button>
          </div>
          <input type="hidden" id="inp-gender" value="male"/>
        </div>
      </div>
    </div>

    <!-- СВЯЗЬ С ПАРТНЁРОМ -->
    <div class="settings-section-title">
      <span>🔗 Связь с партнёром</span>
    </div>
    <div class="settings-card">
      <div class="settings-row">
        <div class="settings-row-main">
          <div class="settings-row-title">Ключ комнаты</div>
          <div class="settings-row-desc">Общий секретный ключ для подключения друг к другу</div>
        </div>
        <div class="settings-row-ctrl key-ctrl">
          <input class="settings-input key-input" id="inp-pairing-key" placeholder="ключ комнаты" type="text" spellcheck="false"/>
          <button class="btn-settings-icon" onclick="generatePairingKey()" title="Сгенерировать надёжный ключ">🎲</button>
          <button class="btn-settings-icon" onclick="copyPairingKey(this)" title="Скопировать ключ">📋</button>
        </div>
      </div>
    </div>

    <!-- ПРИВАТНОСТЬ И СИСТЕМА -->
    <div class="settings-section-title">
      <span>⚙️ Приватность и система</span>
    </div>
    <div class="settings-card">
      <div class="settings-row">
        <div class="settings-row-main">
          <div class="settings-row-title">Приватный режим</div>
          <div class="settings-row-desc">Скрывать названия открытых сайтов и вкладок</div>
        </div>
        <div class="settings-row-ctrl">
          <label class="toggle">
            <input type="checkbox" id="tog-private"/>
            <span class="toggle-slider"></span>
          </label>
        </div>
      </div>

      <div class="settings-row">
        <div class="settings-row-main">
          <div class="settings-row-title">Автозапуск с Windows</div>
          <div class="settings-row-desc">Запускать Together в фоне при старте системы</div>
        </div>
        <div class="settings-row-ctrl">
          <label class="toggle">
            <input type="checkbox" id="tog-autostart" onchange="toggleAutostart()"/>
            <span class="toggle-slider"></span>
          </label>
          <button id="btn-autostart" style="display:none"></button>
        </div>
      </div>

      <div class="settings-row">
        <div class="settings-row-main">
          <div class="settings-row-title">Звуковые уведомления</div>
          <div class="settings-row-desc">Громкость сердечка (ОХАЁ) и сообщений чата</div>
        </div>
        <div class="settings-row-ctrl">
          <button class="btn-settings-action" onclick="toggleVolumeMixer()">Настроить 🔊</button>
        </div>
      </div>
    </div>

    <!-- О ПРИЛОЖЕНИИ -->
    <div class="settings-section-title">
      <span>ℹ️ О приложении</span>
    </div>
    <div class="settings-card update-card">
      <div class="settings-row">
        <div class="settings-row-main">
          <div class="settings-row-title">Together <span id="app-version-badge" class="version-pill">v{version}</span></div>
          <div id="update-status-text" class="settings-row-desc">Проверить наличие обновлений</div>
        </div>
        <div class="settings-row-ctrl">
          <button class="btn-settings-action" id="btn-check-update" onclick="checkUpdate()">Проверить</button>
        </div>
      </div>
      <div id="update-action-box" class="update-action-box" style="display:none">
        <div id="update-notes" class="update-notes"></div>
        <button class="btn btn-primary" id="btn-apply-update" onclick="applyUpdate()" style="width:100%">📥 Скачать и установить обновление</button>
      </div>
    </div>

    <!-- ДИАГНОСТИКА -->
    <details class="settings-accordion">
      <summary class="settings-accordion-header">
        <span>🛠️ Диагностика и сеть</span>
        <span class="accordion-arrow">▾</span>
      </summary>
      <div class="settings-accordion-body">
        <div style="margin-top:12px">
          <button class="btn-settings-action btn-full" onclick="runDebugScan()">🔍 Что видит сканер сейчас?</button>
          <div id="debug-result" class="diag-output"></div>
        </div>
        <div style="margin-top:10px">
          <button class="btn-settings-action btn-full" onclick="showNetworkLog()">🌐 Лог сети (последние 20 строк)</button>
          <button class="btn-settings-action btn-full" id="btn-reconnect" onclick="reconnectNetwork()" style="margin-top:6px">🔄 Переподключиться к серверу</button>
          <div id="network-log-result" class="diag-output"></div>
        </div>
      </div>
    </details>
  </div>
</div>

<div id="heart-burst" class="heart-burst"></div>
<script>
{script}
</script>
</body>
</html>
"""
HTML = HTML.format(
    styles=CSS,
    script=JS,
    version=APP_VERSION,
    test_tag=test_tag,
)
