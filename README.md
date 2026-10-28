# godata-br

Brazilian reference data and tooling for [Go.Data](https://www.who.int/tools/godata), WHO's outbreak investigation and contact tracing tool.

Brazil is the largest Go.Data user in Latin America. About 15 states run their own servers, and the Ministry of Health has run a national one since 2024. Every one of these servers has to load a location tree before the first outbreak can be created, and Go.Data does not ship with one. This repository provides that tree, ready to import.

## Location files (`dist/`)

| File | Content | Records |
|---|---|---|
| `brasil-uf-municipios.json` / `.csv` | Brasil → 27 UFs → 5,571 municípios (IBGE) | 5,599 |
| `brasil-dsei-polos-base.json` / `.csv` | DSEI root → 34 DSEIs → 158 Polos Base (CNES) | 193 |

Each location carries:

- **IBGE code (7 digits)** and **IBGE6 (6 digits, the code used by SINAN)** as identifiers. You can match SINAN notifications to Go.Data locations without a lookup table.
- Coordinates of the municipal seat (UFs: centroid).
- The accent-free name as a synonym (`Amaturá` → `Amatura`), and the UF abbreviation for states.
- Stable IDs (`br-uf-13`, `br-mun-1302603`, `br-dsei-yanomami`, `br-polo-<CNES>`). If you re-import, records are updated instead of duplicated, and other systems can reference them.

The `.json` files use Go.Data's hierarchical import format. The `.csv` files follow the columns of WHO's Excel templates (`NAME, ID, CODE, LONG, LAT, ADMIN_LEVEL, PARENTLOCATIONID`).

### DSEI tree: scope and limitations

- **Included:** the 34 DSEIs (SESAI/MS), plus every active Polo Base whose CNES record names its DSEI. That is 158 of the ~350 active Polos Base in CNES.
- **Not included:** the remaining Polos Base. Their CNES records list a generic owner ("MINISTERIO DA SAUDE"), so the DSEI cannot be determined reliably. The authoritative DSEI ↔ Polo Base table lives in SIASI and has been requested from SESAI.
- **DSEIs that appear with no Polos Base yet:** Altamira, Kaiapó do Mato Grosso, Minas Gerais e Espírito Santo, Parintins, Vale do Javari.
- **Coordinates:** some Polos Base share the same coordinates, because CNES uses the municipal seat as a placeholder.

## Importing

**Web app:** Locations → Quick actions → Import → choose the `.json` file.

**API:**

```bash
curl -X POST "https://<server>/api/locations/import?access_token=<token>" \
     -F "file=@dist/brasil-uf-municipios.json;type=application/json"
```

Validated on Go.Data **2.50.3**. The full Brazil tree takes about 2 minutes to import, and the DSEI tree about 7 seconds.

> **Gotcha:** the built-in `admin@who.int` (System administrator) **cannot import locations**. It lacks the `location_import` permission and cannot change its own roles. Create a user with the **Reference data manager** role and import with that user.

![Location tree in Go.Data](docs/img/02-amazonas-municipios-pt.png)

## Regenerating

```bash
python src/build_locations.py
```

The script reads from `data/raw/`, which is not versioned:

- [IBGE localidades API](https://servicodados.ibge.gov.br/api/docs/localidades): `ibge_estados.json` and `ibge_municipios.json` (`?view=nivelado`)
- [kelvins/municipios-brasileiros](https://github.com/kelvins/municipios-brasileiros) (MIT): `estados.csv` and `municipios.csv` (coordinates)
- [OpenDataSUS CNES](https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/CNES/cnes_estabelecimentos.zip): `cnes_estab.zip`

## Running Go.Data locally (Docker)

WHO provides no official Docker image. `docker/` builds Go.Data from the official sources:

```bash
git clone --depth 1 https://github.com/WorldHealthOrganization/GoDataSource-API vendor/GoDataSource-API
git clone --depth 1 https://github.com/WorldHealthOrganization/GoDataSource-FrontEnd vendor/GoDataSource-FrontEnd
cd docker && docker compose up -d --build   # http://localhost:8000  (admin@who.int / admin)
```

The first start initializes and migrates the database, which takes a few minutes.

## Portuguese translation findings

The bundled "Português" language (`portuguese_pt`) is incomplete:

- **5,589 of 9,785 strings (57%) are identical to English.** About 4,800 of them are UI strings, not help text.
- **548 strings are copied from Spanish** (e.g. "Registro de auditoría", "nube").
- Some strings are mistranslated. For example, the Locations page title reads "Locais para criança" ("places for children"), and the coordinates column reads "Lat / GNL".
- The language follows European Portuguese conventions ("contacto", "utilizador", "registo").

`analysis/pt-traducao-pendente.csv` lists every affected string (snapshot of the official 2.50.3 release).

## License

Code: Apache-2.0. Data: derived from IBGE, CNES/OpenDataSUS and kelvins/municipios-brasileiros (MIT); see their respective terms.
