# Anatomia 3D — Cabeça e Pescoço (Fonoaudiologia)

Ferramenta de estudo de anatomia 3D em português, cobrindo cabeça e pescoço por
completo: cérebro, ossos do crânio, músculos do pescoço, laringe/pregas vocais,
cavidade oral e língua, faringe, ATM, os 11 nervos cranianos do currículo de
Fonoaudiologia (I–V, VII, IX–XII) e regiões de superfície (o mais próximo que o
dataset fonte tem de "pele", que não existe como malha separada).

## Como rodar

```bash
python -m http.server 8080 --directory anatomia-fono-3d
```

Depois abra `http://localhost:8080/web/index.html` no navegador.

(O `.claude/launch.json` do projeto pai já tem essa configuração pronta como
"anatomia-fono-3d" para quem estiver usando o Claude Code / Claude Desktop.)

## Estrutura do projeto

```
anatomia-fono-3d/
├── data/
│   ├── blender_source/Startup.blend   # fonte original do Z-Anatomy (306 MB, nao versionar)
│   ├── TA2.csv                         # Terminologia Anatomica multi-idioma (Z-Anatomy)
│   └── glb/                            # modelos exportados (18 arquivos .glb + manifest.json)
├── scripts/
│   └── export_head_neck.py             # script headless do Blender que gera os .glb
├── web/
│   ├── index.html
│   └── js/main.js                      # visualizador Three.js
└── README.md
```

## Categorias exportadas (18)

Laringe e pregas vocais · Cavidade oral e língua · Faringe · ATM · Nervos
cranianos I, II, III, IV, V, VII, IX, X, XI, XII (cada um sua própria categoria)
· Cérebro · Ossos do crânio · Músculos do pescoço · Regiões de superfície.

~532 objetos de geometria únicos, ~22 MB no total (carregados sob demanda por
categoria, não tudo de uma vez).

## Pipeline de dados

