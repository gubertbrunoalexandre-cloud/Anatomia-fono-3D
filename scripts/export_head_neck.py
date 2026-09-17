"""
Exporta as estruturas de cabeca/pescoco/nervos cranianos do Z-Anatomy (Startup.blend)
para arquivos GLB, um por categoria, mais um manifest.json com nome/arquivo/descricao.

Uso (headless):
    blender --background <caminho para Startup.blend> --python export_head_neck.py

Fonte dos dados: Z-Anatomy (https://github.com/Z-Anatomy/Models-of-human-anatomy)
Licenca do conteudo: CC BY-SA 4.0 (Z-Anatomy) / CC BY-SA 2.1 Japan (BodyParts3D, DBCLS) /
                      CC-BY 4.0 (Cranial Nerves and Foramina, Univ. Dundee CAHID)
"""
import bpy
import bmesh
import os
import re
import json

OUT_DIR = r"C:\Users\guber\Documents\DOCUMENTOS\Projetos BG\SISTEMA DE GERENCIAMENTO DE PROJETOS\anatomia-fono-3d\data\glb"
MANIFEST_PATH = os.path.join(OUT_DIR, "manifest.json")

os.makedirs(OUT_DIR, exist_ok=True)

FALSE_POSITIVES = {
    'inner lip of iliac crest', 'outer lip of iliac crest',
    'lateral lip of linea apera', 'medial lip of linea apera',
    'tonsil of cerebellum',
}

