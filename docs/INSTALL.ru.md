# Установка на свой сервер Nextcloud

[English](INSTALL.en.md) · [Обзор проекта](../README.ru.md)

В этой инструкции используются ваши адреса и пути. Старые `nc-mobile-install.py`
и скрипты удаления относятся к одному историческому серверу; запускать их на
другой установке нельзя.

## 1. Требования и резервное копирование

- Работающий Nextcloud **35**, включённый коннектор ONLYOFFICE **10.2.1** с
  настроенным JWT. Сначала настройте и проверьте штатный коннектор.
- ONLYOFFICE Docs **10.0.0-169**. Другие версии Docs не проверены; переносимый
  установщик проверяет версии Nextcloud/коннектора, но не пакет удалённого Docs.
- HTTPS для публичных Nextcloud и Docs, сертификаты, которым доверяют браузер и
  сервер. Docs должен скачивать файлы и обращаться к callback Nextcloud;
  Nextcloud должен обращаться к Docs. Прокси должен пропускать WebSocket.
- Root на хосте, Git и Python 3. Docker и Compose v2 при использовании нашего
  Compose для Docs. Обновление UI также использует PHP CLI хоста для проверки синтаксиса.
- Доступный на хосте записываемый каталог приложений Nextcloud и числовые UID/GID
  его рабочего пользователя. `custom_apps` должен быть зарегистрирован как
  записываемый в `apps_paths`. Для неизменяемых/управляемых установок без такого
  каталога нужна отдельная интеграция упаковки; этот установщик её не выполняет.

Необязательный Compose Docs задаёт лимит памяти 2 ГиБ, памяти+swap 3 ГиБ и одно
ядро. Это изменяемые начальные значения, а не гарантия достаточных ресурсов.
Оставьте память для Nextcloud/других сервисов, место для образа, данных и копий.
Закреплённый образ — **Linux amd64**; выбор образа/исходников ARM не подготовлен.

До изменения работающей системы создайте согласованную резервную копию БД
Nextcloud, `config`, собственных приложений и пользовательских файлов и проверьте
способ восстановления. Сохраните также конфигурацию, ссылку на образ и тома
старого Docs. Сохранение Docker-образа само по себе не копирует данные.
Старый контейнер Docs и его тома не удаляйте.

## 2. Клонирование и настройки

На хосте, которому доступны каталоги приложения и плагина:

```sh
git clone https://github.com/hitttmannn/onlyoffice-unlim.git
cd onlyoffice-unlim
install -d -m 700 private
cp deployment/mobile.example.json private/mobile.json
chmod 600 private/mobile.json
```

Откройте `private/mobile.json` в редакторе и замените **все значения примера**:

| Поле | Значение |
| --- | --- |
| `nextcloud_url` | Публичный HTTPS-адрес, включая `/nextcloud` при установке в подкаталог. Для сообщений плагина используется только origin. |
| `docs_url` | Публичный HTTPS-адрес Docs, включая подкаталог прокси, если он используется. |
| `docs_internal_url` | Адрес Docs, доступный PHP Nextcloud, для команд принудительного сохранения. |
| `app_dir` | Путь на хосте внутри зарегистрированного записываемого каталога приложений, заканчивающийся на `onlyoffice_mobile`. Не должен существовать. |
| `plugin_dir` | Новый абсолютный каталог на хосте для сгенерированного плагина. Не должен существовать. |
| `occ_command` | JSON-массив аргументов, не строка shell. Запускает `occ` от рабочего пользователя Nextcloud. |
| `owner_uid`, `owner_gid` | Числовой владелец файлов приложения на хосте. По умолчанию 33/33; проверьте свою систему. |
| `allowed_users` | Точные UID Nextcloud, например `["alice", "bob"]`. Администраторы допущены автоматически. |

Пример обычной установки:

```json
"occ_command": ["sudo", "-u", "www-data", "php", "/var/www/nextcloud/occ"]
```

Пример контейнерного Nextcloud — замените имя контейнера и UID:

