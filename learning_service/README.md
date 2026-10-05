# learning_service (Osoba A): AI koji uči od korisnika

Korisnik ocijeni brief (👍/👎 + bilješka, npr. „Više o dugu, kraće."), a servis iz toga
gradi **profil projekta** s gotovim uputama za agentov prompt. Bez UI-ja; agent i frontend
ga zovu preko `LEARNING_URL`.

## Pokretanje

```bash
cd learning_service
pip install -r requirements.txt -r requirements-dev.txt   # samo fastapi/uvicorn/httpx, mali
uvicorn app.main:app --port 8003
```
Testovi (bez mreže): `python -m pytest -q`

Env: `LEARNING_DATA_DIR` (default `./data`, nije u gitu), `LEARNING_LLM=auto|off`,
`ANTHROPIC_API_KEY` (ili prijavljeni `claude` CLI, isti redoslijed kao u agentu).

## Endpointi (ugovor: `contracts/README.md`, mockovi `profile.demo.json`, `feedback.demo.json`)

| Ruta | Šta radi |
|---|---|
| `POST /feedback` {project_id, ticker, brief_generated_at?, rating: up\|down, note?, tags?} | sačuva ocjenu; profil se odmah osvježi |
| `GET /feedback?project_id=` | sve ocjene projekta, najnovija zadnja |
| `GET /profile?project_id=` | `instructions` (za prompt), `label` (za „Naučeno: …"), `focus`, `avoid`, `style`, `mode` |
| `DELETE /profile?project_id=` | zaboravi sve (ponavljanje demoa) |
| `POST /demo/seed?project_id=demo` | učita 2 ocjene iz demo scenarija + unaprijed AI profil (radi offline) |

`project_id` je isti „slug" kao u agentu (`Moj Projekt` → `moj-projekt`).

## Kako uči

1. **Pravila (uvijek, odmah, offline)** – `app/rules.py`. Bilješka se dijeli na rečenice; u svakoj
   se traže teme (dug, FCF, valuacija, rast, marže, konkurencija, rizici, dividende, makro,
   proizvodi) i smjer: „manje / bez / previše / ne zanima" = izbjegavaj, sve ostalo = fokus.
   Stil: „kraće", „detaljnije", „jednostavnije / objasni", „više brojeva". Radi s i bez
   kvačica i na engleskom. Zadnje mišljenje o temi pobjeđuje („ipak više o proizvodima").
   `tags` iz UI-ja rade isto što i riječi u bilješci.
2. **AI sažetak (kad je dostupan)** – poslije svake ocjene, u pozadini, AI napiše 2–3 rečenice
   uputa i kratak `label`. Čuva se uz otisak ocjena koje pokriva; čim stigne nova ocjena, stari
   sažetak se ne koristi dok AI ne napravi novi (do tada `mode: "rules"`). Ako AI padne, ostaju pravila.

## Demo
```bash
curl -X DELETE "localhost:8003/profile?project_id=demo"      # čisto
curl -X POST   "localhost:8003/demo/seed?project_id=demo"    # ili ocijeni uživo iz UI-ja
curl "localhost:8003/profile?project_id=demo"
```
Unaprijed AI profil za demo ocjene: `demo/llm_summary.json` (napravljen s
`python -m scripts.build_demo_summary`; ponovi ako mijenjaš `demo/feedback.json`).

Provjereno 5.10. uživo s kopijom agenta koja ubacuje `instructions` u prompt: prije ocjena
teza AAPL počinje cijenom i P/E-om; poslije „Više o dugu i FCF-u, kraće" + „Manje o proizvodima"
počinje slobodnim novčanim tokom i ne opisuje proizvode.

## Za agent (osoba B)
```python
ins = httpx.get(f"{LEARNING_URL}/profile", params={"project_id": pid}, timeout=5).json()["instructions"]
prompt += f"\nUpute naučene od korisnika (poštuj ih): {ins}" if ins else ""
```
Bez `LEARNING_URL` ili kad servis ne radi: preskoči, brief radi kao prije. Napomena: tvoj prompt
fiksno traži „3-4 rečenice", pa „kraće" iz profila nema puni efekat; pusti da upute to nadjačaju.