CATEGORIES = {
    "laringe": [
        'laryn', 'cricoid', 'arytenoid', 'thyroid cartilage', 'vocal', 'glottis', 'epiglott',
        'cricothyroid', 'cricoarytenoid', 'crico-arytenoid', 'ary-epiglottic', 'thyroarytenoid',
        'thyro-arytenoid', 'corniculate', 'cuneiform cartilage', 'thyrohyoid membrane',
    ],
    "cavidade_oral_lingua": [
        'tongue', 'lingual', 'palate', 'palatine', 'lip', 'labial', 'cheek', 'buccal', 'gingiva',
        ' gum', 'floor of mouth', 'oral cavity', 'parotid', 'submandibular gland', 'sublingual gland',
        'frenulum', 'oral vestibule', 'philtrum', 'genioglossus', 'hyoglossus',
    ],
    "faringe": [
        'pharyn', 'tonsil', 'adenoid', 'nasopharynx', 'oropharynx', 'laryngopharynx',
    ],
    "atm": [
        'temporomandibular', 'mandibular condyle', 'lateral pterygoid', 'medial pterygoid',
        'mandibular fossa', 'articular tubercle',
    ],
    "nervo_I_olfatorio": ['olfactory'],
    "nervo_II_optico": ['optic nerve', 'optic chiasm', 'optic tract', 'optic disc'],
    "nervo_III_oculomotor": ['oculomotor'],
    "nervo_IV_troclear": ['trochlear nerve', 'nucleus of trochlear'],
    "nervo_V_trigemeo": [
        'trigeminal', 'ophthalmic nerve', 'maxillary nerve', 'mandibular nerve', 'trigeminal ganglion',
    ],
    "nervo_VII_facial": [
        'facial nerve', 'chorda tympani', 'greater petrosal', 'geniculate ganglion', 'facial canal',
        'facial colliculus',
    ],
    "nervo_IX_glossofaringeo": [
        'glossopharyngeal', 'tympanic nerve', 'carotid sinus nerve',
    ],
    "nervo_X_vago": [
        'vagus', 'recurrent laryngeal', 'superior laryngeal nerve', 'pharyngeal branch of vagus', 'vagal',
    ],
    "nervo_XI_acessorio": ['accessory nerve', 'nucleus of accessory'],
    "nervo_XII_hipoglosso": ['hypoglossal'],
    "cerebro": [
        'cerebrum', 'cerebral hemisphere', 'frontal lobe', 'parietal lobe', 'temporal lobe',
        'occipital lobe', 'limbic lobe', 'insula', 'insular', 'gyrus', 'sulcus', 'cerebellum',
        'cerebellar', 'brainstem', 'brain stem', 'midbrain', 'mesencephalon', 'pons',
        'medulla oblongata', 'diencephalon', 'thalamus', 'hypothalamus', 'epithalamus',
        'subthalamus', 'corpus callosum', 'fornix', 'internal capsule', 'basal nuclei',
        'caudate nucleus', 'lentiform nucleus', 'putamen', 'globus pallidus',
        'lateral ventricle', 'third ventricle', 'fourth ventricle', 'cerebral aqueduct',
        'choroid plexus', 'pineal', 'pituitary', 'hypophysis', 'infundibulum',
        'olfactory bulb', 'olfactory tract', 'cerebral peduncle', 'cerebral artery',
        'cerebral arterial circle', 'falx cerebri', 'tentorium cerebelli', 'dura mater',
        'arachnoid mater', 'pia mater', 'meninges', 'meningeal', 'subarachnoid',
        'hippocamp', 'amygdala', 'cingulate',
    ],
    "cranio_ossos": [
        'frontal bone', 'parietal bone', 'occipital bone', 'sphenoid', 'ethmoid',
        'temporal bone', 'maxilla', 'zygomatic bone', 'nasal bone', 'lacrimal bone',
        'vomer', 'palatine bone', 'mandible', 'hyoid bone', 'inferior nasal concha',
        'suture', 'skull', 'cranium', 'nasal septum', 'nasal cavity', 'orbit',
        'pterygoid process', 'styloid process', 'mastoid process', 'zygomatic arch',
        'coronoid process', 'foramen magnum', 'foramen ovale', 'foramen spinosum',
        'foramen rotundum', 'foramen lacerum', 'jugular foramen', 'stylomastoid foramen',
        'supraorbital foramen', 'infraorbital foramen', 'mental foramen',
        'incisive foramen', 'palatine foramen',
    ],
    "musculos_pescoco": [
        # nota: o dataset usa a nomenclatura "colli" (nao "cervicis") para varios
        # desses musculos - a versao anterior desta lista tinha "cervicis" e por
        # isso nunca pegava longissimus/semispinalis/iliocostalis/multifidus.
        'sternocleidomastoid', 'trapezius', 'scalenus', 'longus colli', 'longus capitis',
        'splenius capitis', 'splenius colli', 'levator scapulae', 'platysma',
        'longissimus capitis', 'longissimus colli', 'semispinalis colli',
        'iliocostalis colli', 'multifidus colli', 'spinalis capitis', 'spinalis colli',
        'interspinales colli',
    ],
    "musculos_suboccipitais": [
        'obliquus inferior capitis', 'obliquus superior capitis',
        'rectus posterior major capitis', 'rectus posterior minor capitis',
        'rectus anterior capitis', 'rectus lateralis capitis',
    ],
    "musculos_supra_infra_hioideos": [
        'digastric', 'geniohyoid', 'mylohyoid', 'stylohyoid',
        'omohyoid', 'sternohyoid', 'sternothyroid', 'thyrohyoid muscle',
    ],
    "musculos_mastigacao": [
        'temporalis muscle', 'masseter', 'medial pterygoid muscle', 'lateral pterygoid muscle',
        'superior head of lateral pterygoid', 'inferior head of lateral pterygoid',
    ],
    "musculos_faciais": [
        'frontalis', 'occipitalis', 'temporoparietalis', 'corrugator supercilii',
        'nasalis muscle', 'procerus', 'orbicularis oculi', 'orbicularis oris',
        'mentalis', 'risorius', 'zygomaticus major', 'zygomaticus minor',
        'levator labii superioris', 'levator anguli oris', 'depressor anguli oris',
        'depressor labii inferioris', 'levator palpebrae superioris',
    ],
    "musculos_extraoculares": [
        'inferior rectus muscle', 'superior rectus muscle', 'medial rectus muscle',
        'lateral rectus muscle', 'inferior oblique muscle', 'superior oblique muscle',
        'trochlea of superior oblique',
    ],
    "vertebras_cervicais": [
        'atlas (c1)', 'axis (c2)', 'vertebra c3', 'vertebra c4', 'vertebra c5',
        'vertebra c6', 'vertebra c7', 'intervertebral disc c',
    ],
    "regioes_superficie": [
        'auricular region', 'buccal region', 'frontal region', 'infra-orbital region',
        'mastoid region', 'mental region', 'nasal region', 'occipital region',
        'orbital region', 'parietal region', 'parotideomasseteric region',
        'temporal region', 'zygomatic region', 'sternocleidomastoid region',
        'carotid triangle', 'muscular triangle', 'submandibular triangle',
        'submental triangle', 'anterior region of neck', 'lateral region of neck',
        'posterior region of neck', 'external nose', 'auricle',
    ],
    "orelha_nariz_cartilagem": [
        # cartilagens reais confirmadas no dataset (nao existe cartilagem de olho -
        # a "cartilagem tarsal" da palpebra e tecido conjuntivo denso, nao cartilagem,
        # e nao aparece no dataset, corretamente)
        'helix', 'antihelix', 'tragus', 'antitragus', 'crura of antihelix',
        'nasal septal cartilage', 'alar cartilage', 'lateral process of nasal septal cartilage',
        # pontos de referencia de superficie do pavilhao auricular (mesmo complexo cartilaginoso)
        'concha of auricle', 'cymba conchae', 'eminentia conchae', 'cavity of concha',
        'lobule of auricle',
    ],
}

