# Система автоматизации подготовки курсовых и дипломных работ
PYTHON ?= python3
TOPIC ?= "Применение методов машинного обучения для автоматизированной диагностики мочекаменной болезни по данным компьютерной томографии"
OUT ?= build/demo
PORT ?= 8000

.PHONY: help install build build-online web test clean check demo

help: ## Показать справку
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

install: ## Установить зависимости
	$(PYTHON) -m pip install -r requirements.txt

build: ## Собрать работу офлайн (проверенный корпус источников)
	$(PYTHON) -m diploma generate --topic $(TOPIC) --offline --out $(OUT)

build-online: ## Собрать работу с поиском по Crossref/OpenAlex/arXiv
	$(PYTHON) -m diploma generate --topic $(TOPIC) --out $(OUT)

plan: ## Только план и структура
	$(PYTHON) -m diploma plan --topic $(TOPIC)

search: ## Только поиск и проверка источников
	$(PYTHON) -m diploma search --topic $(TOPIC) --offline

web: ## Веб-интерфейс со скачиванием (http://localhost:$(PORT))
	$(PYTHON) -m diploma web --port $(PORT)

check: ## Проверить окружение
	$(PYTHON) -m diploma check

test: ## Тесты
	$(PYTHON) -m unittest discover -s tests -v

demo: ## Демонстрационная сборка (всё включено)
	$(PYTHON) -m diploma generate --topic $(TOPIC) --offline \
		--author "Иванов И. И." --group "МО-41" --chair "Кафедра урологии" \
		--supervisor "Петров П. П." --institution "ФГБОУ ВО «Университет»" \
		--city "Худжанд" --out $(OUT)

clean: ## Удалить результаты сборок
	rm -rf build
