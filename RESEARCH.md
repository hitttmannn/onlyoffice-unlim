# Исследование и границы выводов

Дата проверки: 22.10.2026. Только первичные источники.

* Релиз v10.0.0 присутствует: https://github.com/ONLYOFFICE/DocumentServer/releases/tag/v10.0.0
* LICENSE точного тега: https://github.com/ONLYOFFICE/DocumentServer/blob/v10.0.0/LICENSE
  AGPLv3: изучены права модификации, распространение Corresponding Source,
  сетевой доступ к модифицированному исходному коду. Перед публикацией сохранить
  точные LICENSE/NOTICE каждого компонента и дополнительных условий.
* Состав релиза: https://github.com/ONLYOFFICE/DocumentServer/blob/v10.0.0/.gitmodules
  core, sdkjs, server, web-apps, шрифты, словари и плагины — отдельные репозитории.
  Нельзя использовать только архив верхнего репозитория как полный исходный код.
* https://github.com/ONLYOFFICE/server/blob/master/Common/sources/license.js
  возвращает connections и connectionsView из LICENSE_CONNECTIONS_OS.
* https://github.com/ONLYOFFICE/server/blob/master/Common/sources/constants.js
  в просмотренной master LICENSE_CONNECTIONS_OS = 0x7fffffff, а
  LICENSE_CONNECTIONS = 20. Это свидетельство о master, НЕ о gitlink 10.0.0,
  готовом пакете или фактической обработке соединений. Патч пока не нужен.
* https://github.com/ONLYOFFICE/web-apps/blob/master/build/Gruntfile.js
  существует конфигурация сборки UI; наличие полного mobile editor в релизе
  и права на все его зависимости пока не подтверждены.
* https://helpcenter.onlyoffice.com/docs/faq/docs-community.aspx
  FAQ указывает отсутствие mobile web в Community. Проверять отдельно браузерный
  мобильный редактор, режим desktop в мобильном браузере и нативное приложение.
  Нативный клиент с Nextcloud/WebDAV — возможный отдельный сценарий, требующий
  проверки сохранения, блокировок и совместного редактирования; это не гарантия
  работы мобильного web UI. Коммерческая лицензия — отдельный вариант, не включён.
* https://github.com/ONLYOFFICE/build_tools
  проверенная авторами среда: Ubuntu 24.04 amd64, 8 GB RAM, 4 GB swap, 100 GB SSD.
  Пользователь сообщил о добавлении 4 GB RAM: ожидается 8 GB RAM; swap ранее 4 GB,
  требуется проверить. nc обслуживает production: полная компиляция
  не должна запускаться без измерений. Одного jobs=1 недостаточно для гарантии.
* https://github.com/ONLYOFFICE/Docker-DocumentServer/blob/master/Dockerfile
  upstream Dockerfile скачивает deb и зависимости, включает шрифты и принятие
  EULA Microsoft fonts. Это НЕ сборка DocumentServer из исходников. Перед
  перераспространением проверить лицензии всех шрифтов/пакетов; не считать
  наличие образа в Docker Hub разрешением на любые способы распространения.

## Следующий аудит

На nc выполнить scripts/lock-source.sh. Сохранить полный SHA верхнего репозитория,
все recursive gitlinks, лицензии и NOTICE. Сопоставить их с runtime package.
Зафиксировать build_tools SHA, базу builder по digest, архивы/хеши C++/JS/Python
зависимостей и toolchain, отключить обновление веток. Проверить реальную поддержку
ограничения jobs=1 в данном build_tools, а не угадывать имя флага.
Сборка должна сохранять полный лог, SBOM, пакеты, исходники и контрольные суммы.
Повторить сборку из тех же входов и сравнить состав/артефакты.

До завершения аудита не добавлять закрытые mobile-компоненты, чужие патчи без
лицензии, license key и бинарные правки. Модификации AGPL-кода возможны по условиям
его лицензии; не смешивать это с правами на закрытые компоненты. Сохранить legal
notices и обозначения авторства. Для опубликованных бинарников обеспечить
эквивалентный доступ к соответствующим исходникам; приватный репозиторий не
должен мешать пользователям сервиса получить положенный им исходный код.