# Fissuras, canais, forames e suturas do cranio/pescoco. No Z-Anatomy/BodyParts3D
# esses "buracos" e juntas osseas quase nunca tem malha propria (um forame e
# ausencia de osso, nao um volume) - o dataset so marca a posicao com um objeto
# "gancho" de 2 vertices (sufixo ".j", usado pelo addon original so p/ ancorar
# o rotulo de texto flutuante). Para poder exibi-los como pontos clicaveis no
# app, criamos uma pequena esfera-marcador na posicao exata de cada gancho e
# deixamos ela seguir o pipeline normal de exportacao. Nome -> nome do objeto
# gancho de origem (para pegar a posicao no mundo).
LANDMARK_MARKERS = {
    "Supra-orbital notch": "(Supra-orbital notch).j",
    "Condylar canal": "Condylar canal.j",
    "Ethmoidal notch": "Ethmoidal notch.j",
    "Foramen caecum of frontal bone": "Foramen caecum of frontal bone.j",
    "Foramen magnum": "Foramen magnum.j",
    "Foramen ovale": "Foramen ovale.j",
    "Foramen rotundum": "Foramen rotundum.j",
    "Foramen spinosum": "Foramen spinosum.j",
    "Groove for marginal sinus": "Groove for marginal sinus.j",
    "Groove for middle meningeal artery": "Groove for middle meningeal artery.j",
    "Groove for occipital sinus": "Groove for occipital sinus.j",
    "Groove for transverse sinus": "Groove for transverse sinus.j",
    "Groove of pterygoid hamulus": "Groove of pterygoid hamulus.j",
    "Hypoglossal canal": "Hypoglossal canal.j",
    "Inferior thyroid notch": "Inferior thyroid notch.j",
    "Jugular notch of occipital bone": "Jugular notch of occipital bone.j",
    "Mastoid notch": "Mastoid notch.j",
    "Mental foramen": "Mental foramen.j",
    "Optic canal": "Optic canal.j",
    "Parietal foramen": "Parietal foramen.j",
    "Pterygoid canal": "Pterygoid canal.j",
    "Pterygoid notch": "Pterygoid notch.j",
    "Superior thyroid notch": "Superior thyroid notch.j",
    "Anterior semicircular canal": "Anterior semicircular canal.j",
    "Lateral semicircular canal": "Lateral semicircular canal.j",
    "Posterior semicircular canal": "Posterior semicircular canal.j",
    "Spiral canal of cochlea": "Spiral canal of cochlea.j",
    "Denticulate suture": "Denticulate suture.j",
    "Limbous suture": "Limbous suture.j",
    "Plane suture": "Plane suture.j",
    "Serrate suture": "Serrate suture.j",
    # coluna cervical - mesmo padrao (ganchos sem malha propria)
    "Canal for vertebral artery": "(Canal for vertebral artery).j",
    "Foramen transversarium": "Foramen transversarium.j",
    "Facet for dens": "Facet for dens.j",
    "Groove for spinal nerve": "Groove for spinal nerve.j",
    "Uncinate process of vertebra": "Uncinate process of vertebra.j",
}

