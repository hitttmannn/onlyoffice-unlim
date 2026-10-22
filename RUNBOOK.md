# Ручное выполнение на nc

## 1. Снять состояние без изменений

Скопировать этот каталог на nc. Проверить scripts/preflight.sh и выполнить
`bash scripts/preflight.sh`. Если проверка ресурсов не проходит — остановиться.
После добавления памяти ожидается 8 GB RAM (проверить), swap — проверить отдельно.
Заявленные 8 GB RAM не означают, что свободно место для второго Docs. Не останавливать
production ради теста и не снижать его лимиты. Если свободных ресурсов нет,
нужны временные дополнительные ресурсы или отдельное согласованное окно.

Зафиксировать ОС/архитектуру, Docker/Compose, имя production контейнера, digest
образа, расположение Compose, volumes/binds, PostgreSQL/Redis/RabbitMQ,
reverse proxy, версию Nextcloud и ONLYOFFICE connector. Не присылать полный
`docker inspect`, `.env`, `occ config:list` или Compose config в чат: там секреты.

### Docker Compose на Debian 13

В Debian 13 пакет называется `docker-compose` (версия 2.x); не требуется
переводить рабочий Docker на другой репозиторий. Сначала проверить план:

```sh
apt-get update
apt-get -s install --no-install-recommends --no-upgrade docker-compose
```

Если план добавляет только Compose без удаления/обновления Docker, containerd,
runc и других компонентов рабочего сервера, установить:

```sh
apt-get install --no-install-recommends --no-upgrade docker-compose
docker compose version
```

Если план затрагивает рабочие компоненты — остановиться и изучить его.
Если доступен только вызов `docker-compose`, использовать его вместо
`docker compose` в дальнейших командах; требуется версия 2.x.

## 2. Зафиксировать источники и выбрать путь

`bash scripts/lock-source.sh` получает только исходники, не меняет production.
Исходные SHA/лицензии нужно изучить до выбора сборки. Сетевой доступ к GitHub нужен.
Для полного source build выполнить аудит из RESEARCH.md; готового проверенного
рецепта полного source build в этом комплекте нет.

Облегчённый путь — runtime из проверенного официального 10.0 образа. Проверить
наличие тега, платформу, дату, пакет и лицензию, затем определить digest:
`docker buildx imagetools inspect onlyoffice/documentserver:10.0`.
Тег 10.0 здесь лишь кандидат: не использовать его вместо digest. Если отсутствует,
не подменять latest или 9.x. Не скачивать платный пакет под видом Community.

## 3. Собрать runtime wrapper на nc

Скопировать example.env в private.env, заполнить digest и новый случайный JWT,
`chmod 600 private.env`. Не коммитить файл. Экспортировать BASE_IMAGE,
SOURCE_URL и CANDIDATE_IMAGE из проверенных значений вручную. Затем:

```sh
bash scripts/build.sh
bash scripts/preflight.sh
docker compose --env-file private.env up -d
python3 scripts/smoke.py
```

Build только упаковывает неизменённый upstream runtime. Не запускает компиляцию
и не снимает ограничения. Docker/сеть/образ в среде автора не доступны: команды
ещё не проверены на nc. Ожидать прогрева healthcheck несколько минут; при OOM
остановить только staging. Порог 1536 MiB ограничивает ущерб, но может оказаться
недостаточным для Docs; не повышать его за счёт production без измерений.

Не подключать staging к production томам/БД и не менять ONLYOFFICE URL в рабочем
Nextcloud. Для UI по SSH можно пробросить localhost:18080; для реальной интеграции
нужен отдельный тестовый Nextcloud, изолированная сеть и доступные в обе стороны
HTTPS URL с доверенными сертификатами. Не отключать TLS/JWT/SSRF-проверки целиком.

## 4. Проверить и опубликовать

Выполнить ACCEPTANCE.md, сохранить результаты без секретов. Только затем после
согласования видимости и прав создать hitttmannn/onlyoffice-unlim.
Публикация исходников: минимально Contents write в выбранный репозиторий;
создание репозитория требует отдельного права учётной записи. GHCR требует
отдельной аутентификации и packages:write (и доступа к соответствующему namespace).
GitHub connector не является автоматически логином Docker в GHCR.
Предпочитать временный минимальный credential, вход через --password-stdin;
не помещать токены в Dockerfile/Compose/логи или чат.

После разрешения публикации установить реальный тег, например 10.0.0-nc.1,
выполнить docker tag и docker push в ghcr.io/hitttmannn/onlyoffice-unlim.
Сохранить digest опубликованного образа, проверить pull в чистой среде и
доступность соответствующих исходников. Видимость GHCR проверить отдельно:
публичный GitHub-репозиторий не гарантирует публичный package.
Не включать автоматический publish workflow до согласования прав.

## 5. Переключение

Только после успешных приёмочных тестов, проверенного восстановления backup и
явного подтверждения пользователя. См. BACKUP-ROLLBACK.md.

## Проверка закреплённого кандидата на nc

После probe-upstream.sh найден linux/amd64 manifest; он записан в
runtime-candidate.json. Выполнить `bash scripts/inspect-runtime.sh`. Скрипт
скачивает образ и запускает только /bin/sh для чтения dpkg и файлов; штатный
entrypoint и сервисы Docs не запускаются, портов и томов нет. Проверяет 12 GiB
свободного места в проекте (если Docker хранит данные на другой ФС, проверить
её свободное место отдельно). Вывод сохраняется в artifacts/runtime-audit.txt.
Наличие mobile/index.html не доказывает возможность редактирования. Отсутствие
отдельных JS-файлов может означать упаковку в бинарник, а не отсутствие лимита.
До изучения результата не выполнять build.sh и compose up.

## Локальная baseline-сборка после проверки пакета

На nc подтверждены digest из runtime-candidate.json, amd64 и пакет
onlyoffice-documentserver 10.0.0-169. Отдельных server JS-файлов в runtime
по ожидаемым путям не обнаружено. Mobile index присутствуют, функциональность
редактирования не доказана. Нужна базовая проверка неизменённого upstream.

```sh
python3 scripts/prepare-stage.py
```

Команда проверяет ресурсы, создаёт private.env с новым случайным JWT (0600,
игнорируется Git), собирает onlyoffice-unlim:10.0.0-169-baseline по digest и
проверяет Compose без вывода секрета. Не является компиляцией DocumentServer
из исходников, не меняет лимиты или мобильный UI, не публикует образ. Если
Docker требует Buildx и его нет — сохранить ошибку; не переустанавливать Docker.

После успешной подготовки:

```sh
docker compose --env-file private.env up -d --no-build docs
docker compose --env-file private.env ps
```

Ожидать прогрева несколько минут, затем выполнить `python3 scripts/smoke.py`.
Это проверка HTTP, не сохранения документов. Если проверка не проходит,
сначала получить состояние:

```sh
docker compose --env-file private.env ps
docker compose --env-file private.env ps -q docs | xargs -r docker inspect --format '{{.Name}} status={{.State.Status}} oom={{.State.OOMKilled}} restarts={{.RestartCount}}'
free -m
df -h .
```

При OOM или ухудшении production остановить только тестовый сервис:
`docker compose --env-file private.env stop docs`. Не использовать down -v, prune
и команды для onlyoffice-document-server. Сырые логи перед отправкой проверить
на JWT, URL с токенами, персональные сведения; полный inspect/env не присылать.
