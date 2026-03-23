# saas-shadow

**Self-host your own project management stack from a single config file.**

Kanban board, task tracker, and wiki -- all in one Flask app with SQLite storage, dark/light themes, drag-and-drop, and optional AI task breakdown. Zero external dependencies beyond Python.

## Quickstart

```bash
git clone https://github.com/youruser/saas-shadow && cd saas-shadow
pip install -r requirements.txt
python app.py
# Open http://localhost:5678
```

## Features

- **Kanban Board** -- Drag-and-drop cards across columns (Todo, In Progress, Review, Done)
- **Task Tracker** -- Create tasks with assignee, due date, priority, status, and tags. Filter and sort.
- **Wiki** -- Create and edit pages in Markdown with live preview and page tree navigation
- **AI Breakdown** -- Paste a project description, get a structured task list with estimates (OpenAI)
- **Dark/Light Theme** -- Toggle with persistence
- **Single Config** -- Enable/disable modules, set theme, configure database path in `config.yaml`
- **SQLite Storage** -- Zero setup, everything in one file
- **Change History** -- Every create/update/delete is logged

## Configuration

Edit `config.yaml`:

```yaml
project:
  name: "My Project"
modules:
  kanban: true
  tasks: true
  wiki: true
theme:
  default: "dark"
  accent: "#58a6ff"
ai:
  enabled: true
database:
  path: "./my_project.db"
server:
  port: 5678
```

## API Endpoints

### Kanban
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/board` | Get board with all cards |
| POST | `/api/cards` | Create card |
| PUT | `/api/cards/:id` | Update card |
| POST | `/api/cards/:id/move` | Move card to column |
| DELETE | `/api/cards/:id` | Delete card |

### Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tasks` | List tasks (filter by status, priority, assignee) |
| POST | `/api/tasks` | Create task |
| PUT | `/api/tasks/:id` | Update task |
| DELETE | `/api/tasks/:id` | Delete task |

### Wiki
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/wiki` | List pages |
| GET | `/api/wiki/:slug` | Get page |
| POST | `/api/wiki` | Create page |
| PUT | `/api/wiki/:slug` | Update page |
| DELETE | `/api/wiki/:slug` | Delete page |
| GET | `/api/wiki/search?q=...` | Search pages |

### AI
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ai/breakdown` | Break description into tasks |
| POST | `/api/ai/suggest` | Suggest next steps for a task |

## Architecture

```
config.yaml --> app.py (Flask)
                  |-- modules/kanban.py   (Kanban board CRUD)
                  |-- modules/tasks.py    (Task tracker CRUD)
                  |-- modules/wiki.py     (Wiki Markdown pages)
                  |-- modules/ai_assist.py (AI task breakdown)
                  |-- storage.py          (SQLite backend)
                  |-- templates/          (Jinja2 + vanilla JS)
                  |-- static/             (CSS + JS)
```

## License

MIT