MARKER_RADIUS = 0.0035


def create_marker_sphere(name, world_pos):
    mesh = bpy.data.meshes.new(name + "__marker_mesh")
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=MARKER_RADIUS)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = world_pos
    bpy.context.scene.collection.objects.link(obj)
    return obj


def create_landmark_markers():
    """Cria as esferas-marcador e devolve a lista de nomes criados."""
    created = []
    missing = []
    for name, hook_name in LANDMARK_MARKERS.items():
        hook = bpy.data.objects.get(hook_name)
        if hook is None:
            missing.append(hook_name)
            continue
        create_marker_sphere(name, hook.matrix_world.translation.copy())
        created.append(name)
    if missing:
        print(f"[aviso] marcos nao encontrados no .blend (pulados): {missing}")
    return created


SUFFIX_RE = re.compile(r'^(.*)\.([a-zA-Z0-9]{1,3})$')


def base_name(n):
    n = n.strip()
    m = SUFFIX_RE.match(n)
    if m and len(m.group(2)) <= 3:
        return m.group(1).strip()
    return n


def matches(name_low, keywords):
    return any(kw.lower() in name_low for kw in keywords)


def normalize_key(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


TA2_CSV_PATH = r"C:\Users\guber\Documents\DOCUMENTOS\Projetos BG\SISTEMA DE GERENCIAMENTO DE PROJETOS\anatomia-fono-3d\data\TA2.csv"


def load_ta2_pt():
    """Le a tabela Terminologia Anatomica 2 (English;...;Portugues;...) do Z-Anatomy
    e devolve um dict normalize_key(ingles) -> nome em portugues."""
    lookup = {}
    with open(TA2_CSV_PATH, encoding='utf-8') as f:
        header_seen = False
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith('"') and line.endswith('"'):
                line = line[1:-1]
            cols = line.split(';')
            if not header_seen:
                header_seen = True
                continue
            if len(cols) < 6:
                continue
            en = cols[1].strip()
            pt = cols[5].strip()
            if en and pt:
                key = normalize_key(en)
                if key not in lookup:
                    lookup[key] = pt
    return lookup


def pt_name_for(name, ta2_pt):
    """Traduz um nome (possivelmente com sufixo .l/.r e prefixos tipo
    'Anterior surface of X') usando a tabela TA2; cai para o nome em ingles
    se nao encontrar correspondencia."""
    b = base_name(name)
    key = normalize_key(b)
    if key in ta2_pt:
        return ta2_pt[key]
    return b


def clean_description(raw):
    text = raw
    idx = text.find('== ')
    if idx != -1:
        text = text[:idx]
    lines = text.split('\n')
    start = 0
    while start < len(lines) and (
        lines[start].strip() == '' or
        (lines[start].strip().isupper() and len(lines[start].strip()) < 80)
    ):
        start += 1
    text = '\n'.join(lines[start:]).strip()
    text = re.sub(r'\n{3,}', '\n\n', text)
    # mantem so os 2 primeiros paragrafos (texto introdutorio, estilo lead da Wikipedia)
    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    text = '\n\n'.join(paragraphs[:3])
    return text.strip()


def has_real_geometry(o):
    """Filtra os objetos-'gancho' do Z-Anatomy: pontos de ancoragem de rotulo
    com sufixo '.j' (ou similares) que tem so 2 vertices e 0 faces/segmentos -
    nao sao geometria visivel, sao usados internamente pelo addon original
    para posicionar textos flutuantes. Sem esse filtro, o exportador glTF
    simplesmente descarta esses objetos (mesh vazia), e a estrutura sumia da
    lista sem nenhum motivo aparente."""
    if o.type == 'MESH':
        return len(o.data.polygons) > 0
    if o.type == 'CURVE':
        return len(o.data.splines) > 0
    return True


def collect():
    all_objs = list(bpy.data.objects)
    geo_objs = [o for o in all_objs if o.type in ('MESH', 'CURVE') and has_real_geometry(o)]

    # category -> lista de NOMES (strings, capturados agora, imutaveis) dos objetos alvo
    category_names = {}
    all_target_names = set()
    target_base_keys = set()
    for cat, kws in CATEGORIES.items():
        names = []
        for o in geo_objs:
            low = o.name.lower()
            if matches(low, kws) and base_name(o.name).lower() not in FALSE_POSITIVES:
                names.append(o.name)
                all_target_names.add(o.name)
                target_base_keys.add(normalize_key(base_name(o.name)))
        category_names[cat] = names

    # marcos osseos (fissuras/canais/forames/suturas) - ver create_landmark_markers():
    # sao esferas sinteticas criadas na posicao exata dos pontos de ancoragem
    # originais do Z-Anatomy, ja que esses "buracos"/juntas quase nunca tem
    # malha propria no dataset fonte.
    marker_names = create_landmark_markers()
    category_names["marcos_osseos"] = marker_names
    for n in marker_names:
        all_target_names.add(n)
        target_base_keys.add(normalize_key(base_name(n)))

    # descricoes: bpy.data.texts tem um bloco de texto (artigo da Wikipedia,
    # CC BY-SA 3.0) por estrutura anatomica - muito mais rico que os rotulos
    # 3D (objetos FONT). So mantemos os que interessam ao subconjunto exportado.
    descriptions = {}
    for t in bpy.data.texts:
        key = normalize_key(t.name)
        if key not in target_base_keys:
            continue
        try:
            body = clean_description(t.as_string())
        except Exception:
            body = ""
        if body and (key not in descriptions or len(body) > len(descriptions[key])):
            descriptions[key] = body

    return category_names, all_target_names, descriptions


def clear_parent_keep_transform(obj):
    """Equivalente a 'Clear Parent and Keep Transform', mas via API de dados
    (sem bpy.ops) para evitar ambiguidade de contexto/selecao do operador em
    modo --background, que estava afetando um escopo muito maior do que o
    objeto selecionado (bug observado: todas as categorias saiam com o mesmo
    tamanho de arquivo, como se tudo fosse exportado em cada uma)."""
    if obj.parent is None:
        return
    world_matrix = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = world_matrix


def build_export_lookup(all_target_names, temp_collection):
    """Para cada nome alvo, garante um objeto MESH exportavel e devolve um dict
    nome_original -> objeto_exportavel. Cada curva e convertida UMA UNICA VEZ."""
    lookup = {}
    for name in all_target_names:
        if name not in bpy.data.objects:
            continue
        orig = bpy.data.objects[name]
        if orig.type == 'MESH':
            clear_parent_keep_transform(orig)
            lookup[name] = orig
            continue
        if orig.type != 'CURVE':
            continue

        temp_name = name + "__srctmp"
        orig.name = temp_name

        bpy.ops.object.select_all(action='DESELECT')
        orig.select_set(True)
        bpy.context.view_layer.objects.active = orig
        bpy.ops.object.duplicate(linked=False)
        dup = bpy.context.view_layer.objects.active

        for coll in list(dup.users_collection):
            coll.objects.unlink(dup)
        temp_collection.objects.link(dup)

        clear_parent_keep_transform(dup)

        bpy.ops.object.select_all(action='DESELECT')
        dup.select_set(True)
        bpy.context.view_layer.objects.active = dup
        bpy.ops.object.convert(target='MESH')
        dup.name = name  # nome limpo (o original ja foi renomeado para temp_name, nao ha colisao)

        lookup[name] = dup
    return lookup


def export_category(cat, names, lookup, ta2_pt):
    # esconde TUDO que ja foi preparado para exportacao antes de mexer nesta
    # categoria - o exportador glTF em modo --background parece usar tambem
    # (ou em vez de) a visibilidade dos objetos como escopo, entao sem isso
    # cada categoria ia acumulando os objetos ja tornados visiveis pelas
    # categorias anteriores (bug observado: contagem de malhas no .glb
    # crescendo categoria apos categoria, bem alem do esperado)
    for obj in lookup.values():
        obj.hide_set(True)
        obj.hide_viewport = True
        obj.hide_render = True

    valid = []
    bpy.ops.object.select_all(action='DESELECT')
    for name in names:
        obj = lookup.get(name)
        if obj is None:
            continue
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.hide_render = False
        obj.select_set(True)
        obj["orig_name"] = name  # preserva o nome original (com "." e espacos) como extras do glTF
        obj["name_pt"] = pt_name_for(name, ta2_pt)  # nome oficial em portugues (Terminologia Anatomica)
        valid.append(obj)
    if not valid:
        print(f"[skip] {cat}: sem malhas validas")
        return None
    bpy.context.view_layer.objects.active = valid[0]
    out_path = os.path.join(OUT_DIR, f"{cat}.glb")
    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_materials='NONE',
        export_extras=True,
    )
    print(f"[ok] {cat}: {len(valid)} objetos -> {out_path}")
    return {
        "file": f"{cat}.glb",
        "objects": [o.name for o in valid],
    }


