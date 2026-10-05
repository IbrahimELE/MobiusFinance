# Ugovor: učenje (learning_service, osoba A, port 8003)
Agent (B) poziva samo `GET /profile`; UI ide preko agenta (`/feedback`, `/profile` se prosljeđuju). Bez `LEARNING_URL` agent radi kao prije.

- `POST /feedback` tijelo: `{"project_id","ticker","brief_generated_at","rating":"up"|"down","note":"","tags":[]}` → `{"ok":true,"feedback_count":n}`
- `GET /feedback?project_id=` → lista unosa gornjeg oblika + `created_at`
- `GET /profile?project_id=` → mocks/profile.demo.json (prazan profil: `instructions:""`, prazne liste, `feedback_count:0`)
- `DELETE /profile?project_id=` → `{"ok":true}` ("zaboravi")
`mode`: "llm" | "rules". `instructions` je gotov tekst koji agent ubacuje u prompt.
