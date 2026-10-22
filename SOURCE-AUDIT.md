# Аудит точного релиза 10.0.0 — 22.10.2026

Проверены реальные checkout server и web-apps, закреплённые gitlinks родительского
DocumentServer v10.0.0, а не master. SHA сохранены в sources.lock.json.

## Соединения

server/Common/sources/constants.js: LICENSE_CONNECTIONS_OS = 0x7fffffff.
server/Common/sources/license.js: readLicense возвращает это значение для
connections и connectionsView, usersCount/usersViewCount = 0.
server/DocService/sources/DocsCoServer.js: ветка проверки соединений сравнивает
счётчики с licenseInfo.connections/connectionsView.

Следствие: в этой открытой реализации порог не 20, а 2147483647. Патч этой
константы не требуется. LICENSE_CONNECTIONS = 20 тоже присутствует — нельзя
заменять все вхождения 20 без анализа. Исполняемый пакет может отличаться от
исходников; реальная поддержка 21+ сессии и ресурсов пока не проверена.

## Мобильный интерфейс

В web-apps есть mobile/src, React-компоненты и задачи deploy-app-mobile.
Но apps/documenteditor/mobile/src/lib/patch.jsx содержит заглушки:
isSupportEditFeature возвращает false, getToolbarOptions возвращает null,
initFonts/initEditorStyles/initFocusObjects/initTableTemplates не реализованы,
context menu возвращает пустой список. Аналогичные проверки false есть для
spreadsheeteditor и presentationeditor.

Следствие: наличие mobile UI не означает готового мобильного редактирования.
Замена false на true не восстанавливает отсутствующие обработчики и UI.
Нужно отдельно проверить полноту SDK и остальных исходников. Если нужных частей
нет под доступной лицензией, варианты: собственная реализация из открытых
компонентов, отдельный нативный клиент с проверкой Nextcloud или коммерческая
лицензия. Ни один из этих вариантов пока не выбран и не проверен.

## Лицензии

Заголовок mobile patch.jsx явно указывает AGPL-3.0-only и дополнительные условия
LICENSE. web-apps/LICENSE содержит требования сохранения уведомлений, отметок
модификаций, legal notices и CC BY-SA 4.0 для non-code content.
У vendor/framework7-react/package.json поле license = UNLICENSED, private = true:
это метаданные сборочного workspace, однако их расхождение с лицензией репозитория
нужно разобрать по конкретным файлам и зависимостям, а не считать все bundled
компоненты автоматически AGPL. Сторонние npm licenses и шрифты ещё не проверены.

Источники: https://github.com/ONLYOFFICE/DocumentServer/tree/v10.0.0
https://github.com/ONLYOFFICE/server/tree/3e71b09caf66c4ac0d43106ea4922f6ddfa76043
https://github.com/ONLYOFFICE/web-apps/tree/f4f1c88937717f9b41e2f8a864b8aeffa21e3a2a

## Статус

Полная компиляция не начата. Образ не опубликован. Смена production не разрешена.
На nc пользователь сообщил установку Compose; полный повторный вывод проверки
пока не получен. Последние измерения nc: RAM 8192 MiB, MemAvailable 6871 MiB,
swap 4096 MiB (не занят), свободный диск 43 GiB. Docker 26.1.5+dfsg1, Debian 13.
Production: ghcr.io/thomisus/onlyoffice-documentserver-unlimited:9.2.1.