def main():
    category_names, all_target_names, descriptions = collect()
    print(f"[info] total de nomes alvo unicos: {len(all_target_names)}")

    ta2_pt = load_ta2_pt()
    print(f"[info] entradas TA2 (ingles->portugues): {len(ta2_pt)}")

    temp_collection = bpy.data.collections.new("EXPORT_TEMP")
    bpy.context.scene.collection.children.link(temp_collection)

    lookup = build_export_lookup(all_target_names, temp_collection)
    print(f"[info] objetos exportaveis resolvidos: {len(lookup)}")

    # nomes em portugues por chave normalizada (para o manifest e para as
    # descricoes, que sao indexadas pela mesma chave)
    names_pt = {}
    for name in all_target_names:
        key = normalize_key(base_name(name))
        if key not in names_pt:
            names_pt[key] = pt_name_for(name, ta2_pt)

    manifest = {"categories": {}, "descriptions_en": descriptions, "names_pt": names_pt}
    for cat, names in category_names.items():
        result = export_category(cat, names, lookup, ta2_pt)
        if result:
            manifest["categories"][cat] = result

    # descricoes_pt e descricoes_fallback vivem em arquivos separados
    # (data/descriptions_pt_overrides.json e data/descriptions_fallback.json),
    # nao dentro do manifest gerado, para sobreviver a re-execucoes deste script
    # sem precisar retraduzir nada manualmente.
    for key, out_key in [
        ("descriptions_pt_overrides.json", "descriptions_pt"),
        ("descriptions_fallback.json", "descriptions_fallback"),
    ]:
        path = os.path.join(os.path.dirname(MANIFEST_PATH), "..", key)
        path = os.path.normpath(path)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                manifest[out_key] = json.load(f)
            print(f"[info] {out_key}: {len(manifest[out_key])} entradas carregadas de {path}")
        else:
            manifest[out_key] = {}

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"[done] manifest -> {MANIFEST_PATH}")


main()
