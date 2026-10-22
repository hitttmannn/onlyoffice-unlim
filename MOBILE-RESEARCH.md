# Мобильное редактирование: результат исследования 22.10.2026

## Что подтверждено

Проверен web-apps SHA f4f1c88937717f9b41e2f8a864b8aeffa21e3a2a,
указанный gitlink релиза DocumentServer v10.0.0. На nc реальный пакет
10.0.0-169 показывает предупреждение: mobile web в Community только для просмотра.
Это подтверждённая неудачная проверка DOCX, не предположение по документации.

В apps/documenteditor/mobile/src/lib/patch.jsx isSupportEditFeature() возвращает
false, getToolbarOptions() — null; initFonts/initEditorStyles/initFocusObjects/
initTableTemplates — заглушки. Контекстное меню не содержит действий.
Toolbar.jsx использует этот модуль для панели и undo/redo, Main.jsx — для
инициализации редактирования, шрифтов и свойств. У spreadsheeteditor и
presentationeditor isSupportEditFeature() также false.

В vendor/framework7-react/build/webpack.config.js, строки 292–296, есть
NormalModuleReplacementPlugin: он заменяет ../lib/patch на модуль из соседнего
../../../web-apps-mobile/${targetPatch}/patch.jsx при наличии файлов и выбранного
addon/development режима. Каталог web-apps-mobile не входит в проверенные
деревья DocumentServer и web-apps и не указан среди gitlinks sources.lock.json.
Это не доказывает, что ни у кого нет иной лицензированной реализации, но в
проверенном релизе соответствующего дополнения нет.

## Вывод для сборки

Пересборка тех же открытых компонентов не гарантирует mobile editing: нужны
дополнительная реализация контроллеров/UI и проверка SDK. Замена false на true
не восполняет перечисленные заглушки. Никаких таких патчей в проект не внесено.
Возможность самостоятельно реализовать недостающие функции не исключена, но
это отдельная разработка и тестирование трёх редакторов, а не параметр Docker.
Нельзя переносить закрытый addon из коммерческой поставки без соответствующих прав.

Официальные сведения согласуются с наблюдением:
https://api.onlyoffice.com/docs/docs-api/get-started/how-it-works/mobile-integration
https://www.onlyoffice.com/docs
Mobile web заявлен в коммерческих Enterprise/Developer builds. Покупка или
подключение trial здесь не выполнялись. Конкретные условия лицензии, установки
и перераспространения нужно сверять перед использованием.

## Нативный клиент как отдельный путь

Официальные приложения ONLYOFFICE Documents для Android и iOS поддерживают
редактирование и подключение Nextcloud/WebDAV:
https://helpcenter.onlyoffice.com/mobile/android/documents/overview.aspx
https://helpcenter.onlyoffice.com/mobile/ios/documents/overview.aspx
https://helpcenter.onlyoffice.com/integration/nextcloud.aspx

Важно различать два сценария. Подключение Nextcloud с серверным совместным
редактором может зависеть от возможностей Docs и его коммерческой лицензии.
WebDAV с локальным редактированием и загрузкой файла обратно — отдельный путь,
который нужно проверить на устройстве. Не обещать realtime coediting, блокировки
и отсутствие конфликтов. Из наличия поддержки Nextcloud в приложении не следует,
что серверная Community-сборка получает mobile web editors.

### Проверка на устройстве

1. Выбрать Android или iOS и записать версии ОС/приложения.
2. Работать с копиями DOCX/XLSX/PPTX в отдельной тестовой папке существующего
   Nextcloud; рабочие файлы не редактировать, сервер Docs не переключать.
3. В ONLYOFFICE Documents выбрать подключение Nextcloud либо WebDAV в зависимости
   от доступного интерфейса. Для WebDAV использовать URL из настроек Files
   самого Nextcloud, не угадывать путь. Если нужен пароль приложения, создать
   отдельный и ввести только в приложение; не присылать его в чат.
4. Изменить документ, сохранить, закрыть приложение. Через браузер Nextcloud
   скачать файл и проверить изменения. Повторить для всех трёх форматов.
5. Отдельно проверить повторное открытие и конфликт двух копий на тестовых файлах.
   Результат local/WebDAV не считать доказательством server coediting.

## Статус проекта

Desktop standalone baseline на nc прошёл open/edit/save/download, включая
пересоздание тестового контейнера. Mobile web DOCX — read only. Мобильный
нативный путь, 21+ сессий и интеграция Nextcloud с новым сервером не проверены.
Полная source compilation, публикация GHCR и переключение production не выполнены.
