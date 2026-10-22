# Локальная проверка 22.10.2026

PASS: bash -n для трёх shell scripts.
PASS: синтаксис Python smoke.py.
PASS: build.sh отвергает latest, плавающий тег 10.0, чужой repository и короткий digest до вызова Docker.

НЕ ВЫПОЛНЕНО: Docker build, Compose config/up, HTTP, функциональные тесты,
компиляция, backup/restore, публикация. Docker и gh не обнаружены в этой среде;
сетевые запросы из терминала не разрешают GitHub/nc. Исследование выполнено через
web-инструмент. На nc пользователь выполняет действия вручную.
