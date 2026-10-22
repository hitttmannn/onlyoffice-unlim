# Локальная проверка 22.10.2026

PASS: bash -n для трёх shell scripts.
PASS: синтаксис Python smoke.py.
PASS: build.sh отвергает latest, плавающий тег 10.0, чужой repository и короткий digest до вызова Docker.

НЕ ВЫПОЛНЕНО: Docker build, Compose config/up, HTTP, функциональные тесты,
компиляция, backup/restore, публикация. Docker и gh не обнаружены в этой среде;
сетевые запросы из терминала не разрешают GitHub/nc. Исследование выполнено через
web-инструмент. На nc пользователь выполняет действия вручную.

Обновление по результатам ручного выполнения на nc: Docker Compose 2.26.1-4
работает; preflight прошёл. inspect-runtime.sh прошёл на pinned amd64 digest,
подтверждён пакет 10.0.0-169, image ID
82ba611d7112e642a06c900d6a6ba652f852a21db90ba6524516ed85ebdf655d.
Отдельные server JS не найдены, mobile index есть. Ни build.sh, ни staging
up/smoke пока не выполнялись. prepare-stage.py: локально проверен синтаксис
и создание закрытого env с повторным использованием JWT; Docker здесь нет.