```json
"occ_command": ["docker", "exec", "-u", "33", "nextcloud", "php", "/var/www/html/occ"]
```

Для контейнера `app_dir` указывает **сторону хоста** постоянного bind mount
приложений, например `/srv/nextcloud/custom_apps/onlyoffice_mobile`. Этот mount
должен соответствовать `apps_paths` внутри контейнера. Путь внутри контейнера
не становится путём хоста автоматически. Для rootless Docker/user namespaces
проверьте отображение UID/GID; нельзя автоматически считать их равными 33/33.
Имя вроде `docs` доступно только в общей Docker-сети. `127.0.0.1` для PHP
в контейнере означает сам контейнер Nextcloud.

```sh
python3 scripts/install-mobile-app.py check-config --config private/mobile.json
sudo python3 scripts/install-mobile-app.py render-plugin --config private/mobile.json
```

`check-config` проверяет только синтаксис, не сервисы. `render-plugin` создаёт
плагин под origin вашего Nextcloud и отказывается перезаписывать каталог.
Не размещайте результат внутри закрытого каталога, недоступного процессам Docs.

## 3. Подключение плагина к Docs

### Работающий Docs — предпочтительно, если уже настроен

Используйте тот же экземпляр и адреса Docs проверенной версии, что и штатный
коннектор. Добавьте **постоянное read-only монтирование** в его конфигурацию:

```yaml
volumes:
  - /opt/onlyoffice-unlim/mobile-panel:/var/www/onlyoffice/documentserver/sdkjs-plugins/mobile-panel:ro
```

Источник замените на свой `plugin_dir`. Сохраните все остальные mount, JWT,
сети и порты. Пересоздайте только сервис Docs его существующим Compose/оркестратором
в согласованное время простоя. `docker cp` в работающий контейнер не обеспечивает
сохранность плагина при пересоздании.

### Необязательный отдельный Docs

Создайте `private/docs.env` с правами 600 в текстовом редакторе. JWT-секрет и
заголовок должны быть **теми же, что в настроенном коннекторе Nextcloud**.
Не отправляйте секрет в чат и не добавляйте в Git. Пример ключей — секрет замените:

```dotenv
JWT_SECRET='replace-with-the-existing-connector-secret'
JWT_HEADER=Authorization
MOBILE_PLUGIN_DIR=/opt/onlyoffice-unlim/mobile-panel
DOCS_BIND_IP=127.0.0.1
DOCS_PORT=18082
DOCS_MEMORY=2g
DOCS_MEMORY_SWAP=3g
DOCS_CPUS=1.0
```

```sh
chmod 600 private/docs.env
sudo docker compose -f deployment/compose.mobile.yaml --env-file private/docs.env config --quiet
sudo docker compose -f deployment/compose.mobile.yaml --env-file private/docs.env up -d
```

При следующих вызовах Compose используйте те же `-f` и `--env-file`.
Новый сервис имеет отдельные именованные тома. Скрипт не переключает на него
штатный коннектор: `docs_url/docs_internal_url` использует только наша панель.
Для автоматического мобильного открытия штатный коннектор уже должен работать;
компьютеры продолжают использовать его настроенный Docs. Миграция настольного
редактора — отдельная задача.

## 4. Настройка HTTPS-прокси

Например, выделите для Docs `https://docs.example.com/`. Прокси на том же хосте
направляет запросы на `127.0.0.1:18082`. Для других хостов/контейнеров используйте
доступный защищённый адрес; не открывайте напрямую сырой HTTP-сервис в Интернет.

**Nginx**, внутри существующего TLS `server` для домена Docs:

```nginx
location / {
    proxy_pass http://127.0.0.1:18082;
    proxy_http_version 1.1;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Host $http_host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;
}
```

**Apache**, внутри существующего TLS VirtualHost Docs, с модулями `proxy`,
`proxy_http`, `headers` и версией с поддержкой `upgrade=websocket`:

