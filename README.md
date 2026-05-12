# Topsus Backend

Backend FastAPI untuk [Aplikasi Akademik Topsus](https://github.com/DewaYoGamer/topsus_frontend).

Stack:
- FastAPI + SQLAlchemy 2
- MySQL (persistence)
- Redis (caching + JWT blacklist + rate limiting)
- JWT (HS256)

## Fitur

- **Auth** — Login JWT untuk 3 role: admin, dosen, mahasiswa
- **Role-based access** — dienforce di level endpoint (`require_admin`/`require_dosen`/`require_mahasiswa`)
- **Caching** — `GET /dosen` & `GET /mahasiswa` di-cache di Redis (TTL 60s), invalidated saat CUD
- **Blacklist** — `POST /auth/logout` menambahkan `jti` ke blacklist Redis
- **Rate limiting** — `POST /auth/login` dibatasi 5 req / 60s per IP
- **Graceful degradation** — Redis down ≠ app crash (cache miss / skip)

## Prasyarat

- Python 3.12
- MySQL server (`DATABASE_URL`)
- Redis server (`REDIS_URL`) — opsional (aplikasi jalan tanpa Redis tapi tanpa caching/blacklist/rate-limit)

Cara cepat dengan Docker:

```bash
docker run -d --name mysql -p 127.0.0.1:3306:3306 \
  -e MYSQL_ALLOW_EMPTY_PASSWORD=yes -e MYSQL_DATABASE=topsus3 mysql:9
docker run -d --name redis -p 127.0.0.1:6379:6379 redis:7-alpine
```

## Setup

```bash
python3 -m venv venv   # atau: uv venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit bila perlu
python -m backend.seed # seed admin + demo user (idempotent)
```

## Jalankan

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Docs: http://127.0.0.1:8000/docs

## Akun Demo (setelah seed)

| Email                 | Password | Role       |
|-----------------------|----------|------------|
| admin@kampus.ac.id    | admin123 | admin      |
| budi@kampus.ac.id     | dosen123 | dosen      |
| ani@kampus.ac.id      | mhs123   | mahasiswa  |
| chandra@kampus.ac.id  | mhs123   | mahasiswa  |

## Endpoint

| Method | Path                              | Role            |
|--------|-----------------------------------|-----------------|
| POST   | `/auth/login`                     | public (rate-limited) |
| POST   | `/auth/logout`                    | any (blacklist jti) |
| GET    | `/auth/me`                        | any             |
| GET    | `/dosen`                          | admin (cached)  |
| POST   | `/dosen`                          | admin           |
| GET    | `/dosen/me`                       | dosen           |
| PUT    | `/dosen/{id}`                     | admin           |
| DELETE | `/dosen/{id}`                     | admin           |
| GET    | `/mahasiswa`                      | admin, dosen (cached) |
| POST   | `/mahasiswa`                      | admin           |
| GET    | `/mahasiswa/me`                   | mahasiswa       |
| PUT    | `/mahasiswa/{id}`                 | admin           |
| DELETE | `/mahasiswa/{id}`                 | admin           |
| PATCH  | `/mahasiswa/{id}/pembimbing`      | admin           |

## Env Variables

Lihat `.env.example`. Variabel penting di production:

- `JWT_SECRET` — **harus** diganti
- `DATABASE_URL` — SQLAlchemy format (`mysql+pymysql://...`)
- `REDIS_URL` — support `rediss://` (TLS) untuk Railway
- `CORS_ORIGINS` — comma-separated origin frontend

## Deploy ke Railway

1. New Project → Deploy from GitHub → pilih repo ini
2. Add Plugin: **MySQL** → salin `DATABASE_URL` (ganti prefix jadi `mysql+pymysql://`)
3. Add Plugin: **Redis** → salin `REDIS_URL`
4. Set env vars (`JWT_SECRET`, `CORS_ORIGINS=https://<vercel-domain>`)
5. Jalankan seed via Railway shell: `python -m backend.seed`

## Catatan Teknis

- `bcrypt<4.1` karena passlib belum kompatibel dengan bcrypt v5.
- JWT claims: `uid`, `role`, `type`, `jti`, `exp`.
- Role selalu dikonfirmasi ulang dari DB → token tidak bisa spoof role yang diubah admin.
