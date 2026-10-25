# Frontend refresh for 915

Keeps the latest 915 project structure and backend contracts.
Frontend visual direction is inspired by the supplied demo1 frontend:
- dark operations sidebar and grouped navigation
- dashboard/control-tower layout
- metric cards, status pills, clean tables
- real FastAPI integration for scenario import, planning jobs, plans, events and simulations
- B-06 experiment workflow using the latest backend contracts
- no copied legacy Spring Boot business implementation and no fake business data

Run:
cd frontend
npm ci
npm run build
npm run dev
