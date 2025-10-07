# Ferramentas OSINT - Integração

Este diretório contém a integração com ferramentas OSINT open source para investigações avançadas.

## Ferramentas Integradas

### 1. Social Mapper
**Repositório**: https://github.com/Greenwolf/social_mapper

**Descrição**: Correlaciona perfis de redes sociais via reconhecimento facial.

**Funcionalidades**:
- Busca automatizada em múltiplas plataformas (LinkedIn, Facebook, Twitter, Instagram, etc.)
- Reconhecimento facial para matching de perfis
- Geração de relatórios HTML

**Uso**:
```bash
cd tools/osint/social-mapper
python3 social_mapper.py -f [foto.jpg] -m fast -a all
```

### 2. EagleEye
**Repositório**: https://github.com/ThoughtfulDev/EagleEye

**Descrição**: Busca reversa de imagens em múltiplas plataformas.

**Funcionalidades**:
- Reverse image search (Google, Yandex, Bing, TinEye)
- Extração de metadados EXIF
- Detecção de faces e análise

**Uso**:
```bash
cd tools/osint/eagleeye
python3 eagleeye.py --image [foto.jpg] --engines all
```

### 3. TheHunter (theharvester)
**Repositório**: https://github.com/laramies/theHarvester

**Descrição**: Coleta de informações de e-mails, nomes, IPs e URLs.

**Funcionalidades**:
- Busca em múltiplas fontes (Google, Bing, LinkedIn, etc.)
- Enumeração de subdomínios
- Coleta de e-mails e funcionários

**Uso**:
```bash
cd tools/osint/theharvester
python3 theHarvester.py -d [dominio.com] -b all -l 500
```

## Arquitetura de Integração

```
tools/osint/
├── README.md                    # Este arquivo
├── docker-compose.yml           # Containers para ferramentas Python
├── social-mapper/               # Social Mapper + deps
│   ├── Dockerfile
│   ├── requirements.txt
│   └── wrapper.py               # SDK Node.js wrapper
├── eagleeye/                    # EagleEye + deps
│   ├── Dockerfile
│   ├── requirements.txt
│   └── wrapper.py
├── theharvester/                # TheHarvester + deps
│   ├── Dockerfile
│   ├── requirements.txt
│   └── wrapper.py
└── python-sdk/                  # SDK Python centralizado
    ├── osint_wrapper.py         # Wrapper unificado
    ├── requirements.txt
    └── server.py                # API REST para Node consumir
```

## Instalação Local

### Pré-requisitos
- Python 3.9+
- Node.js 20+
- Docker & Docker Compose
- Git

### Setup Rápido

```bash
# 1. Clonar submódulos das ferramentas
git submodule add https://github.com/Greenwolf/social_mapper tools/osint/social-mapper/source
git submodule add https://github.com/ThoughtfulDev/EagleEye tools/osint/eagleeye/source
git submodule add https://github.com/laramies/theHarvester tools/osint/theharvester/source
git submodule update --init --recursive

# 2. Build containers Docker
cd tools/osint
docker-compose build

# 3. Iniciar serviços
docker-compose up -d

# 4. Testar conexão
curl http://localhost:5000/health
```

### Instalação Manual (sem Docker)

```bash
# Instalar dependências Python
cd tools/osint/python-sdk
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Instalar cada ferramenta
cd ../social-mapper/source && pip install -r requirements.txt
cd ../../eagleeye/source && pip install -r requirements.txt
cd ../../theharvester/source && pip install -r requirements.txt

# Iniciar servidor wrapper
cd ../../python-sdk
python server.py
```

## Integração com Backend Node.js

O backend Fastify se comunica com as ferramentas Python via:
1. **REST API** (python-sdk/server.py) - Recomendado para produção
2. **Child Process** - Para testes locais

### Exemplo de Uso no Backend

```typescript
// apps/backend/src/services/osint.service.ts
import { execFile } from 'child_process';
import { promisify } from 'util';

const execFileAsync = promisify(execFile);

export class OsintService {
  async socialMapperSearch(imagePath: string, platforms: string[]) {
    // Via REST API
    const response = await fetch('http://localhost:5000/api/social-mapper', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ imagePath, platforms })
    });
    return response.json();
  }

  async eagleEyeSearch(imagePath: string) {
    const response = await fetch('http://localhost:5000/api/eagleeye', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ imagePath })
    });
    return response.json();
  }

  async theHarvesterSearch(domain: string) {
    const response = await fetch('http://localhost:5000/api/theharvester', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ domain })
    });
    return response.json();
  }
}
```

## Deploy em Produção

### Vercel + Supabase Edge Functions

Como as ferramentas Python não rodam diretamente na Vercel (Node.js), usamos:

**Opção 1: Supabase Edge Functions (Deno)**
- Criar Edge Functions que chamam containers Docker hospedados externamente
- Usar serviços como Railway, Render ou Fly.io para hospedar containers

**Opção 2: AWS Lambda + Docker**
- Build containers Docker das ferramentas
- Deploy em Lambda com imagem customizada
- Backend Vercel chama Lambda via API Gateway

**Opção 3: Microserviço Separado**
- Deploy containers em Railway/Render
- Backend Vercel se comunica via REST

### Exemplo: Deploy no Railway

```bash
# 1. Instalar Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Deploy
cd tools/osint
railway up

# 4. Configurar variáveis no backend Vercel
# OSINT_API_URL=https://seu-projeto.railway.app
```

## Variáveis de Ambiente

Adicionar ao `.env`:

```bash
# OSINT Tools
OSINT_API_URL=http://localhost:5000
OSINT_API_KEY=seu-token-secreto

# Social Mapper
SOCIAL_MAPPER_ENGINES=linkedin,facebook,twitter,instagram

# EagleEye
EAGLEEYE_ENGINES=google,yandex,bing,tineye

# TheHarvester
THEHARVESTER_SOURCES=google,bing,linkedin
```

## Segurança

⚠️ **IMPORTANTE**:
- Nunca exponha as ferramentas diretamente para a internet
- Use autenticação por token (OSINT_API_KEY)
- Implemente rate limiting
- Sanitize inputs para prevenir command injection
- Use containers isolados (Docker)
- Logs de auditoria para todas as operações

## Rate Limits e Considerações

- **Social Mapper**: Lento, pode levar minutos. Use filas (BullMQ).
- **EagleEye**: Rápido para reverse search, mas APIs externas têm limites.
- **TheHarvester**: Depende de scraping, sujeito a rate limits e CAPTCHAs.

**Recomendações**:
- Implementar cache Redis para resultados
- Usar filas para processar buscas assíncronas
- Retry com backoff exponencial
- Rotação de proxies (opcional)

## Próximos Passos

1. ✅ Estrutura básica criada
2. 🔄 Criar Dockerfiles para cada ferramenta
3. 🔄 Implementar Python SDK wrapper
4. 🔄 Integrar com backend Node.js
5. 🔄 Adicionar testes
6. 🔄 Deploy containers em Railway/Render
7. 🔄 Documentar fluxo completo de uso

## Referências

- [Social Mapper GitHub](https://github.com/Greenwolf/social_mapper)
- [EagleEye GitHub](https://github.com/ThoughtfulDev/EagleEye)
- [TheHarvester GitHub](https://github.com/laramies/theHarvester)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Vercel Limits](https://vercel.com/docs/concepts/limits/overview)