1. Fonte: [Z-Anatomy](https://github.com/Z-Anatomy/Models-of-human-anatomy) —
   atlas 3D de anatomia humana de código aberto, construído sobre o BodyParts3D
   e enriquecido com o conjunto "Cranial Nerves and Foramina" da University of
   Dundee (CAHID). Tudo vive num único arquivo `Startup.blend` (306 MB, ~7.184
   objetos no total).
2. `scripts/export_head_neck.py` roda dentro do Blender (headless) e:
   - Identifica os objetos relevantes por categoria via palavras-chave no nome.
   - Descarta objetos sem geometria real (`has_real_geometry`) — o Z-Anatomy usa
     objetos-"gancho" de 2 vértices/0 faces (sufixo `.j`) só para ancorar rótulos
     de texto flutuante; sem esse filtro eles entram na lista mas o exportador
     glTF os descarta silenciosamente (a estrutura "sumia" sem explicação).
   - Converte nervos/vasos (objetos do tipo `CURVE`) para malha antes de exportar,
     já que glTF não suporta curvas nativamente. Cada curva é convertida **uma
     única vez** (não por categoria) via um lookup compartilhado, para não
     desperdiçar trabalho quando a mesma estrutura aparece em mais de uma
     categoria (ex.: nervo glossofaríngeo em "faringe" e em sua própria categoria).
   - Remove o parentesco de cada objeto antes de exportar (mantendo a posição no
     mundo via matriz), e esconde **todos** os objetos já preparados antes de
     tornar visível só o subconjunto da categoria atual. Sem isso, o exportador
     glTF em modo `--background` parecia usar a visibilidade acumulada da cena
     como escopo real de exportação (mais do que a seleção em si) — cada
     categoria ia "vazando" objetos de todas as anteriores, crescendo
     categoria após categoria até a última sair com quase tudo dentro.
   - Grava o nome original de cada objeto como propriedade customizada
     (`orig_name`) antes de exportar, porque o exportador glTF do Blender
     sanitiza nomes (troca espaço por `_`, remove `.`) — o app web lê essa
     propriedade via `extras` para recuperar o nome real.
   - Traduz o nome de cada estrutura para português via `data/TA2.csv`
     (Terminologia Anatomica oficial, tradução de Ana Teresa Bigio para o
     Z-Anatomy) — cobertura de ~97% dos nomes do dataset inteiro.
   - Extrai descrições anatômicas dos blocos de texto internos do `.blend`
     (`bpy.data.texts`, um artigo por estrutura, derivado da Wikipédia) e grava
     tudo em `data/glb/manifest.json` como `descriptions_en`.
   - Exporta um `.glb` por categoria.
3. As 377 descrições em inglês foram traduzidas para português (PT-BR,
   terminologia médica/anatômica) e gravadas em `manifest.json` como
   `descriptions_pt` — é essa chave que o app usa; `descriptions_en` fica como
   fallback caso alguma estrutura nova apareça sem tradução ainda.

Para regerar os `.glb` depois de qualquer ajuste no script:

```bash
"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background ^
  "data\blender_source\Startup.blend" --python "scripts\export_head_neck.py"
```

Se novas categorias/estruturas forem adicionadas depois, as descrições novas
ficam só em `descriptions_en` até alguém (ou uma sessão futura) traduzir e
mesclar em `descriptions_pt` (ver `scripts/export_head_neck.py`, seção
`descriptions`, e o histórico desta sessão para o processo usado — tradução em
lote via agentes, arquivo por arquivo, mesclado por chave normalizada).

## Licenciamento e atribuição (obrigatório manter visível no app)

- **BodyParts3D** — Database Center for Life Science (DBCLS), CC BY-SA 2.1 Japan.
- **Z-Anatomy** — CC BY-SA 4.0.
- **Cranial Nerves and Foramina** — University of Dundee, CAHID, CC-BY 4.0.
- **Terminologia em português** — tradução de Ana Teresa Bigio para o Z-Anatomy.
- **Descrições textuais** — adaptadas da Wikipédia (CC BY-SA 3.0) e traduzidas
  para português.

Uso comercial é permitido em todas essas licenças, desde que a atribuição seja
mantida e qualquer obra derivada continue sob licença compatível (ShareAlike).

**Atenção**: dois conjuntos específicos empacotados dentro do Z-Anatomy são
**não-comerciais** e foram deliberadamente **excluídos** deste subconjunto:
"Anatomy of the Inner Ear" (Univ. Dundee, CC-BY-NC-SA 4.0) e "Kidney" (Lissie
Cowley, CC-BY-NC 4.0). Se o escopo do app um dia incluir ouvido interno, essas
peças precisam ser substituídas por outra fonte compatível com uso comercial.

## Limitações conhecidas / próximos passos

- **Não existe malha de pele/integumento** no dataset fonte (BodyParts3D nunca
  modelou isso — é um atlas de ossos/músculos/órgãos, não de anatomia de
  superfície). A categoria "Regiões de superfície" usa as subdivisões
  topográficas oficiais da cabeça/pescoço (região frontal, região parotídea,
  triângulo carotídeo etc.) como o substituto mais próximo disponível.
- **Cores por tipo de tecido são heurísticas** (definidas em `main.js` via regex
  no nome da estrutura: nervo=amarelo, músculo=vermelho, cartilagem=cinza-azulado,
  etc.), não a paleta original do Z-Anatomy — o material original do Blender usa
  um shader customizado que não é traduzido corretamente pelo exportador glTF
  padrão (veio com `emissive` branco puro, estourando tudo pra branco).
- **~30% das estruturas não têm descrição textual** (não existe artigo
  correspondente nos blocos de texto do arquivo fonte — mais comum em acidentes
  ósseos pequenos e subdivisões muito finas).
- **Malhas de nervos são relativamente pesadas** (curvas com bevel convertidas
  para malha) — pode valer a pena decimar no Blender se a performance em
  dispositivos mais fracos for um problema.
- Nervos cranianos VI (abducente) e VIII (vestibulococlear) existem no dataset
  fonte mas não foram incluídos por não estarem no escopo original — fácil de
  adicionar depois (bastaria uma nova categoria em `CATEGORIES` no script de
  exportação, seguindo o mesmo padrão dos outros nervos).
- Sem modo quiz ainda (mencionado no briefing original como funcionalidade do
  Anatomy 3D Atlas a ser eventualmente replicada).
