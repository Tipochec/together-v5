; ============================================================================
; Together — установщик (Inno Setup)
; ============================================================================
; Зачем это вообще нужно (а не просто раздавать голый .exe):
;
; Правило Windows Firewall может добавить только процесс с правами
; администратора — это ограничение самой ОС, обойти его нельзя. Раньше
; program.exe пытался добавить правило САМ при каждом отдельном запуске —
; отсюда UAC-запрос (а то и два — свой плюс родное окно Windows) каждый раз,
; когда кто-то новый запускал .exe.
;
; Установщик просит права ОДИН раз при установке (это ожидаемо и привычно —
; так делает почти любая программа с иконкой в Program Files) и внутри уже
; сам, без лишних вопросов, добавляет то же самое правило брандмауэра.
; После этого core/firewall.py при обычном запуске приложения увидит, что
; правило с именем RULE_NAME уже существует, и просто ничего не будет делать —
; ни одного дополнительного окна пользователь больше не увидит.
;
; ВАЖНО: имя правила ("Together (app)") и порт (39721) здесь захардкожены и
; должны СОВПАДАТЬ с RULE_NAME/PORT в core/firewall.py — если поменяешь одно,
; поменяй и второе, иначе получится дубликат правила (не критично, но лишнее).
; ============================================================================

#define MyAppName "Together"
#define MyAppVersion "1.0"
#define MyAppExeName "Together.exe"
#define MyFirewallRuleName "Together (app)"
#define MyFirewallPort "39721"

[Setup]
AppId={{8F6C9C6E-2B7B-4B9E-9C7A-8A2A1A9B5C11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=TogetherSetup
Compression=lzma
SolidCompression=yes
; Установка в Program Files + добавление правила брандмауэра — оба действия
; требуют администратора, поэтому просим права сразу на весь установщик.
; Это тот самый ЕДИНСТВЕННЫЙ запрос прав, который увидит пользователь.
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать значок на рабочем столе"; GroupDescription: "Дополнительные значки:"

[Files]
; Собранный PyInstaller-ом однофайловый exe (main.spec — onefile-сборка,
; отдельная папка dist не нужна, только сам .exe).
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Удалить {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; Автозапуск НЕ прописывается здесь: core/autostart.py сам включает его
; один раз при самом первом запуске приложения (setup_autostart_once(),
; вызывается из main.py) — это стандартное поведение по умолчанию, не то,
; что должно спрашиваться отдельной галочкой при установке. Отключить
; при желании можно тумблером в самих настройках программы.

[Run]
; Правило брандмауэра — та самая часть, ради которой всё это затевалось.
; runhidden: без мелькающего окна консоли. Флаг profile=any покрывает
; частные, публичные и доменные сети одним правилом — не нужно, чтобы
; пользователь сам догадывался ставить галочку "общественные сети" в
; отдельном диалоге Windows.
Filename: "{sys}\netsh.exe"; \
    Parameters: "advfirewall firewall add rule name=""{#MyFirewallRuleName}"" dir=in action=allow program=""{app}\{#MyAppExeName}"" protocol=TCP localport={#MyFirewallPort} profile=any enable=yes"; \
    Flags: runhidden; StatusMsg: "Настройка брандмауэра..."

Filename: "{app}\{#MyAppExeName}"; Description: "Запустить {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Чистим за собой правило при удалении программы — иначе оно бесполезно
; провисит в списке правил брандмауэра навсегда, указывая на уже
; несуществующий файл.
Filename: "{sys}\netsh.exe"; \
    Parameters: "advfirewall firewall delete rule name=""{#MyFirewallRuleName}"""; \
    Flags: runhidden
