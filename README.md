# investigacao-osint-facial

Sistema profissional de investigação OSINT com reconhecimento facial.

## Visão Geral
Plataforma full‑stack com:
- Frontend: React (Vite) + Tailwind, deploy na Vercel
- Backend: Node.js (Fastify) + TypeScript, REST e Webhooks, deploy na Vercel/Serverless
- Banco: Supabase (Postgres + Auth + Storage)
- Reconhecimento facial: face-api.js (browser) e mediapipe/onnx via server opcional
- Integrações: APIs OSINT públicas, Supabase, Vercel, Proxies

## Estrutura do Projeto
```
/
├── apps/
│   ├── frontend/         # React + Vite + Tailwind, rotas públicas/privadas
│   └── backend/          # Fastify + TS, rotas /api, webhooks, workers
├── packages/
│   ├── shared/           # Tipos, schemas zod, utils
│   └── osint-clients/    # SDK para serviços OSINT e face
├── .github/workflows/    # CI: lint, typecheck, build, test, preview
├── supabase/             # Migrations, policies (RLS), seeds
└── README.md
```

## Como Rodar Localmente
Pré‑requisitos: Node 20+, pnpm, Supabase CLI, Git.

```bash
# Clonar e instalar
pnpm i

# Variáveis de ambiente (crie .env na raiz)
cp .env.example .env

# Subir Supabase local
supabase start

# Rodar backend e frontend
pnpm -C apps/backend dev
pnpm -C apps/frontend dev
```

## Variáveis de Ambiente (.env)
- SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE
- NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY (no frontend)
- FACE_MODEL_URL (URL dos modelos face-api.js em /public/models ou CDN)
- OSINT_API_KEYS (chaves opcionais por provedor)

## Supabase
- Auth: email + OTP, provedor OAuth (opcional)
- Tabelas: persons, faces, sources, findings, audits
- Storage: bucket faces/ com políticas privadas; URL assinada para acesso temporário
- RLS: leituras do usuário só em seus dados; tabela audits sem RLS para auditoria

## Backend (Fastify)
- Endpoints:
  - POST /api/persons, GET /api/persons/:id
  - POST /api/faces: upload e indexação de embedding
  - POST /api/search: busca OSINT + facial
- Middlewares: auth JWT Supabase, rate limit, logging pino
- Workers: fila para crawling e extração (BullMQ/Upstash)

## Frontend (React)
- Páginas: Login, Dashboard, Pessoas, Buscas, Comparação Facial
- Componente CameraCapture (WebRTC) + face-api.js para detecção local
- Upload seguro para Storage com URL assinada do backend

## Integração Vercel
- Projetos separados para apps/frontend e apps/backend
- Adicionar variáveis de ambiente no Dashboard da Vercel
- Rotas serverless: /api/** no backend; preview deployments por PR

## Integração Supabase
Exemplo de cliente no frontend:
```ts
import { createClient } from '@supabase/supabase-js'
export const supabase = createClient(import.meta.env.VITE_SUPABASE_URL!, import.meta.env.VITE_SUPABASE_ANON_KEY!)
```
Exemplo no backend (service role via Vercel env):
```ts
import { createClient } from '@supabase/supabase-js'
export const supabaseAdmin = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE!)
```

## Exemplos de Integração de APIs OSINT
SDK simplificado em packages/osint-clients:
```ts
export async function searchUsername(username: string) {
  const res = await fetch(`https://api.wikiless.rawbit.ch/api.php?action=query&list=search&srsearch=${encodeURIComponent(username)}`)
  return res.json()
}
```
Exemplo facial (frontend):
```ts
import * as faceapi from 'face-api.js'
await faceapi.nets.ssdMobilenetv1.loadFromUri(import.meta.env.VITE_FACE_MODEL_URL)
await faceapi.nets.faceRecognitionNet.loadFromUri(import.meta.env.VITE_FACE_MODEL_URL)
const detections = await faceapi.detectAllFaces(video).withFaceLandmarks().withFaceDescriptors()
```

## Scripts sugeridos (pnpm)
- pnpm lint, pnpm build, pnpm test
- pnpm -C apps/backend dev
- pnpm -C apps/frontend dev

## Segurança e Compliance
- RLS habilitado por padrão; nunca expor service_role no cliente
- Logs de auditoria em audits
- Rate limit e CAPTCHA para endpoints sensíveis

## Roadmap
- Exportação de relatórios PDF
- Integração com provedores adicionais OSINT
- Treinamento incremental de embeddings
```