```apache
ProxyPreserveHost On
ProxyPass "/" "http://127.0.0.1:18082/" upgrade=websocket timeout=3600
ProxyPassReverse "/" "http://127.0.0.1:18082/"
RequestHeader set X-Forwarded-Proto "https"
```

Это фрагменты проксирования, а не полные настройки TLS/DNS/файрвола.
Проверяйте конфигурацию перед reload. Проксирование подкаталога требует
дополнительной обработки путей/forwarded-host; старый файл nc — пример только
для того хоста. Не отключайте проверку TLS или все проверки SSRF ради исправления сети.

Проверьте относительно **своего** публичного адреса Docs:

- `/healthcheck` возвращает `true`.
- `/web-apps/apps/api/documents/api.js` — JavaScript, а не HTML страницы входа/welcome.
- `/sdkjs-plugins/mobile-panel/config.json` — конфигурация созданного плагина.
- `/sdkjs-plugins/mobile-panel/bridge.html` и `bridge.js` загружаются.

## 5. Установка приложения и проверка

```sh
sudo python3 scripts/install-mobile-app.py install-app --config private/mobile.json
```

Скрипт проверяет состояние Nextcloud/коннектора, копирует только наше приложение,
записывает четыре его настройки и включает его. Прокси, JWT и адреса штатного
коннектора не меняются, Docs не останавливается, общий `occ upgrade` не запускается.
Существующий каталог приложения не перезаписывается. При ошибке после копирования
проверьте сообщение, журналы и каталог; не удаляйте его вслепую.

Откройте `<nextcloud_url>/index.php/apps/onlyoffice_mobile/`. Положите **копии**
DOCX/XLSX в корень личных «Файлов», проверьте изменение/сохранение, закройте,
откройте заново и скачайте. Проверьте книгу с несколькими листами, масштаб и
реальный телефон/Android-клиент. В новом WebView Android ожидаем отдельный вход.
Проверьте отказ пользователям без допуска. Автоматическое направление касается
только доступных редактируемых DOCX/XLSX на телефоне, не публичных ссылок,
других форматов и компьютеров. Ограничения штатного коннектора продолжают действовать.

Интерфейс сейчас на русском; инструкции доступны на двух языках.

## 6. Обновление, отключение и откат

Для изменений UI установленной версии 0.2.0:

```sh
git pull --ff-only
sudo python3 scripts/update-mobile-panel.py --ui-only --config private/mobile.json
```

Три старых UI-файла сохраняются в `private/mobile-ui-before-*`. Обновите страницу.
Версия приложения не меняется, общий `occ upgrade` не запускается. Для отката
верните эти файлы по соответствующим путям в `app_dir` с исходным владельцем и
правами чтения. Для обновления кода/версии изучите изменения, сохраните приложение
и настройки, следуйте инструкции конкретной миграции; `--ui-only` не заменяет
полное обновление приложения.

После **своего префикса `occ_command`** используйте одну из команд:

```text
config:app:set onlyoffice_mobile mobile_default --value=no
app:disable onlyoffice_mobile
```

Первая отключает автоматическое направление на телефонах, вторая — приложение
целиком. Переносимая установка не меняет штатный коннектор, поэтому отключение
возвращает его обычное поведение. Сохраняйте копии и старый Docs. Для отката не
используйте `docker compose down -v`, `docker rm -v` и очистку томов.
Аварийное восстановление БД/файлов зависит от ваших проверенных копий Nextcloud.

## Локальные проверки разработки

Из корня репозитория:

```sh
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/install-mobile-app.py scripts/update-mobile-panel.py
```

`tests/sheet-picker.cjs` использует Playwright и локальный Chromium/Brave;
при необходимости задайте `PLAYWRIGHT_MODULE`/`BROWSER_PATH`.
`tests/mobile-zoom-routing.cjs` требует конкретный одноразовый стенд на
`127.0.0.1:18782`, пользователя `localadmin` и `mobile-test.xlsx`; пароль берётся
из `NC_TEST_ENV`. Это не проверка для запуска на production и не доказательство
совместимости с каждым Android-клиентом.
