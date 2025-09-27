# TDMS Analytics API

API d'analyse pour données de capteurs TDMS utilisant ClickHouse pour le stockage et FastAPI pour l'interface REST.

## Fonctionnalités

- 🚀 **Ingestion rapide** : Traitement optimisé de fichiers TDMS volumineux (10M+ points)
- 📊 **Downsampling intelligent** : Algorithmes LTTB, uniforme et ClickHouse
- 🔍 **Fenêtrage avancé** : Requêtes par temps absolu, relatif ou index
- 💾 **Stockage colonnaire** : ClickHouse pour performance maximale
- 📈 **Pagination optimisée** : Navigation efficace dans de gros datasets

## Installation

### Prérequis

- Python 3.11+
- Poetry
- Docker et Docker Compose (pour ClickHouse)

### Configuration du projet

```bash
# Cloner et configurer
git clone <repository>
cd tdms-analytics-api

# Installer les dépendances
poetry install
poetry install --extras fast  # Pour lttbc (optionnel mais recommandé)

# Configuration
cp .env.example .env
# Éditer .env selon vos besoins
```

### Démarrage de ClickHouse

```bash
# Démarrer ClickHouse avec Docker
docker-compose up -d clickhouse

# Attendre que ClickHouse soit prêt
docker-compose logs -f clickhouse
```

### Initialisation de la base de données

```bash
# Initialiser le schéma ClickHouse
poetry run python src/tdms_analytics_api/scripts/init_db.py
```

### Démarrage de l'API

```bash
# Mode développement
poetry run python src/tdms_analytics_api/main.py

# Ou avec uvicorn directement
poetry run uvicorn tdms_analytics_api.main:app --reload --host 0.0.0.0 --port 8000
```

L'API sera disponible sur http://localhost:8000

## Documentation API

- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc
- **OpenAPI JSON** : http://localhost:8000/openapi.json

## Endpoints principaux

### Ingestion
- `POST /ingest` - Ingérer un fichier TDMS
- `GET /api/constraints` - Obtenir les contraintes de l'API

### Datasets
- `GET /datasets` - Lister tous les datasets
- `GET /dataset_meta?dataset_id=<uuid>` - Métadonnées d'un dataset
- `DELETE /datasets/{dataset_id}` - Supprimer un dataset

### Canaux
- `GET /datasets/{dataset_id}/channels` - Lister les canaux d'un dataset
- `GET /channels/{channel_id}/time_range` - Plage temporelle d'un canal

### Données fenêtrées
- `GET /window` - Fenêtre de données avec downsampling
- `GET /get_window_filtered` - Fenêtre filtrée avec pagination

## Test avec des fichiers TDMS

Créer un fichier TDMS de test :

```python
from nptdms import TdmsWriter, ChannelObject
import numpy as np
import datetime as dt

N = 10_000_000   # 10M points
FS = 10_000      # 10 kHz

t = np.arange(N, dtype=np.float64) / FS
sig1 = np.sin(2*np.pi*50*t).astype(np.float32)
sig2 = (np.sin(2*np.pi*120*t) + 0.2*np.random.randn(N)).astype(np.float32)
sig3 = (np.sign(np.sin(2*np.pi*5*t)) * 0.5).astype(np.float32)

start = dt.datetime(2024, 1, 1, 0, 0, 0)

def props(unit="V"):
    return {
        "NI_UnitDescription": unit,
        "wf_start_time": start,
        "wf_increment": 1.0 / FS,
        "wf_samples": N,
    }

with TdmsWriter("big_sample.tdms") as w:
    ch1 = ChannelObject("GroupA", "Sine50Hz", sig1, properties=props())
    ch2 = ChannelObject("GroupA", "Sine120HzNoise", sig2, properties=props())
    ch3 = ChannelObject("GroupA", "Square5Hz", sig3, properties=props())
    w.write_segment([ch1, ch2, ch3])
```

Puis ingérer le fichier via l'API :

```bash
curl -X POST "http://localhost:8000/ingest" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@big_sample.tdms"
```

## Architecture

```
src/tdms_analytics_api/
├── main.py              # Application FastAPI principale
├── config.py            # Configuration
├── dependencies/        # Dépendances FastAPI (DB, auth)
├── entities/           # Modèles Pydantic
├── enums/              # Énumérations
├── exceptions/         # Exceptions personnalisées
├── repos/              # Couche repository (si nécessaire)
├── routes/             # Endpoints FastAPI
├── services/           # Logique métier
├── scripts/            # Scripts (init DB, migrations)
└── utils/              # Utilitaires (LTTB, temps, etc.)
```

## Performance

L'API est optimisée pour :

- **Ingestion rapide** : Traitement par chunks, insertion en batch
- **Queries efficaces** : Index ClickHouse optimaux, requêtes parallèles
- **Downsampling intelligent** : LTTB pour préserver les caractéristiques des signaux
- **Mémoire réduite** : Streaming des données, pas de chargement complet

## Développement

### Tests

```bash
poetry run pytest
```

### Linting

```bash
poetry run black src/
poetry run isort src/
poetry run flake8 src/
poetry run mypy src/
```

### Pre-commit hooks

```bash
poetry run pre-commit install
poetry run pre-commit run --all-files
```

## Production

Pour un déploiement en production :

1. Utiliser un ClickHouse dédié (cluster recommandé)
2. Configurer un reverse proxy (nginx)
3. Utiliser un gestionnaire de processus (systemd, supervisor)
4. Monitoring et logs (Prometheus, Grafana)
5. Sauvegardes régulières

## Troubleshooting

### ClickHouse ne démarre pas
```bash
# Vérifier les logs
docker-compose logs clickhouse

# Nettoyer et redémarrer
docker-compose down -v
docker-compose up -d clickhouse
```

### Erreurs d'ingestion
- Vérifier la taille du fichier (MAX_FILE_SIZE)
- Contrôler l'espace disque ClickHouse
- Surveiller les logs de l'API

### Performance lente
- Augmenter BATCH_INSERT_SIZE
- Activer lttbc (ENABLE_LTTBC=true)
- Optimiser les index ClickHouse