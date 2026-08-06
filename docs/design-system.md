# DESIGN SYSTEM — единый стандарт для всех шаблонов

Все шаблоны должны использовать следующие классы вместо inline-стилей и старых
премиум-классов. НЕ используйте классы `stat-card`, `stat-value`, `stat-label`,
`hover-glow`, `empty-icon-wrapper`, `text-4xl text-primary` в пустых состояниях.

## CSS-компоненты (уже добавлены в static/css/style.css)

### Карточки
- `glass-panel` — основная карточка-контейнер (заголовок + содержимое)
- `glass-card` — маленькая карточка / кликабельный элемент

### Статистика — НЕ stat-card/stat-value/stat-label
Используйте единую плитку:
```
<div class="stat-tile">
  <div class="stat-tile-value [text-info|text-success|text-warning|text-danger]">ЧИСЛО</div>
  <div class="stat-tile-label">Подпись</div>
</div>
```
Сетка: `grid-4` / `grid-5` / `grid-2` (уже есть в CSS).

### Кнопки
- `.btn-primary` — основная (indigo). Без inline-градиентов/box-shadow.
- `.btn-outline` — вторичная (прозрачная, с рамкой)
- `.btn-danger` — опасная (красная прозрачная, для удаления)
- `.icon-btn` + `.icon-btn-danger` — маленькие иконочные кнопки в строках (редактировать/удалить)

### Бейджи статусов — НЕ `.badge` со inline-цветом
- `.badge-soft-primary` / `.badge-soft-success` / `.badge-soft-warning` / `.badge-soft-danger` / `.badge-soft-muted`

### Семантические цвета текста (вместо inline style="color: ...")
- `.text-success` (зелёный, выдача/активен), `.text-warning` (янтарный), `.text-danger` (красный, удаление), `.text-info` (indigo), `.text-muted`

### Фильтры-чипы (вместо glass-card в качестве фильтра)
```
<a href="..." class="filter-chip {% if активен %}active{% endif %}">Метка</a>
```

### Пустое состояние — единое
```
<div class="empty-state">
  <div class="empty-icon"><i class="fas fa-*"></i></div>
  <h4>Заголовок</h4>
  <p>Текст</p>
</div>
```

### Таблица — НЕ inline стили на th/td
```
<table class="data-table">
  <thead><tr><th>...</th></tr></thead>
  <tbody><tr><td>...</td></tr></tbody>
</table>
```
Внутри `.table-responsive-wrap`.

### Строка списка
```
<div class="list-row">
  <div class="list-row-avatar">ИН</div>
  <div class="list-row-main">
    <div class="list-row-title">Имя</div>
    <div class="list-row-sub">подпись</div>
  </div>
  <div class="row-actions">
    <a class="icon-btn" href="..."><i class="fas fa-edit"></i></a>
    <a class="icon-btn icon-btn-danger" href="..."><i class="fas fa-trash"></i></a>
  </div>
</div>
```

### Заголовок страницы с действиями
```
<div class="page-header">
  <h1 class="page-title">Заголовок</h1>
  <div class="page-actions"><a class="btn-primary">...</a></div>
</div>
```

### Панель действий
```
<div class="action-bar">
  <a class="filter-chip">...</a>
  <span class="flex-1"></span>
  <a class="btn-primary">...</a>
</div>
```

### Заголовок секции внутри карточки
```
<div class="card-header">
  <h3 class="card-title"><i class="fas fa-*"></i> Заголовок</h3>
  <a class="...">Ссылка</a>
</div>
```

## Запрещено
- `linear-gradient(...)` в inline-стилях и CSS для фона
- `box-shadow` с glow/свечением (0 0 20px и т.п.)
- inline `style="color: #...hex"` — заменить на text-success/warning/danger/info/muted
- старые классы: stat-card, stat-value, stat-label, hover-glow, empty-icon-wrapper, text-4xl text-primary (в пустых состояниях)
- эмодзи в интерфейсе (использовать Font Awesome <i class="fas ...">)

## Правила безопасности при правке
1. НЕ менять Django-теги, контекстные переменные, url-шаблоны, JS-логику.
2. Сохранять переводы `{% trans "..." %}` и `{% blocktrans %}`.
3. Файлы писать через инструмент записи (UTF-8), НЕ через PowerShell Set-Content.
4. После правки страница должна рендериться без ошибок.
