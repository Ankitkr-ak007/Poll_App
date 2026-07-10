# Live Audience Polling App

A live audience-polling app for a physical room (100–150 people).

## Tech Stack
- **Backend:** FastAPI (Python), PostgreSQL
- **Frontend:** Next.js (App Router), Tailwind CSS

## Local Development
1. Start the services:
   ```bash
   docker-compose up -d
   ```
2. Apply backend migrations:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```
3. Create the initial admin user:
   ```bash
   docker-compose exec backend python -m app.scripts.create_admin
   ```
4. Open the frontend: [http://localhost:3000](http://localhost:3000)
5. Admin dashboard: [http://localhost:3000/admin/login](http://localhost:3000/admin/login) (admin / changeme)

## Deployment
- Backend: Render or Railway
- Frontend: Vercel
- DB: Managed PostgreSQL
